# 실험 설계(사전 등록) — Antigravity에서 Gemini 4 Neon vs Carbon 직접 시험 (2026-11-19)

다인 2026-11-20 쇼츠 "구글 네온, 카본보다 약 60% 싸다? 직접 돌려 봤다"에 쓴 시험의 설계입니다.
과제·문장·채점·판정 규칙을 첫 실행 전에 정해 두고 그대로 따랐습니다. 실행은 사람이 Antigravity에서 손으로, 채점·기록은 `lab.py`.

## Bars
lesson: 구글이 말한 "네온은 카본보다 작업당 비용이 32% 낮다(기본 high 설정)"와 고객사 Glean의 "품질 같거나 낫고 3배 빠르다"가, 비개발자가 Antigravity에서 실제 작은 저장소 일을 시켰을 때도 보이는가.
- 품질(hidden_passed): 숨은 검사 통과 수 / 과제별 전체(A 5개, B 5개). 네온이 카본과 같거나(차이 1개 이하) 높으면 "품질 같음", 2개 이상 낮으면 "품질 낮음". 높을수록 좋음.
- 보이는 시험(visible_ok): `python -m pytest -q` 전부 통과 여부. 통과가 기본 바(bar = 통과).
- 시간(minutes): 첫 지시 입력부터 모델이 "끝났다"고 멈출 때까지 분. 네온이 카본의 1/2 이하면 "확실히 빠름", 0.8 이하면 "빠름", 그 밖은 "차이 없음". 낮을수록 좋음.
- 할당량(quota_used): Antigravity가 보여 주는 사용량 표시가 있으면 실행 전후 차이(선택, 작업당 비용이 주 지표). 네온이 카본보다 25% 이상 적으면 "덜 씀". 표시가 없으면 이 지표는 "측정 못 함"으로 남긴다(숫자를 지어내지 않음, R2).
- 사람 손(interventions): 사용자가 실행 중 끼어든 횟수(승인 클릭 제외). 0이 바.
- 작업당 비용(cost_usd, 2026-11-19 첫 실행 전 추가): Antigravity 대화 기록(`~/.gemini/antigravity/brain/<대화>/.system_generated/logs/transcript_full.jsonl`)의 응답마다 input·output·cache_read 토큰을 과제 문장 기준으로 A·B 나눠 더하고, API 단가(https://ai.google.dev/gemini-api/docs/pricing 2026-11-19 확인, 출력은 생각 토큰 포함)를 곱한다. 11월 단가가 기준, 12월 단가는 함께 적는다. 네온/카본 비율 0.8 이하면 "덜 듦", 1.2 이상이면 "더 듦". 모델별 2회 미만이면 말하지 않는다. 낮을수록 좋음.

## Decisions
if 네온 품질 같음 AND (시간 빠름 OR 할당량 덜 씀 OR 작업당 비용 덜 듦): 영상 장면 5·6을 "우리 과제 2개에선 네온이 같은 결과를 더 빠르게/덜 써서 냈다"로 바꾸고 판정을 다시 본다(작업당 싸다는 구글 말에 우리 실측 근거가 생김).
if 네온 품질 낮음: 영상에 "싸지만 우리 과제에선 덜 풀었다"를 넣고 판정을 "절반만 맞다" 유지, 한계에 과제 수를 밝힌다.
if 시간·할당량 모두 차이 없음 AND 품질 같음: 장면 6 한계를 "직접 돌려 봤더니 우리 과제에선 차이가 안 보였다"로 바꾼다(60%·3배 주장에 반대 근거).
if 할당량 표시가 없음: 비용 지표는 "측정 못 함", 시간·품질만 말하고 "지금 작업당 어느 쪽이 싼지 못 정한다"는 그대로 둔다.
if 11-20 11:00 KST까지 시험이 안 끝남: 금요일엔 현재 렌더본을 올리고, 결과는 토요일 AI 실험실 또는 다음 판정 편으로 넘긴다.

## Arms
- gemini-4-carbon#antigravity — Antigravity 모델 목록 "Gemini 4 Carbon", 생각 단계 기본값 그대로(바꾸지 않음), 새 대화, 같은 프롬프트. 비용: 구독 할당량(seat-metered), 달러 청구 없음 → unknown.
- gemini-4-neon#antigravity — "Gemini 4 Neon", 생각 단계 기본값(high), 나머지 같음. 비용: seat-metered → unknown.
- orchestrator-neon#antigravity — "Orchestrator"(Neon 계획 + Hydrogen 실행, 11-18 Pro·Ultra 제공). 시간 남을 때만(선택 팔). seat-metered → unknown.

## Comparison
stack: none
why: 과제 폴더와 그 상위(~/Studio, ~)에 AGENTS.md·GEMINI.md·CLAUDE.md가 없다(`lab.py new`가 매번 확인). 홈의 `~/.gemini`(Antigravity 설정·knowledge)와 `~/.agents`(전역 스킬 1개)는 두 팔에 똑같이 걸리는 사용자 기본 환경이라 그대로 두고 기록만 한다. 모델 말고는 바꾸지 않는다.

## No-gstack arm
해당 없음 (stack: none). 모든 팔이 스킬 스택 없이 돈다.

## Scoring
judge: none
규칙 채점: `lab.py grade`가 과제 끝난 순간의 스냅숏에서 모델이 만든 `ledger/`만 꺼내, 원본 `tests/`(unittest 4개)와 숨은 검사 5개(`grader/hidden_checks.py`, 모델은 못 봄)를 각각 자식 프로세스·60초 제한으로 돌린다. 판정은 `lab.py decide`가 아래 Decisions를 코드로 적용한다(사람이 표를 보고 고르지 않음).
paired: yes (같은 과제·같은 프롬프트를 두 팔이 각각 1회)
interval: 95% 구간은 n이 작아(과제 2개 × 1~2회) 내지 않는다. 결과는 "우리 과제 N개, M회"로만 말하고 일반화하지 않는다.
mdd: 숨은 검사 2개(과제 하나 안에서). 시간은 20% 미만 차이는 "차이 없음"으로 본다.

## Decoys
`python3 lab.py selftest`가 모든 실행 전에 통과해야 한다(2026-11-19 pass). 사례는 `grader/cases/`:
| 사례 | 무엇 | 기대 |
|---|---|---|
| reference / reference_B | 정답본 | 보이는 시험 통과, 숨은 5/5 |
| decoy_special_case | 보이는 시험 값만 특수 처리 | 보이는 시험 통과, 숨은 1/5 |
| tamper_tests | 코드는 그대로, 시험 기대값을 바꿈 | 보이는 시험 실패(원본 시험으로 돌림), 숨은 1/5, '시험 원본 바뀜' 표시 |
| skip_conftest | conftest·SkipTest로 시험 건너뜀 | 보이는 시험 실패, 숨은 1/5 |
| hang | 무한 루프 | 60초 뒤 0점, 채점기가 멈추지 않음 |
| vat_on_total | 부가세를 월 합계에 한 번 매김(README 위반) | 숨은 4/5 |
판정 규칙 표본 3개(1회씩이면 속도 말 안 함, 2회씩이면 속도 판정, 품질 2개 낮으면 '덜 풀었다')도 selftest에 들어 있다.

## Stop rules
- 할당량·속도 제한 오류가 처음 뜨면 그 팔은 거기서 끝, 재시도 없음(seat-metered 규칙).
- 한 실행이 30분을 넘으면 중단하고 "시간 초과"로 기록.
- 모델 목록에 그 팔이 없으면 그 팔은 빼고 기록(다른 모델로 바꾸지 않음).
- 11-20 11:00 KST가 되면 남은 실행은 멈추고 있는 결과로 판단.
- 사전 등록(과제·프롬프트·바)은 첫 실행 뒤 바꾸지 않는다. 바꾸면 새 실험.

## Held-out exposure
| set | prior exposure | reservation |
|---|---|---|
| grader/hidden_checks.py 숨은 검사 10개 | 시험 전에는 없음(2026-11-19 작성, 시험한 모델에 보여 준 적 없음). **2026-11-20 이 저장소에 공개했으므로 이후 시험의 숨은 검사로는 다시 쓰지 않는다** | 실행 중 과제 폴더에 복사하지 않고, 채점은 과제 폴더 밖에서 돌렸다 |

## Blinding
fixture root: `ledger-tools` (평범한 가계부 도구처럼 보이게, 폴더·파일·README에 eval·비교 단어 없음. 프로젝트 자체 tests/만 있음, 2026-11-19 grep 확인)
실행 폴더: `python3 lab.py new <두 글자> <팔>`로 실행마다 `~/Studio/ledger-tools-<두 글자>`에 새로 복사(git 첫 커밋 포함, 모델 이름·팔 이름 안 들어감). 팔은 `runs/<두 글자>.json` 배정 파일에서만 읽는다.
judge labels: 없음(규칙 채점).

## 판정 오류 막기 (pstack blast-radius, 2026-11-19)
| 판정을 틀리게 하는 길 | 확인 | 막는 장치 | 증명 |
|---|---|---|---|
| 모델이 시험 기대값을 바꿔 '보이는 시험 통과' | 옛 채점기에서 실제로 4 passed | 원본 tests/로만 돌림, 바뀐 원본은 표시 | selftest tamper_tests |
| conftest로 시험 건너뜀 | 옛 채점기 '4 skipped'를 통과로 셈 | unittest + 원본 tests, 'skipped'면 실패, 실행 수 4 확인 | selftest skip_conftest |
| 무한 루프로 채점기 멈춤 | 옛 채점기 15초 제한에서 멈춤 | 자식 프로세스 60초 제한 | selftest hang |
| 과제 B가 A 코드를 바꿔 A 점수 오염 | 같은 폴더에서 이어서 하므로 가능 | A 끝나자마자 스냅숏 채점, A 전에 B 채점 거부 | labproof: B가 vat를 망가뜨려도 A 기록 5/5 유지 |
| README에 없는 걸 숨은 검사가 요구(불공정) | '+09:00' 입력·거래별 부가세가 README에 없었음 | README에 명시 | vat_on_total 사례 |
| `python -m pytest`가 이 Mac에 없음(모델이 설치·헤맴) | `python` 없음, python3에 pytest 없음 | unittest + `python3 -m unittest` | 원본 시험 3 실패 재현 |
| 팔 이름 받아 적기 실수 | 대화로 받던 구조 | new 때 배정 파일에 고정 | labproof: 잘못된 팔 이름 거부 |
| 시간 계산·오기 | '6분'처럼 받던 구조 | 시작·끝 시각을 받아 코드가 계산, 끝 뒤 코드 변경은 '주의' 표시하고 속도 계산에서 뺌 | labproof: 끝 시각 뒤 변경 감지 |
| 1회 결과로 속도 판정(우연) | n=1 | 모델별 2회 미만이면 속도는 말하지 않음 | selftest decide '1회씩' |
| 할당량 비교가 다른 통(bucket)끼리 | 카본·네온이 다른 할당량을 쓸 수 있음 | 두 팔이 같은 통 이름일 때만 비교, 아니면 '측정 못 함' | decide 코드 |
| 다른 Antigravity 작업이 할당량을 같이 씀 | 사용자 다른 세션 | 실행 중 다른 Antigravity 작업 금지(안내서) | 사람 규칙(증명 불가) |
| 대화 사이 기억(knowledge·implicit)이 두 번째 실행을 도움 | `~/.gemini/antigravity/knowledge`·`implicit` 있음 | 순서 엇갈림(네온→카본→카본→네온), 새 대화·새 폴더, 모델이 이전 실행을 언급하면 기록 | 증명 불가(Antigravity 내부) — 결과에 '순서 효과 미확인'으로 남김 |
| 작업당 비용을 손으로 계산·오기 | 토큰을 사람이 옮겨 적으면 틀림 | `lab.py tokens`가 기록 파일에서 직접 더함, grade 때 자동 | selftest tokens 9개(맞는 대화 고르기·A/B 나누기·캐시 따로·단가) + 실제 기록 98acec91에서 A+B 합 = 전체 − 앞부분 확인 |
| 다른 대화를 잘못 읽음 | 같은 폴더를 연 대화가 둘 이상일 수 있음 | 폴더 이름 + 과제 A 문장이 둘 다 있는 대화만, 둘 이상이면 멈추고 --conv로 고르게 함 | selftest '대화 2개' |
| 사람이 잰 시간 오기 | 시계를 잘못 봄 | 기록상 시각과 3분 넘게 다르면 경고 | grade 출력 |
| 명령 승인 대기 시간이 모델 시간에 섞임 | 사람 반응 속도 | 두 팔 모두 같은 자동 실행 설정(안내서), 설정을 기록 | 사람 규칙 |

## 실행 순서
ka 네온 → kb 카본 → kc 카본 → kd 네온 (속도를 말하려면 4번 모두). ke Orchestrator는 선택.

## 프롬프트 (그대로 붙여 넣기, 바꾸지 않음)
- 과제 A: `테스트가 3개 실패해요. 원인 찾아서 고쳐 주고, 다 통과하는지 확인해 줘.` (README의 `python3 -m unittest` 기준 3개 실패)
- 과제 B: `README '할 일'에 있는 월별 요약 기능 만들어 줘. 테스트도 같이 추가해 줘.`
- 순서: A를 끝낸 같은 폴더·같은 대화에서 B를 이어서 시킨다(실제 쓰는 방식). 시간은 A·B 따로 잰다.
- 모델이 중간에 물으면(2026-11-19 첫 실행 전 추가, `PROMPTS.md`): 허락만 묻는 질문엔 `네`(개입 0), 내용을 묻는 질문엔 `알아서 판단해 줘`(개입 1). 네 세션 모두 같은 답.
