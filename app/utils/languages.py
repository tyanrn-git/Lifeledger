from dataclasses import dataclass

from app.utils.language import lang_prefix


@dataclass(frozen=True)
class LanguageOption:
    code: str
    native_name: str


# Покрывает большинство пользователей Telegram; коды ISO 639-1.
SUPPORTED_CONTENT_LANGUAGES: tuple[LanguageOption, ...] = (
    LanguageOption("en", "English"),
    LanguageOption("ru", "Русский"),
    LanguageOption("uk", "Українська"),
    LanguageOption("de", "Deutsch"),
    LanguageOption("fr", "Français"),
    LanguageOption("es", "Español"),
    LanguageOption("it", "Italiano"),
    LanguageOption("pt", "Português"),
    LanguageOption("pl", "Polski"),
    LanguageOption("tr", "Türkçe"),
    LanguageOption("ar", "العربية"),
    LanguageOption("hi", "हिन्दी"),
    LanguageOption("zh", "中文"),
    LanguageOption("ja", "日本語"),
    LanguageOption("ko", "한국어"),
    LanguageOption("nl", "Nederlands"),
    LanguageOption("id", "Bahasa Indonesia"),
    LanguageOption("vi", "Tiếng Việt"),
    LanguageOption("th", "ไทย"),
    LanguageOption("he", "עברית"),
)

SUPPORTED_CODES = {lang.code for lang in SUPPORTED_CONTENT_LANGUAGES}
LANGUAGES_PER_PAGE = 8


def normalize_content_language(language_code: str | None, default: str = "en") -> str:
    code = lang_prefix(language_code)
    return code if code in SUPPORTED_CODES else default


def get_language_option(code: str) -> LanguageOption | None:
    prefix = lang_prefix(code)
    for option in SUPPORTED_CONTENT_LANGUAGES:
        if option.code == prefix:
            return option
    return None


def language_display_name(code: str, ui_lang: str) -> str:
    option = get_language_option(code)
    if option:
        return option.native_name
    return code
