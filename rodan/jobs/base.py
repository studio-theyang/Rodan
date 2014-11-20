import tempfile, shutil, os, uuid, copy, re
from celery import Task
from celery.app.task import TaskType
from rodan.models.runjob import RunJobStatus
from rodan.models import RunJob, Input, Output, Resource, ResourceType, Job, InputPortType, OutputPortType
from rodan.jobs.helpers import create_thumbnails
from django.conf import settings as rodan_settings
from django.core.files import File
from django.db.models import Prefetch
from rodan.exception import CustomAPIException
from rest_framework import status

import logging
logger = logging.getLogger('rodan')

class RodanTaskType(TaskType):
    """
    This is the metaclass for RodanTask base class.

    Every time a new task inherits RodanTask, __init__ method of this metaclass is
    triggered, which registers the new task in Rodan database.

    Note: TaskType is the metaclass of Task (Celery objects)
    """
    def __new__(cls, clsname, bases, attrs):
        attrs['_abstract'] = attrs.get('abstract')  # Keep a copy as Celery TaskType will delete it.
        return TaskType.__new__(cls, clsname, bases, attrs)

    def __init__(cls, clsname, bases, attrs):
        super(RodanTaskType, cls).__init__(clsname, bases, attrs)

        if attrs.get('_abstract') == True:  # not the abstract class
            return
        else:
            if RodanAutomaticTask in bases:
                interactive = False
            elif RodanManualTask in bases:
                interactive = True
            else:
                raise TypeError('Rodan tasks should always inherit either RodanAutomaticTask or RodanManualTask')

            if not Job.objects.filter(job_name=attrs['name'], interactive=interactive).exists():
                j = Job(job_name=attrs['name'],
                        author=attrs.get('author'),
                        description=attrs.get('description'),
                        settings=attrs.get('settings'),
                        enabled=attrs.get('enabled', False),
                        category=attrs.get('category'),
                        interactive=interactive)
                j.save()

                for ipt in attrs['input_port_types']:
                    i = InputPortType(job=j,
                                      name=ipt.get('name'),
                                      minimum=ipt.get('minimum'),
                                      maximum=ipt.get('maximum'))
                    i.save()
                    resource_types = RodanTaskType._resolve_resource_types(ipt['resource_types'])
                    if len(resource_types) == 0:
                        raise ValueError('No available resource types found for this InputPortType: {0}'.format(ipt['resource_types']))
                    i.resource_types.add(*resource_types)

                for opt in attrs['output_port_types']:
                    o = OutputPortType(job=j,
                                       name=opt.get('name'),
                                       minimum=opt.get('minimum'),
                                       maximum=opt.get('maximum'))
                    o.save()
                    resource_types = RodanTaskType._resolve_resource_types(opt['resource_types'])
                    if len(resource_types) == 0:
                        raise ValueError('No available resource types found for this OutputPortType: {0}'.format(opt['resource_types']))
                    o.resource_types.add(*resource_types)

    @staticmethod
    def _resolve_resource_types(value):
        """
        `value` should be one of:
        - a list of strings of mimetypes
        - a callable which receives one parameter (as a filter)

        Returns a list of ResourceType objects.
        """
        try:
            mimelist = filter(value, ResourceType.all_mimetypes())
        except TypeError:
            mimelist = value
        return ResourceType.cached_list(mimelist)


class RodanTask(Task):
    __metaclass__ = RodanTaskType
    abstract = True

    def _inputs(self, runjob_id, with_urls=False):
        """
        Return a dictionary of list of input file path and input resource type.
        If with_urls=True, it also includes the compat resource url and thumbnail urls.
        """
        values = ['input_port__input_port_type__name',
                  'resource__compat_resource_file',
                  'resource__resource_type__mimetype']
        if with_urls:
            values.append('resource__uuid')
        input_values = Input.objects.filter(run_job__pk=runjob_id).values(*values)

        inputs = {}
        for input_value in input_values:
            ipt_name = input_value['input_port__input_port_type__name']
            if ipt_name not in inputs:
                inputs[ipt_name] = []
            d = {'resource_path': input_value['resource__compat_resource_file'],
                 'resource_type': input_value['resource__resource_type__mimetype']}

            if with_urls:
                r = Resource.objects.get(uuid=input_value['resource__uuid'])
                d['resource_url'] = r.compat_file_url
                d['small_thumb_url'] = r.small_thumb_url
                d['medium_thumb_url'] = r.medium_thumb_url
                d['large_thumb_url'] = r.large_thumb_url

            inputs[ipt_name].append(d)
        return inputs

    def _outputs(self, runjob_id, temp_dir):
        "Return a dictionary of list of output file path and output resource type."
        output_values = Output.objects.filter(run_job__pk=runjob_id).values(
            'output_port__output_port_type__name',
            'resource__resource_type__mimetype',
            'uuid')

        outputs = {}
        for output_value in output_values:
            opt_name = output_value['output_port__output_port_type__name']
            if opt_name not in outputs:
                outputs[opt_name] = []

            output_res_tempname = str(uuid.uuid4())
            output_res_temppath = os.path.join(temp_dir, output_res_tempname)

            outputs[opt_name].append({'resource_type': output_value['resource__resource_type__mimetype'],
                                      'resource_temp_path': output_res_temppath,
                                      'uuid': output_value['uuid']})
        return outputs

    def _settings(self, runjob_id):
        return RunJob.objects.filter(uuid=runjob_id).values_list('job_settings', flat=True)[0]


class RodanAutomaticTask(RodanTask):
    abstract = True
    # code here are run asynchronously. Any write to database should use `queryset.update()` method, instead of `obj.save()`.
    # Specific jobs that inherit the base class should not touch database.

    def run(self, runjob_id):
        settings = RunJob.objects.filter(uuid=runjob_id).values_list('job_settings', flat=True)[0]
        inputs = self._inputs(runjob_id)
        _temp_dir = tempfile.mkdtemp()
        outputs = self._outputs(runjob_id, _temp_dir)

        # build argument for run_my_task and mapping dictionary
        arg_outputs = {}
        temppath_map = {}
        for opt_name, output_list in outputs.iteritems():
            if opt_name not in arg_outputs:
                arg_outputs[opt_name] = []
            for output in output_list:
                arg_outputs[opt_name].append({
                    'resource_path': output['resource_temp_path'],
                    'resource_type': output['resource_type']
                })
                temppath_map[output['resource_temp_path']] = output

        try:
            retval = self.run_my_task(inputs, settings, arg_outputs)
        except:
            raise
        else:
            # save outputs
            for temppath, output in temppath_map.iteritems():
                with open(temppath, 'rb') as f:
                    o = Output.objects.get(uuid=output['uuid'])
                    o.resource.compat_resource_file.save(temppath, File(f), save=False) # Django will resolve the path according to upload_to
                    path = o.resource.compat_resource_file.path
                    res_query = Resource.objects.filter(outputs__uuid=output['uuid'])
                    res_query.update(compat_resource_file=path)
            return retval
        finally:
            shutil.rmtree(_temp_dir)
            del _temp_dir

    def run_my_task(self, inputs, settings, outputs):
        raise NotImplementedError()

    def my_error_information(self, exc, traceback):
        raise NotImplementedError()


    def on_success(self, retval, task_id, args, kwargs):
        runjob_id = args[0]
        RunJob.objects.filter(pk=runjob_id).update(status=RunJobStatus.HAS_FINISHED,
                                                 error_summary='',
                                                 error_details='')
        output_resources = Resource.objects.filter(outputs__run_job=runjob_id)
        for output_resource in output_resources:
            create_thumbnails.si(str(output_resource.uuid)).apply_async()

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        runjob_id = args[0]

        update = self._add_error_information_to_runjob(exc, einfo)
        update['status'] = RunJobStatus.FAILED
        RunJob.objects.filter(pk=runjob_id).update(**update)

    def _add_error_information_to_runjob(self, exc, einfo):
        # Any job using the default_on_failure method can define an error_information
        # method, which will take in an exception and a traceback string,
        # and return a dictionary containing 'error_summary' and 'error_details'.
        # This is to allow pretty formatting of error messages in the client.
        # If any StandardError is raised in the process of retrieving the
        # values, the default values are used for both fields.
        try:
            err_info = self.my_error_information(exc, einfo.traceback)
            err_summary = err_info['error_summary']
            err_details = err_info['error_details']
            if rodan_settings.TRACEBACK_IN_ERROR_DETAIL:
                err_details = str(err_details) + "\n\n" + str(einfo.traceback)
        except Exception as e:
            logger.warning("The my_error_information method is not implemented properly (or not implemented at all). Exception: ")
            logger.warning("%s: %s" % (e.__class__.__name__, e.__str__()))
            logger.warning("Using default sources for error information.")
            err_summary = exc.__class__.__name__
            err_details = einfo.traceback

        return {'error_summary': err_summary,
                'error_details': err_details}

    def test_my_task(self, testcase):
        raise NotImplementedError('{0}.test_my_task() is not implemented.'.format(type(self).__module__))

class RodanManualTask(RodanTask):
    abstract = True

    def get_interface(self, runjob_id):
        inputs = self._inputs(runjob_id)
        settings = self._settings(runjob_id)
        return self.get_my_interface(inputs, settings)

    def get_my_interface(self, inputs, settings):
        """
        inputs will contain:
        resource_path, resource_type, resource_url, small_thumb_url, medium_thumb_url,
        large_thumb_url

        Should return: (template, context), template is a Django Template object,
        and context should be a dictionary.

        could raise rodan.jobs.base.ManualJobException
        """
        raise NotImplementedError()

    def save_user_input(self, runjob_id, user_input):
        inputs = self._inputs(runjob_id)
        settings = self._settings(runjob_id)
        _temp_dir = tempfile.mkdtemp()
        outputs = self._outputs(runjob_id, _temp_dir)

        # build argument for run_my_task and mapping dictionary
        arg_outputs = {}
        temppath_map = {}
        for opt_name, output_list in outputs.iteritems():
            if opt_name not in arg_outputs:
                arg_outputs[opt_name] = []
            for output in output_list:
                arg_outputs[opt_name].append({
                    'resource_path': output['resource_temp_path'],
                    'resource_type': output['resource_type']
                })
                temppath_map[output['resource_temp_path']] = output

        try:
            retval = self.save_my_user_input(inputs, settings, arg_outputs, user_input)
        except:
            raise
        else:
            # save outputs
            for temppath, output in temppath_map.iteritems():
                with open(temppath, 'rb') as f:
                    o = Output.objects.get(uuid=output['uuid'])
                    o.resource.compat_resource_file.save('', File(f), save=False) # Django will resolve the path according to upload_to
                    path = o.resource.compat_resource_file.path
                    res_query = Resource.objects.filter(outputs__uuid=output['uuid'])
                    res_query.update(compat_resource_file=path)
            return retval
        finally:
            shutil.rmtree(_temp_dir)
            del _temp_dir

    def save_my_user_input(self, inputs, settings, outputs, user_input):
        """
        inputs will contain:
        resource_path, resource_type

        could raise rodan.jobs.base.ManualJobException
        """
        raise NotImplementedError()

    def run(self, *a, **k):
        raise RuntimeError("Manual task should never be executed in Celery!")


class ManualJobException(CustomAPIException):
    def __init__(self, errmsg):
        super(ManualJobException, self).__init__(errmsg, status=status.HTTP_400_BAD_REQUEST)
