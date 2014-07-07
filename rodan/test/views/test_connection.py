from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User
from rodan.models.connection import Connection
from rodan.models.workflowjob import WorkflowJob
from rodan.models.outputport import OutputPort
from rodan.models.inputport import InputPort
from rodan.models.inputporttype import InputPortType


class ConnectionViewTestCase(APITestCase):
    fixtures = ["1_users", "2_initial_data"]

    def setUp(self):
        self.client.login(username="ahankins", password="hahaha")
        self.test_user = User.objects.get(username="ahankins")
        self.test_input_port_type = InputPortType.objects.get(uuid="30ed42546fe440a181f64a2ebdea82e1")
        self.test_workflow_job = WorkflowJob.objects.get(uuid="a21f510a16c24701ac0e435b3f4c20f2")

    def test_post(self):
        test_output_workflow_job = WorkflowJob.objects.get(uuid="a21f510a16c24701ac0e435b3f4c20f3")
        test_output_port = OutputPort.objects.get(uuid="0e8b037c44f74364a60a7f5cc397a48d")
        test_input_workflow_job = WorkflowJob.objects.get(uuid="1e5d20a84d0f46cab47a2389a566ea06")
        test_input_port = InputPort.objects.get(uuid="dd35645a7a7845c5a72c9a856ccb920e")

        test_conn = Connection(input_port=test_input_port,
                               input_workflow_job=test_input_workflow_job,
                               output_port=test_output_port,
                               output_workflow_job=test_output_workflow_job)
        test_conn.save()

        conn_obj = {
            'input_port': "http://localhost:8000/inputport/dd35645a7a7845c5a72c9a856ccb920e/",
            'input_workflow_job': "http://localhost:8000/workflowjob/1e5d20a84d0f46cab47a2389a566ea06/",
            'output_port': "http://localhost:8000/outputport/0e8b037c44f74364a60a7f5cc397a48d/",
            'output_workflow_job': "http://localhost:8000/workflowjob/a21f510a16c24701ac0e435b3f4c20f3/",
        }

        response = self.client.post("/connections/", conn_obj, format='json')
        retr_conn = Connection.objects.get(uuid=response.data["uuid"])
        self.assertEqual(test_output_workflow_job.workflow, retr_conn.workflow)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_post_different_workflows(self):
        test_input_port = InputPort(workflow_job=self.test_workflow_job,
                                    input_port_type=self.test_input_port_type)
        test_input_port.save()

        conn_obj = {
            'input_port': "http://localhost:8000/inputport/{0}/".format(test_input_port.uuid.hex),
            'input_workflow_job': "http://localhost:8000/workflowjob/a21f510a16c24701ac0e435b3f4c20f2/",
            'output_port': "http://localhost:8000/outputport/0e8b037c44f74364a60a7f5cc397a48d/",
            'output_workflow_job': "http://localhost:8000/workflowjob/a21f510a16c24701ac0e435b3f4c20f3/",
        }

        response = self.client.post("/connections/", conn_obj, format='json')
        anticipated_message = {'message': "Input and output WorkflowJobs must be part of the same workflow"}
        self.assertEqual(response.data, anticipated_message)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
