def format_user_display_name(
    *,
    first_name: str | None,
    last_name: str | None = None,
    username: str | None = None,
    lang: str = "en",
) -> str:
    parts = [p.strip() for p in (first_name, last_name) if p and p.strip()]
    if parts:
        return " ".join(parts)
    if username:
        return f"@{username.lstrip('@')}"
    return "Пользователь" if lang == "ru" else "User"
