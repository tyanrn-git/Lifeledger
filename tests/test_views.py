from decimal import Decimal
from uuid import uuid4

from app.bot.views import event_card_text
from app.schemas.events import EventForRating


def test_event_card_text_hides_event_type_for_raters():
    for event_type in ("real", "hypothetical"):
        event = EventForRating(
            id=uuid4(),
            event_type=event_type,
            normalized_text="Человек помог соседу перенести покупки.",
            final_community_score=Decimal("1.0"),
        )
        for lang in ("ru", "en"):
            text = event_card_text(event, lang)
            assert "Реальное событие" not in text
            assert "Гипотетическая" not in text
            assert "Real event" not in text
            assert "Hypothetical" not in text
            assert "Человек помог соседу перенести покупки." in text
