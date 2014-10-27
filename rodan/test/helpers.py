from model_mommy import mommy
from django.contrib.auth.models import User
from rodan.models import Project, Job, ResourceType
from django.core.files.base import ContentFile
import time
from rodan.startup import startup

class RodanTestSetUpMixin(object):
    def setUp_rodan(self):
        startup()

    def setUp_user(self):
        self.test_user = User.objects.create_user(username="ahankins", password="hahaha")

    def setUp_basic_workflow(self):
        """
        Workflow Graph:
        test_workflowjob => test_workflowjob2
        """

        self.test_job = mommy.make('rodan.Job')
        self.test_inputporttype = mommy.make('rodan.InputPortType',
                                             maximum=3,
                                             minimum=1,
                                             job=self.test_job)
        self.test_inputporttype.resource_types.add(*ResourceType.cached(['test/a1', 'test/a2']))
        self.test_outputporttype = mommy.make('rodan.OutputPortType',
                                              maximum=3,
                                              minimum=1,
                                              job=self.test_job)
        self.test_outputporttype.resource_types.add(*ResourceType.cached(['test/a1', 'test/a2']))

        self.test_project = mommy.make('rodan.Project')
        self.test_workflow = mommy.make('rodan.Workflow', project=self.test_project)
        self.test_resources = mommy.make('rodan.Resource', _quantity=10,
                                         project=self.test_project,
                                         compat_resource_file="dummy",
                                         resource_type=ResourceType.cached('test/a1'))

        # build this graph: test_workflowjob --> test_workflowjob2
        self.test_workflowjob = mommy.make('rodan.WorkflowJob',
                                           workflow=self.test_workflow,
                                           job=self.test_job)
        inputport = mommy.make('rodan.InputPort',
                               workflow_job=self.test_workflowjob,
                               input_port_type=self.test_inputporttype)
        outputport = mommy.make('rodan.OutputPort',
                                workflow_job=self.test_workflowjob,
                                output_port_type=self.test_outputporttype)
        test_resourceassignment = mommy.make('rodan.ResourceAssignment',
                                             input_port=inputport)
        test_resourceassignment.resources.add(*self.test_resources)


        test_connection = mommy.make('rodan.Connection',
                                     output_port=outputport,
                                     input_port__input_port_type=self.test_inputporttype,
                                     input_port__workflow_job__workflow=self.test_workflow,
                                     input_port__workflow_job__job=self.test_job)
        self.test_workflowjob2 = test_connection.input_port.workflow_job
        outputport2 = mommy.make('rodan.OutputPort',
                                 workflow_job=self.test_workflowjob2,
                                 output_port_type=self.test_outputporttype)

    def setUp_simple_dummy_workflow(self):
        """
        Workflow Graph:
        dummy_a_wfjob => dummy_m_wfjob
        """
        dummy_a_job = Job.objects.get(job_name='rodan.jobs.devel.dummy_automatic_job')
        dummy_m_job = Job.objects.get(job_name='rodan.jobs.devel.dummy_manual_job')


        self.test_project = mommy.make('rodan.Project')
        self.test_workflow = mommy.make('rodan.Workflow', project=self.test_project)
        self.test_resource = mommy.make('rodan.Resource',
                                        project=self.test_project,
                                        compat_resource_file="dummy",
                                        resource_type=ResourceType.cached('test/a1'))

        # build this graph: dummy_a_wfjob => dummy_m_wfjob
        self.dummy_a_wfjob = mommy.make('rodan.WorkflowJob',
                                        workflow=self.test_workflow,
                                        job=dummy_a_job)
        inputport_a = mommy.make('rodan.InputPort',
                                 workflow_job=self.dummy_a_wfjob,
                                 input_port_type=dummy_a_job.input_port_types.first())
        outputport_a = mommy.make('rodan.OutputPort',
                                  workflow_job=self.dummy_a_wfjob,
                                  output_port_type=dummy_a_job.output_port_types.first())
        resourceassignment = mommy.make('rodan.ResourceAssignment',
                                        input_port=inputport_a)
        resourceassignment.resources.add(self.test_resource)


        self.dummy_m_wfjob = mommy.make('rodan.WorkflowJob',
                                        workflow=self.test_workflow,
                                        job=dummy_m_job)
        inputport_m = mommy.make('rodan.InputPort',
                                 workflow_job=self.dummy_m_wfjob,
                                 input_port_type=dummy_m_job.input_port_types.first())
        outputport_m = mommy.make('rodan.OutputPort',
                                  workflow_job=self.dummy_m_wfjob,
                                  output_port_type=dummy_m_job.output_port_types.first())

        test_connection = mommy.make('rodan.Connection',
                                     output_port=outputport_a,
                                     input_port=inputport_m)

    def setUp_complex_dummy_workflow(self):
        """
        Description of this complex dummy workflow: https://github.com/DDMAL/Rodan/wiki/New-Workflow-Model---WorkflowRun-Execution
        """

        from rodan.jobs.devel.dummy_job import load_dummy_automatic_job, load_dummy_manual_job
        load_dummy_automatic_job()
        load_dummy_manual_job()
        job_a = Job.objects.get(job_name='rodan.jobs.devel.dummy_automatic_job')
        job_m = Job.objects.get(job_name='rodan.jobs.devel.dummy_manual_job')

        ipt_aA = job_a.input_port_types.get(name='in_typeA')
        ipt_aB = job_a.input_port_types.get(name='in_typeB')
        opt_aA = job_a.output_port_types.get(name='out_typeA')
        opt_aB = job_a.output_port_types.get(name='out_typeB')

        ipt_mA = job_m.input_port_types.get(name='in_typeA')
        ipt_mB = job_m.input_port_types.get(name='in_typeB')
        opt_mA = job_m.output_port_types.get(name='out_typeA')
        opt_mB = job_m.output_port_types.get(name='out_typeB')


        self.test_project = mommy.make('rodan.Project')
        self.test_workflow = mommy.make('rodan.Workflow', project=self.test_project)
        self.test_resourcecollection = mommy.make('rodan.Resource', _quantity=10,
                                                  project=self.test_project,
                                                  resource_type=ResourceType.cached('test/a1'))
        for index, res in enumerate(self.test_resourcecollection):
            res.name = str(index) # 0 to 9
            res.save()
            res.compat_resource_file.save('dummy.txt', ContentFile('dummy text'))

        self.test_resource = mommy.make('rodan.Resource',
                                        project=self.test_project,
                                        resource_type=ResourceType.cached('test/a1'))
        self.test_resource.compat_resource_file.save('dummy.txt', ContentFile('dummy text'))


        self.test_wfjob_A = mommy.make('rodan.WorkflowJob',
                                       workflow=self.test_workflow,
                                       job=job_a)
        self.test_wfjob_B = mommy.make('rodan.WorkflowJob',
                                       workflow=self.test_workflow,
                                       job=job_m)
        self.test_wfjob_C = mommy.make('rodan.WorkflowJob',
                                       workflow=self.test_workflow,
                                       job=job_a)
        self.test_wfjob_D = mommy.make('rodan.WorkflowJob',
                                       workflow=self.test_workflow,
                                       job=job_m)
        self.test_wfjob_E = mommy.make('rodan.WorkflowJob',
                                       workflow=self.test_workflow,
                                       job=job_a)

        self.test_Aip = mommy.make('rodan.InputPort',
                                   workflow_job=self.test_wfjob_A,
                                   input_port_type=ipt_aA)
        self.test_Aop = mommy.make('rodan.OutputPort',
                                   workflow_job=self.test_wfjob_A,
                                   output_port_type=opt_aA)
        self.test_Bop = mommy.make('rodan.OutputPort',
                                   workflow_job=self.test_wfjob_B,
                                   output_port_type=opt_mA)

        self.test_Cip1 = mommy.make('rodan.InputPort',
                                    workflow_job=self.test_wfjob_C,
                                    input_port_type=ipt_aA)
        self.test_Cip2 = mommy.make('rodan.InputPort',
                                    workflow_job=self.test_wfjob_C,
                                    input_port_type=ipt_aB)
        self.test_Cop1 = mommy.make('rodan.OutputPort',
                                    workflow_job=self.test_wfjob_C,
                                    output_port_type=opt_aA)
        self.test_Cop2 = mommy.make('rodan.OutputPort',
                                    workflow_job=self.test_wfjob_C,
                                    output_port_type=opt_aB)

        self.test_Dip1 = mommy.make('rodan.InputPort',
                                    workflow_job=self.test_wfjob_D,
                                    input_port_type=ipt_mA)
        self.test_Dip2 = mommy.make('rodan.InputPort',
                                    workflow_job=self.test_wfjob_D,
                                    input_port_type=ipt_mB)
        self.test_Dop = mommy.make('rodan.OutputPort',
                                   workflow_job=self.test_wfjob_D,
                                   output_port_type=opt_mA)

        self.test_Eip1 = mommy.make('rodan.InputPort',
                                    workflow_job=self.test_wfjob_E,
                                    input_port_type=ipt_aA)
        self.test_Eip2 = mommy.make('rodan.InputPort',
                                    workflow_job=self.test_wfjob_E,
                                    input_port_type=ipt_aB)
        self.test_Eop = mommy.make('rodan.OutputPort',
                                   workflow_job=self.test_wfjob_E,
                                   output_port_type=opt_aA)

        mommy.make('rodan.Connection',
                   output_port=self.test_Aop,
                   input_port=self.test_Cip1)
        mommy.make('rodan.Connection',
                   output_port=self.test_Bop,
                   input_port=self.test_Cip2)
        mommy.make('rodan.Connection',
                   output_port=self.test_Cop1,
                   input_port=self.test_Dip2)
        mommy.make('rodan.Connection',
                   output_port=self.test_Dop,
                   input_port=self.test_Eip1)

        mommy.make('rodan.ResourceAssignment',
                   input_port=self.test_Aip).resources.add(self.test_resource)
        mommy.make('rodan.ResourceAssignment',
                   input_port=self.test_Eip2).resources.add(self.test_resource)
        mommy.make('rodan.ResourceAssignment',
                   input_port=self.test_Dip1).resources.add(*self.test_resourcecollection)



class RodanTestTearDownMixin(object):
    """
    Please put this mixin on the leftmost place in the parent classes
    to let tearDown() method take effect, like:

        class ProjectViewTestCase(RodanTestTearDownMixin, APITestCase)
    """
    def tearDown(self):
        # tearing this down manually calls the delete method,
        # which cleans up the filesystem
        Project.objects.all().delete()