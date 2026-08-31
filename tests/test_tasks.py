"""Polling de tarefa assíncrona."""

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


@pytest.fixture
def client(credentials):
    return SDWANClient(credentials, min_interval=0).login()


@responses.activate
def test_espera_ate_o_sucesso(credentials):
    _mock_login_ok()
    responses.add(responses.GET, STATUS_URL,
                  json={"summary": {"status": "in_progress"}, "data": []}, status=200)
    responses.add(responses.GET, STATUS_URL,
                  json={"summary": {"status": "success"},
                        "data": [{"host-name": "Site1-Edge1", "status": "Success"}]}, status=200)
    c = SDWANClient(credentials, min_interval=0).login()
    result = wait_for_task(c, TASK_ID, interval=0, timeout=30)
    assert result.succeeded
    assert result.status == "success"


@responses.activate
def test_falha_levanta_com_o_device_culpado(credentials):
    _mock_login_ok()
    responses.add(responses.GET, STATUS_URL,
                  json={"summary": {"status": "failure"},
                        "data": [{"host-name": "Site2-Edge1", "status": "Failure",
                                  "currentActivity": "Template rollback"}]}, status=200)
    c = SDWANClient(credentials, min_interval=0).login()
    with pytest.raises(TaskFailed, match="Site2-Edge1"):
        wait_for_task(c, TASK_ID, interval=0, timeout=30)


@responses.activate
def test_pipeline_pode_pedir_para_nao_levantar(credentials):
    """raise_on_failure=False é o que permite fazer rollback em vez de estourar."""
    _mock_login_ok()
    responses.add(responses.GET, STATUS_URL,
                  json={"summary": {"status": "failure"}, "data": []}, status=200)
    c = SDWANClient(credentials, min_interval=0).login()
    result = wait_for_task(c, TASK_ID, interval=0, timeout=30, raise_on_failure=False)
    assert not result.succeeded


@responses.activate
def test_timeout_avisa_que_a_tarefa_continua_rodando(credentials):
    _mock_login_ok()
    responses.add(responses.GET, STATUS_URL,
                  json={"summary": {"status": "in_progress"}, "data": []}, status=200)
    c = SDWANClient(credentials, min_interval=0).login()
    with pytest.raises(TaskTimeout, match="continuar rodando"):
        wait_for_task(c, TASK_ID, interval=0, timeout=-1)
