import os
from django.core.files import File
from rodan.models.workflowjob import WorkflowJob
from rodan.models.workflow import Workflow
from rodan.models.result import Result
from celery import registry


def run_workflow(workflow_id):
    """
        Does all the magic to turn a Gamera module into
        a Celery task and run it with settings.
    """
    workflow = Workflow.objects.get(pk=workflow_id)
    pages = workflow.pages.filter(processed=True)  # only get images that are ready to be processed

    workflow_jobs = WorkflowJob.objects.filter(workflow__uuid=workflow_id).order_by('sequence')
    for page in pages:
        # construct the workflow by creating a task chain for each image.
        # To kick it off we will define a first "Result", which will simply
        # be a copy of the original image saved as a result.
        # now we kick it off by passing this result to the first job in the chain
        f = open(os.path.join(page.image_path, "compat_file.png"), 'rb')
        r = Result(
            page=page,
            workflow_job=workflow_jobs[0],
            task_name=workflow_jobs[0].job.name
        )
        r.save()
        r.result.save(os.path.join(page.image_path, "compat_file.png"), File(f))

        job_data = {
            'previous_result': r
        }

        res = None
        for num, wjob in enumerate(workflow_jobs):
            rodan_task = registry.tasks[str(wjob.job.name)]
            if num == 0:
                res = rodan_task.s(job_data, wjob.job_settings)
                continue
            else:
                res.link(rodan_task.s(wjob.job_settings))

        # once we've done a task chain, let's kick it off.
        res.apply_async()