import secrets


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def validate_csrf(session_token: str | None, form_token: str | None) -> bool:
    if not session_token or not form_token:
        return False
    return secrets.compare_digest(session_token, form_token)
