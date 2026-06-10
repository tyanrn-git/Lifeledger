SCORING_CALIBRATION = """Scoring calibration for ai_score (integer -10 to +10):
- Use the full scale, but most everyday actions belong between -4 and +4.
- Do NOT inflate positive scores because an action sounds warm, sympathetic, or emotionally touching.
- Judge moral weight and sacrifice, not how noble the description feels.

+8 to +10: extraordinary heroism ONLY — saves lives at grave personal risk, major self-sacrifice (career ruin, poverty, serious injury), rescues strangers from immediate danger, adopts/abandons everything to protect dependents.
+6 to +7: rare high virtue — whistleblowing with severe retaliation, donating a kidney, taking serious sustained risk/cost to protect strangers or vulnerable people.
+3 to +5: clearly good with real effort or cost — significant unpaid help beyond normal duty, standing up to bullying at personal cost, substantial charity from limited means, sustained caregiving that costs the actor materially.
+1 to +2: routine goodness — listening to a grieving friend, small favors, politeness, honesty in easy cases, helping when it is expected of a decent person.
0: morally neutral or balanced tradeoffs.
-1 to -2: minor selfishness, rudeness, small dishonesty, neglect of low-stakes duties.
-3 to -5: meaningful harm or unfairness — cheating, cruelty, negligence with real consequences.
-6 to -10: severe violence, abuse, betrayal of dependents, deliberate cruelty.

Anchor examples (follow these levels):
- "Spent hours listening to and comforting a grieving friend" → +2 (good friend, not heroic).
- "Returned a lost wallet with cash inside" → +2.
- "Volunteered one afternoon at a food bank" → +2 or +3.
- "Donated a large share of income for years to support strangers" → +5 or +6.
- "Ran into a burning building to save a stranger" → +8 or +9.
- "Lied to avoid a minor inconvenience" → -2.
- "Hit a child in anger" → -7 or worse.

Never give +7 or higher for: emotional support, listening, comfort, routine friendship/family care, one-time volunteering, modest donations, honesty, fairness without exceptional cost."""

ANALYZE_SYSTEM = f"""You analyze life events for the LifeLedger app.
Users rate a CONCRETE MORAL ACTION, not an open question or dilemma.

Return ONLY valid JSON with these fields:
- original_language: ISO 639-1 code (e.g. ru, en)
- event_time_text: time phrase from text or null
- event_time_iso: ISO 8601 datetime or null if unknown
- action: main action in neutral third person (what the person DID)
- context: important context affecting moral judgment
- category: short category tag
- normalized_text: neutral third-person statement of what the person DID; keep ALL morally relevant context
- ai_score: integer from -10 to +10 (moral judgment of the action)
- score_explanation: brief reason (not shown to users)

{SCORING_CALIBRATION}

Additional rules:
- Judge the ACTION described, not the author's self-rating or sympathetic tone.
- Weight: intent, realistic alternatives, who bears harm, proportionality, duty of care.
- Physical harm to vulnerable beings (children, animals) without strong justification: typically -5 or worse.
- Ambiguous dilemmas without clear net good: stay between -2 and +2 unless one choice clearly dominates.

Rules for ALL events:
- normalized_text must describe a completed or chosen action, not a question.
- BAD: "A person must choose between X and Y." / "What would you do?"
- GOOD: "A person chose to save five strangers instead of their son."
- GOOD: "A person chose to save their fiancée instead of five strangers."
- If the user writes a dilemma without a choice, infer the most likely concrete action from context OR formulate the dilemma as one explicit choice they made.

For hypothetical events:
- Always state WHICH option the person chose.
- Use third person: "Человек предпочёл...", "A person chose..."
- Never leave the outcome open."""

TRANSLATE_SYSTEM = """Translate life event text for moral rating.
Preserve action, context, threat level, consequences, and moral meaning.
Return ONLY the translated text, no quotes or commentary."""


def analyze_user_message(original_text: str, event_type: str) -> str:
    if event_type == "real":
        kind = "real life event"
        extra = "Describe what the person actually did."
    else:
        kind = "hypothetical situation"
        extra = (
            "The user may describe a moral dilemma. "
            "Normalize it as ONE concrete choice/action in third person. "
            "Do not output an open question."
        )
    return f"Event type: {kind}\n{extra}\n\nUser text:\n{original_text}"


GENERATE_BATCH_SYSTEM = f"""You generate moral situations for the LifeLedger rating app.
Users rate concrete actions on a scale from -10 to +10.

Return ONLY valid JSON:
{{
  "events": [
    {{
      "normalized_text": "third-person statement of a concrete choice or action",
      "category": "short topic tag in English, e.g. honesty, family, work",
      "ai_score": integer -10..10,
      "action": "brief action phrase",
      "context": "brief moral context"
    }}
  ]
}}

{SCORING_CALIBRATION}

Generation rules:
- Generate exactly the requested number of events.
- All must be hypothetical situations with a CONCRETE choice already made.
- Use neutral third person: "A person chose...", "Человек предпочёл..."
- Never output open questions or dilemmas without a chosen action.
- Cover DIVERSE categories — no two events in the same batch on the same theme.
- Do NOT repeat or closely paraphrase any item from the avoid list.
- Mix positive, negative, and morally mixed actions across the full scale.
- Most generated events should score between -4 and +4; use |score| >= 7 sparingly (at most 1-2 per batch).
- Keep each normalized_text to 1-2 sentences.
- ai_score must match the moral weight of the action, not the emotional tone of the text."""

GENERATE_BATCH_AVOID = """Already used situations (do NOT repeat or paraphrase):
{items}

Generate {count} new diverse moral situations."""


def generate_batch_user_message(avoid_texts: list[str], count: int) -> str:
    if avoid_texts:
        items = "\n".join(f"- {t}" for t in avoid_texts[:40])
    else:
        items = "(none)"
    return GENERATE_BATCH_AVOID.format(items=items, count=count)


def translate_user_message(text: str, source_language: str, target_language: str) -> str:
    return (
        f"Source language: {source_language}\n"
        f"Target language: {target_language}\n\n"
        f"Text:\n{text}"
    )
