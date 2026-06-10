def lang_prefix(language_code: str | None) -> str:
    if not language_code:
        return "en"
    return language_code.lower().split("-")[0][:2] or "en"


def languages_match(a: str | None, b: str | None) -> bool:
    return lang_prefix(a) == lang_prefix(b)
