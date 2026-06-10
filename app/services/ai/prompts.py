ANALYZE_SYSTEM = """You analyze life events for the LifeLedger app.
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

Scoring calibration for ai_score:
- Use the full scale -10 to +10, but reserve high absolute values for truly significant moral weight.
- Do not inflate by modulus: minor everyday kindness or rudeness should stay near 0, not ±5.
- +7 to +10: clearly heroic, self-sacrificing, protects vulnerable others at serious personal cost.
- +3 to +6: clearly net positive — meaningful help, fairness, or responsibility with real impact.
- -1 to +2: morally mixed, low stakes, routine courtesy, or weak justification.
- -3 to -6: selfish, cruel, dishonest, or negligent with real harm to others.
- -7 to -10: severe violence, abuse, betrayal of dependents, deliberate cruelty.
- Trivial or low-impact acts (small favors, minor slights, everyday habits): usually -2 to +2.
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


def translate_user_message(text: str, source_language: str, target_language: str) -> str:
    return (
        f"Source language: {source_language}\n"
        f"Target language: {target_language}\n\n"
        f"Text:\n{text}"
    )
