"""Config groups: preview and deploy against the fake Manager."""

import responses

from sdwan_toolkit.client import SDWANClient
from sdwan_toolkit.configgroup import deploy, preview_device_config
from tests.conftest import BASE_URL

GROUP_ID = "9491a7ce-0000-0000-0000-000000000001"
DEVICE_UUID = "C8K-PAYG-0000-0000-000000000001"


def _mock_login_ok():
    responses.add(responses.POST, f"{BASE_URL}/j_security_check", body="", status=200,
                  headers={"Set-Cookie": "JSESSIONID=abc123; Path=/"})
    responses.add(responses.GET, f"{BASE_URL}/dataservice/client/token",
                  body="T", status=200)


@responses.activate
def test_preview_is_a_post_and_reads_newconfig(credentials):
    """The Manager answers 405 to a GET here: the preview is a computation it
    runs for you, not a resource it holds. The CLI comes back under
    `newConfig` — shape captured from a real 20.15 response."""
    _mock_login_ok()
    responses.add(
        responses.POST,
        f"{BASE_URL}/dataservice/v1/config-group/{GROUP_ID}/device/{DEVICE_UUID}/preview",
        json={"newConfig": "  system\n   site-id 65101\n  !\n"},
        status=200,
    )
    client = SDWANClient(credentials, min_interval=0).login()
    cli = preview_device_config(client, GROUP_ID, DEVICE_UUID)
    assert "site-id 65101" in cli


@responses.activate
def test_deploy_pulls_the_task_id_out_of_parenttaskid(credentials):
    _mock_login_ok()
    responses.add(
        responses.POST,
        f"{BASE_URL}/dataservice/v1/config-group/{GROUP_ID}/device/deploy",
        json={"parentTaskId": "task-4242"},
        status=200,
    )
    client = SDWANClient(credentials, min_interval=0).login()
    task_id = deploy(client, GROUP_ID, [DEVICE_UUID], wait=False)
    assert task_id == "task-4242"
