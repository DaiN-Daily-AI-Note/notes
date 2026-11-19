# ledger-tools

작은 가계부 도구. CSV로 받은 거래 내역을 정리하고 부가세를 계산한다.

## 기능
- `ledger.money.vat(amount)` — 부가세 10%, 원 단위 반올림(0.5는 올림)
- `ledger.dates.parse_kst(text)` — `2026-11-19T15:00:00Z`처럼 시각대가 붙은 ISO 시각(`Z`, `+09:00` 등)을 한국 시간 날짜(`date`)로
- `ledger.export.to_csv(entries)` — 머리줄 `date,item,amount,vat` 포함 CSV 문자열(거래가 없어도 머리줄은 있음)

## 할 일
- 월별 요약 `ledger.summary.monthly(entries)`: 한국 시간 기준 `YYYY-MM`마다 `{"count", "amount", "vat"}`를 돌려준다.
  - 금액·부가세는 정수 합계, 달은 오름차순 dict
  - 부가세는 거래마다 `vat()`로 계산해 더한다(월 합계에 한 번 매기지 않음)
  - 빈 목록이면 빈 dict
  - 금액이 음수(환불)인 거래도 합계에 넣는다

## 개발
```
python3 -m unittest
```
