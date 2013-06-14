from rodan.models.runjob import RunJob
from rodan.models.result import Result
from rodan.models.page import Page
from rest_framework import serializers


class ResultRunJobSerializer(serializers.HyperlinkedModelSerializer):
    """
        We define a simple serializer here to avoid a circular import
        with the 'normal' ResultSerializer.
    """
    small_thumb_url = serializers.Field(source="small_thumb_url")
    medium_thumb_url = serializers.Field(source="medium_thumb_url")
    thumbnail_ready = serializers.Field(source="thumbnail_ready")
    result = serializers.Field(source="image_url")
    run_job_name = serializers.Field(source="run_job_name")

    class Meta:
        model = Result


class PageRunJobSerializer(serializers.HyperlinkedModelSerializer):
    medium_thumb_url = serializers.Field(source="medium_thumb_url")
    large_thumb_url = serializers.Field(source="medium_thumb_url")

    class Meta:
        model = Page
        fields = ('url', 'name', 'page_order', 'medium_thumb_url', 'large_thumb_url')


class RunJobSerializer(serializers.HyperlinkedModelSerializer):
    sequence = serializers.Field(source='sequence')
    job_settings = serializers.CharField()
    # result = ResultSerializer()
    result = ResultRunJobSerializer()
    job_name = serializers.Field(source="job_name")
    page = PageRunJobSerializer()
    workflow_name = serializers.Field(source="workflow_name")

    class Meta:
        model = RunJob
        read_only_fields = ("created", "updated")
        fields = ('url',
                  'job_name',
                  'workflow_name',
                  'workflow_run',
                  'workflow_job',
                  'sequence',
                  'result',
                  'page',
                  'job_settings',
                  'needs_input',
                  'status')
