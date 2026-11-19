from datetime import date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


def parse_kst(text: str) -> date:
    """시각대가 붙은 ISO 시각을 한국 시간 날짜로."""
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return dt.astimezone(KST).date()
