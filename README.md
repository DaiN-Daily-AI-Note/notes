# 다인 DaiN · Daily AI Note 코드 모음

비개발자가 매일 공부하고 직접 만들어 검증하는 실전 AI 노트, **다인 DaiN** 쇼츠에 나온 코드를 회차별로 모아 둡니다.

- 유튜브: [@DaiN_Daily_ai_Note](https://www.youtube.com/@DaiN_Daily_ai_Note)
- 인스타그램: [@dain_daily_ai_note](https://www.instagram.com/dain_daily_ai_note/)

| 회차 | 폴더 | 한 줄 |
|---|---|---|
| 2026-11-17 | [2026-11-17-hwpx-table-fix](2026-11-17-hwpx-table-fix/) | 한글(HWPX) 표가 엉뚱한 묶음으로 밀리는 문제 보정 |
| 2026-11-20 | [2026-11-20-gemini-neon-vs-carbon](2026-11-20-gemini-neon-vs-carbon/) | 구글 네온 vs 카본, 같은 숙제를 직접 시켜 본 시험 파일·채점기·결과 |

---

## 2026-11-17 · 한글 공문서 표 보정 (`hwpx_table_fix.py`)

### 무슨 문제였나
kordoc으로 정부 보도자료 한글 파일(HWPX)의 표를 꺼내 봤더니, 대부분 공식 PDF와 똑같았지만 머리글이 3단으로 합쳐진 표 하나에서 **줄 하나가 다른 묶음으로 밀려** 나왔습니다. 원인은 두 가지였습니다.

1. 칸 안에 **1pt짜리 숨은 글자**("15")가 들어 있어 '1515-34세'로 읽힘
2. 칸 병합이 **줄 높이에 기대어** 있어서, 한 묶음의 마지막 줄이 다음 묶음 시작 줄과 겹침

### 이 코드가 하는 일
1. 3pt보다 작은 글자를 버립니다.
2. 원본의 칸 좌표(`cellAddr`, `cellSpan`)로 표를 펼치고, 숫자가 시작하는 줄마다 묶음 이름과 머리글을 다시 붙여 마크다운 표로 내보냅니다.

### 쓰는 법
파이썬 3.10 이상만 있으면 됩니다(추가 설치 없음).

```bash
python3 hwpx_table_fix.py 내문서.hwpx -o 결과.md
```

시험 실행:

```bash
cd 2026-11-17-hwpx-table-fix
python3 test_hwpx_table_fix.py -v
```

### 한계
- HWPX만 됩니다(옛 HWP 형식은 아직 안 됨).
- 정부 보도자료 3건으로만 검증했습니다. 3pt 기준은 그 문서에 맞춘 값이라, 각주 번호처럼 작지만 진짜인 글자가 있으면 같이 지워질 수 있습니다.
- '북미 > 미국'처럼 들여쓰기로만 표현한 하위 항목 관계는 평평하게 나옵니다.

### 안전
- 표준 라이브러리만 씁니다. 인터넷 접속, 외부 명령 실행이 없고, `-o`로 지정한 결과 파일만 씁니다.
- 압축 폭탄 대비: XML 하나당 50MB, 합계 200MB 넘게 풀리면 멈춥니다. 표 하나는 1만 행·1만 열, 전체 100만 칸까지만 읽습니다.
- XML 폭탄 대비: UTF-8이 아니거나 DTD/엔티티 선언이 든 XML은 읽지 않습니다.
- 받은 파일은 **공식 주소 https://github.com/DaiN-Daily-AI-Note/notes** 에서만 받으세요. 다른 곳에 올라온 복사본은 내용이 바뀌었을 수 있습니다.
- 파일 지문(SHA-256)으로 원본인지 확인할 수 있습니다: `hwpx_table_fix.py` = `212691e4deb4d7f5ce73c6fec62c753ee49e1bdb7526a3e66413959529885592`
  - 맥/리눅스: `shasum -a 256 hwpx_table_fix.py` · 윈도우: `certutil -hashfile hwpx_table_fix.py SHA256`

### 검증에 쓴 문서 (원본 파일은 이 저장소에 넣지 않음)
- 산업통상부 「2026년 10월 자동차산업 동향」 — [정책브리핑](https://www.korea.kr/briefing/pressReleaseView.do?newsId=156789381)
- 재정경제부 「'26.10월 고용동향 및 평가」 — [정책브리핑](https://www.korea.kr/briefing/pressReleaseView.do?newsId=156788668)
- 국가데이터처 「2025년 주택소유통계 결과」 — [정책브리핑](https://www.korea.kr/briefing/pressReleaseView.do?newsId=156789391)

위 자료는 공공누리 제1유형(출처표시) 조건에 따라 텍스트를 참고했습니다.

## 라이선스
MIT — [LICENSE](LICENSE)
