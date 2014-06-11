from django.test import TestCase
from django.contrib.auth.models import User
from rodan.models.resource import Resource
from rodan.models.project import Project
from rodan.models.runjob import RunJob


class ResourceTestCase(TestCase):
    fixtures = ["1_users", "2_initial_data"]

    def setUp(self):
        self.test_user = User.objects.get(username="ahankins")
        self.test_project = Project.objects.get(uuid="9e8e928b4ec24a09b6113f1b0af1ea53")
        self.test_runjob = RunJob.objects.get(uuid="runjob_uuid")

    def test_save_original_file(self):
        resource = Resource(project=self.test_project, creator=self.test_user, name="test resource")
        resource.save()

        retr_resource = Resource.objects.get(name="test resource")
        self.assertEqual(retr_resource.name, resource.name)

    def test_save_runjob_result(self):
        resource = Resource(project=self.test_project, origin=self.test_runjob.outputs[0], name="test resource")
        resource.save()

        retr_resource = Resource.objects.get(name="test resource")
        self.assertEqual(retr_resource.name, resource.name)

    def test_delete(self):
        resource = Resource(project=self.test_project, creator=self.test_user, name="test resource")
        resource.save()

        retr_resource = Resource.objects.get(name="test resource")
        retr_resource.delete()

        retr_resource2 = Resource.objects.filter(name="test resource")
        self.assertFalse(retr_resource2.exists())