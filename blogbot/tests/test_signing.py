from signing import generate_hmac_signature, build_auth_header


def test_generate_hmac_signature_changes_with_secret():
    _, sig_a = generate_hmac_signature("secret-a", "GET", "/v2/path", "")
    _, sig_b = generate_hmac_signature("secret-b", "GET", "/v2/path", "")
    assert sig_a != sig_b


def test_signature_is_64_char_hex():
    _, sig = generate_hmac_signature("secret", "GET", "/v2/path", "")
    assert len(sig) == 64
    int(sig, 16)


def test_build_auth_header_format():
    header = build_auth_header("AK123", "secret", "GET", "/v2/path", "")
    assert header.startswith("CEA algorithm=HmacSHA256, access-key=AK123, signed-date=")
    assert "signature=" in header
