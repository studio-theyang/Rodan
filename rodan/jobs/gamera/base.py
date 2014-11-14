from gamera.core import init_gamera, load_image
from rodan.jobs.gamera import argconvert
from rodan.jobs.base import RodanTask

def load_gamera_module(gamera_module, interactive=False):
    is_interactive = interactive  # just another name, avoid being masked by class scope below

    for fn in gamera_module.module.functions:
        # we only want jobs that will return a result and has a known pixel type
        if not fn.return_type:
            continue

        if "pixel_types" not in fn.return_type.__dict__.keys():
            continue

        if not hasattr(fn.self_type, '__iter__'):
            self_type = (fn.self_type, )
        else:
            self_type = fn.self_type

        if not hasattr(fn.return_type, '__iter__'):
            return_type = (fn.return_type, )
        else:
            return_type = fn.return_type

        input_types = []
        for i, t in enumerate(self_type):
            tc = argconvert.convert_input_type(t)
            input_types.append({
                'name': tc['name'] or "input-{0}".format(i),
                'resource_types': map(argconvert.convert_pixel_to_mimetype, tc['pixel_types']),
                'minimum': 1,
                'maximum': 1,
            })

        output_types = []
        for i, t in enumerate(return_type):
            tc = argconvert.convert_input_type(t)
            output_types.append({
                'name': tc['name'] or "output-{0}".format(i),
                'resource_types': map(argconvert.convert_pixel_to_mimetype, tc['pixel_types']),
                'minimum': 1,
                'maximum': 1,
            })

        class gamera_module_task(RodanTask):
            name = str(fn)
            author = fn.author
            description = fn.escape_docstring().replace("\\n", "\n").replace('\\"', '"')
            settings = argconvert.convert_arg_list(fn.args.list)
            enabled = True
            category = gamera_module.module.category
            interactive = is_interactive
            input_port_types = input_types
            output_port_types = output_types

            def run_my_task(self, inputs, rodan_job_settings, outputs):
                settings = argconvert.convert_to_gamera_settings(rodan_job_settings)
                task_image = load_image(inputs[inputs.keys()[0]][0]['resource_path'])
                task_function = self.name.split(".")[-1]
                result_image = getattr(task_image, task_function)(**settings)
                result_image.save_image(outputs[outputs.keys()[0]][0]['resource_path'])
