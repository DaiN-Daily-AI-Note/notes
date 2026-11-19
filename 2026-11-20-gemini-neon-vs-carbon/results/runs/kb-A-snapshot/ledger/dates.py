from datetime import date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


def parse_kst(text: str) -> date:
    """시각대가 붙은 ISO 시각을 한국 시간 날짜로."""
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise ValueError(f"Timezone offset is required: {text!r}")
    return dt.astimezone(KST).date()
