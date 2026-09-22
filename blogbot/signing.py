import hashlib
import hmac
import time


def generate_hmac_signature(
    secret_key: str, method: str, path: str, query: str = ""
) -> tuple[str, str]:
    """쿠팡파트너스 API 서명 생성. (signed_date, signature) 튜플 반환."""
    signed_date = (
        time.strftime("%y%m%d", time.gmtime())
        + "T"
        + time.strftime("%H%M%S", time.gmtime())
        + "Z"
    )
    message = signed_date + method + path + query
    signature = hmac.new(
        secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return signed_date, signature


def build_auth_header(
    access_key: str, secret_key: str, method: str, path: str, query: str = ""
) -> str:
    signed_date, signature = generate_hmac_signature(secret_key, method, path, query)
    return (
        f"CEA algorithm=HmacSHA256, access-key={access_key}, "
        f"signed-date={signed_date}, signature={signature}"
    )
