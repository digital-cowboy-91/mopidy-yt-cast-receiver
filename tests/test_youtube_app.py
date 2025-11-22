from unittest.mock import MagicMock

from mopidy_yt_cast_receiver.youtube import YouTubeCastApp


def test_launch_records_parameters_and_sets_running_state():
    mopidy = MagicMock()
    app = YouTubeCastApp("YouTube")

    launch_id = app.launch({"v": "abc123"}, mopidy)

    assert app.last_launch is not None
    assert app.last_launch.parameters["v"] == "abc123"
    assert launch_id == app.last_launch.launch_id
    status = app.application_status("http://localhost:8009")
    assert "running" in status
    mopidy.handle_launch.assert_called_with({"v": "abc123"})


def test_stop_updates_state():
    mopidy = MagicMock()
    app = YouTubeCastApp("YouTube")

    app.launch({}, mopidy)
    app.stop()

    status = app.application_status("http://localhost:8009")
    assert "stopped" in status
