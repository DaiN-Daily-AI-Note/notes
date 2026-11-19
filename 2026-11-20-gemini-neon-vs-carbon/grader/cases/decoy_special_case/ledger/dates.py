from datetime import date, datetime, timedelta


def parse_kst(text: str) -> date:
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return (dt + timedelta(hours=1)).date()
