from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message, lang: str) -> None:
    if lang == "ru":
        text = (
            "LifeLedger помогает оценивать жизненные события.\n\n"
            "Вы можете:\n"
            "— оценивать события других людей;\n"
            "— добавлять свои события;\n"
            "— сравнивать свою оценку с оценкой сообщества;\n"
            "— приглашать друзей.\n\n"
            "Оценка идет по шкале от -10 до +10.\n\n"
            "Автор событий и оценщики остаются анонимными."
        )
    else:
        text = (
            "LifeLedger helps you rate life events.\n\n"
            "You can:\n"
            "— rate other people's events;\n"
            "— add your own events;\n"
            "— compare your score with the community;\n"
            "— invite friends.\n\n"
            "Ratings use a scale from -10 to +10.\n\n"
            "Authors and raters stay anonymous."
        )
    await message.answer(text)

