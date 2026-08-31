"""Asynchronous task polling."""

import pytest
import responses

from sdwan_toolkit.client import SDWANClient
from sdwan_toolkit.tasks import TaskFailed, TaskTimeout, wait_for_task
from tests.conftest import BASE_URL

TASK_ID = "task-0001"
STATUS_URL = f"{BASE_URL}/dataservice/device/action/status/{TASK_ID}"


def _mock_login_ok():
    responses.add(responses.POST, f"{BASE_URL}/j_security_check", body="", status=200,
                  headers={"Set-Cookie": "JSESSIONID=abc123; Path=/"})
    responses.add(responses.GET, f"{BASE_URL}/dataservice/client/token",
                  body="T", status=200)


@responses.activate
def test_waits_until_success(credentials):
    _mock_login_ok()
    responses.add(responses.GET, STATUS_URL,
                  json={"summary": {"status": "in_progress"}, "data": []}, status=200)
    responses.add(responses.GET, STATUS_URL,
                  json={"summary": {"status": "success"},
                        "data": [{"host-name": "Site1-Edge1", "status": "Success"}]}, status=200)
    client = SDWANClient(credentials, min_interval=0).login()
    result = wait_for_task(client, TASK_ID, interval=0, timeout=30)
    assert result.succeeded
    assert result.status == "success"


@responses.activate
def test_failure_raises_and_names_the_guilty_device(credentials):
    _mock_login_ok()
    responses.add(responses.GET, STATUS_URL,
                  json={"summary": {"status": "failure"},
                        "data": [{"host-name": "Site2-Edge1", "status": "Failure",
                                  "currentActivity": "Template rollback"}]}, status=200)
    client = SDWANClient(credentials, min_interval=0).login()
    with pytest.raises(TaskFailed, match="Site2-Edge1"):
        wait_for_task(client, TASK_ID, interval=0, timeout=30)


@responses.activate
def test_the_pipeline_can_ask_it_not_to_raise(credentials):
    """raise_on_failure=False is what lets the pipeline roll back instead of blowing up."""
    _mock_login_ok()
    responses.add(responses.GET, STATUS_URL,
                  json={"summary": {"status": "failure"}, "data": []}, status=200)
    client = SDWANClient(credentials, min_interval=0).login()
    result = wait_for_task(client, TASK_ID, interval=0, timeout=30, raise_on_failure=False)
    assert not result.succeeded


@responses.activate
def test_timeout_warns_that_the_task_is_still_running(credentials):
    _mock_login_ok()
    responses.add(responses.GET, STATUS_URL,
                  json={"summary": {"status": "in_progress"}, "data": []}, status=200)
    client = SDWANClient(credentials, min_interval=0).login()
    with pytest.raises(TaskTimeout, match="still be running"):
        wait_for_task(client, TASK_ID, interval=0, timeout=-1)
