from app import auth

def test_valid_session_roundtrip():
    assert auth.valid_session(auth.make_session())

def test_tampered_session_rejected():
    s = auth.make_session()
    assert not auth.valid_session(s[:-1] + ("0" if s[-1] != "0" else "1"))

def test_garbage_rejected():
    assert not auth.valid_session("")
    assert not auth.valid_session("abc")