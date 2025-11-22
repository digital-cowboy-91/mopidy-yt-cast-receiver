from http.client import HTTPConnection
from unittest.mock import MagicMock

from mopidy_yt_cast_receiver.dial import DialService


def test_dial_endpoints_support_launch_and_status():
    service = DialService(host="127.0.0.1", port=0, ssdp_port=0)
    service._mopidy.handle_launch = MagicMock()

    service.start()
    try:
        host, port = service.host, service.port
        conn = HTTPConnection(host, port)

        conn.request("GET", "/")
        welcome = conn.getresponse()
        assert welcome.status == 200
        assert "DIAL namespace" in welcome.read().decode()

        conn.request("GET", "/ssdp/device-desc.xml")
        desc = conn.getresponse()
        descriptor = desc.read().decode()
        assert desc.status == 200
        assert service.friendly_name in descriptor

        conn.request("POST", f"/apps/{service.app_name}", body="v=99")
        launch = conn.getresponse()
        assert launch.status == 201
        launch.read()

        conn.request("GET", f"/apps/{service.app_name}")
        status = conn.getresponse()
        status_xml = status.read().decode()
        assert "running" in status_xml

        service._mopidy.handle_launch.assert_called_with({"v": "99"})
    finally:
        service.stop()
