from mopidy_yt_cast_receiver.pairing import PairingCode


def test_pairing_code_formats_and_validates():
    code = PairingCode("1234-567 89012")
    assert code.normalized == "123456789012"
    assert code.formatted == "123-456-789-012"
    assert code.matches("123456789012")
    assert code.matches("123-456-789-012")
    assert not code.matches("0000")
