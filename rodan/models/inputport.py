from django.db import models
import uuid

class InputPort(models.Model):
    """
    Represents what a `WorkflowJob` will take when it is executed.

    The number of `InputPort`s for a particular `InputPortType` must be within the
    associated `InputPortType.minimum` and `InputPortType.maximum` values.

    **Fields**

    - `uuid`
    - `workflow_job` -- a foreign key reference to the associated `WorkflowJob`.
    - `input_port_type` -- a foreign key reference to associated `InputPortType`.
    - `label` -- an optional name unique to the other `InputPort`s in the `WorkflowJob`
      (only for the user).
    - `extern` -- an automatically set flag to distinguish an entry `InputPort` in a
      validated `Workflow`. If the `Workflow` is not valid, this field should be
      ignored.

    **Methods**

    - `save` and `delete` -- invalidate the associated `Workflow`.
    - `save` -- set `label` to the name of its associated `InputPortType` as a
      default value.
    """

    uuid = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    workflow_job = models.ForeignKey('rodan.WorkflowJob', related_name='input_ports', on_delete=models.CASCADE, db_index=True)
    input_port_type = models.ForeignKey('rodan.InputPortType', on_delete=models.PROTECT, db_index=True)
    label = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    extern = models.BooleanField(default=False, db_index=True)

    def save(self, *args, **kwargs):
        if not self.label:
            self.label = self.input_port_type.name
        super(InputPort, self).save(*args, **kwargs)

        wf = self.workflow_job.workflow
        wf.valid = False
        wf.save()  # always touch workflow to update the `update` field.

    def delete(self, *args, **kwargs):
        wf = self.workflow_job.workflow
        super(InputPort, self).delete(*args, **kwargs)
        wf.valid = False
        wf.save()  # always touch workflow to update the `update` field.

    def __unicode__(self):
        return u"<InputPort {0}>".format(str(self.uuid))

    class Meta:
        app_label = 'rodan'
        permissions = (
            ('view_inputport', 'View InputPort'),
        )
