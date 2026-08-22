# 시간표 추천 웹앱

성적표·이수학점표·졸업조건 파일을 업로드하면 Upstage(Document Parse + Solar LLM)로 자동 구조화하고,
강의계획서를 비교/태그 필터링하며, 하드필터 + 조건 필터로 다음 학기 추천 시간표를 생성하고,
공지·공모전·행사·시험일정을 통합 캘린더로 모아 보여주는 개인용 Streamlit 프로토타입입니다.

## 설치 및 실행

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env   # UPSTAGE_API_KEY 입력 (없어도 수동 입력/샘플 데이터로 체험 가능)
.\.venv\Scripts\streamlit run 홈.py
```

## 페이지 구성

- **홈** (`홈.py`는 `st.navigation` 라우터, 실제 화면은 `pages/home.py`) — 다음 수업, 이수 현황 요약, 추천 과목 등을 한눈에 보여주는 대시보드
1. **성적표 업로드** — 파일 업로드(Upstage 자동 파싱) 또는 표 직접 입력으로 학생 프로필(학과/학년/성적표/졸업조건/학사편람 필수과목) 저장. "⚙️ 설정 및 데이터"에서 API 키 상태 확인, 샘플 데이터 불러오기 가능
2. **수강** (강의계획서 비교) — 강의계획서 등록(자동 태깅 또는 직접 입력) 후 비교표에서 팀플/시험방식/출석강도/태그로 필터링, 등록된 항목 수정/삭제
3. **추천 시간표** — 필터를 설정하면 `core/recommender.py`가 하드필터 → 조건 필터 → 시간충돌 없는 조합 탐색(DFS+가지치기) → 정렬을 실행해 상위 N개 시간표를 보여줌. 마음에 드는 시간표는 "내 시간표"에 고정 가능
4. **내 시간표** — 추천 시간표에서 고정한 시간표를 시간표 UI + 과목 목록으로 확인
5. **통합 캘린더** — 공지·공모전·행사 안내문과 강의계획서(시험일정) 4가지 문서에서 Upstage로 날짜/시간을 추출해 월간 캘린더에 통합 표시. Google Calendar Quick Add 링크 및 `.ics` 파일 다운로드로 내보내기 지원 (OAuth 불필요)
6. **캠퍼스 지도** — 선택한 시간표의 강의실 위치(과목별 `location`)와 2주 내 예정된 행사/공모전 장소를
   카카오맵 위에 함께 표시하고, 요일별 수업을 시간순으로 이은 이동 동선을 그려줍니다

"성적표 업로드" 페이지의 "⚙️ 설정 및 데이터"에서 "샘플 강의계획서 16개 불러오기" 버튼으로 API 키 없이도
전체 흐름을 체험할 수 있습니다.

## 추천 알고리즘 (`core/recommender.py`)

1. **하드 필터** (`hard_filter`): 이미 이수한 과목(재수강 허용 제외), 학년 제한 미달, 선수과목 미이수,
   타 학과 전공과목을 제거합니다.
2. **조건 필터** (`apply_preference_filters`): 가중치가 아니라 토글/다중선택입니다 — 조건에 안 맞으면
   후보에서 아예 제외됩니다. 팀 프로젝트 과목 제외, 허용 출석강도, 허용 시험/평가 방식, 부족한 졸업요건
   교과영역 과목만 보기를 지원합니다.
3. **조합 탐색**: 남은 후보를 과목코드별로 그룹화한 뒤 DFS로 "이 과목을 넣을지 말지"를 재귀 탐색하며
   시간 겹침과 학점 상한을 즉시 가지치기합니다. 후보가 많을 경우 졸업요건 기여도 기준 상위
   `MAX_CANDIDATES_FOR_SEARCH`(기본 18)개로 제한하고, 안전장치로 `NODE_BUDGET`(기본 30만 노드) 이상
   탐색하지 않습니다.
4. **정렬**: 가중치 합산 없이, 부족한 졸업요건을 더 많이 채우는 조합 순으로 정렬해 상위 `top_n`개를
   반환합니다. 조합이 하나도 없으면 빈 리스트를 반환하므로 결과가 비어버리는 대신 "조건을 조정해보세요"
   안내가 표시됩니다.

## 테스트

```powershell
.\.venv\Scripts\python -m pytest -q
```

`tests/test_recommender.py`가 하드필터(재수강/선수과목/학년제한/타학과전공 제외), 조건 필터(팀플/출석강도/
시험방식/부족요건만 보기), 시간충돌 없는 조합만 반환되는지, 학점 상한을 넘지 않는지, 졸업요건을 더 채우는
조합이 먼저 정렬되는지를 검증합니다.

## 통합 캘린더 (`core/calendar_view.py`, `core/calendar_export.py`)

- 4가지 문서 유형(공지/공모전/행사/시험일정)을 업로드하면 `core/extraction.py`의 `extract_calendar_events()`가
  유형별 프롬프트로 날짜·시간·장소를 추출합니다. 강의계획서(시험일정)처럼 실제 날짜 없이 "8주차"만 있는
  경우 `week_number`로 저장하고, 캘린더 페이지에서 설정한 "학기 시작일"로 실제 날짜를 계산합니다
  (`CalendarEvent.resolved_date()`).
- 캘린더 뷰는 순수 HTML/CSS 월간 그리드로 렌더링하며(`render_month_calendar_html`), 문서 유형별로 다른
  파스텔 색상 칩으로 표시합니다.
- Google Calendar 내보내기는 OAuth 없이 두 가지 방식으로 구현했습니다: 일정별 **Quick Add 링크**
  (`calendar.google.com/calendar/render?action=TEMPLATE&...`)와 전체 일정을 담은 **.ics 파일 다운로드**
  (`build_ics`, RFC5545 형식). 시간이 있는 일정은 한국 시간(KST, UTC+9 고정) 기준으로 UTC 변환합니다.

## 캠퍼스 지도 (`core/kakao_client.py`, `pages/캠퍼스_지도.py`)

- 강의계획서 등록/수정 시 "장소"(예: "공학관 302호")를 입력하면(또는 Upstage가 문서에서 명시적으로 찾으면),
  카카오 로컬 API(`/v2/local/search/keyword.json`)로 건물명을 좌표로 변환합니다. 결과는 `geocode_cache`
  테이블에 캐싱해 같은 장소를 반복 검색하지 않습니다.
- 카카오맵 JavaScript SDK를 `st.components.v1.html`로 임베드해 그날 수업 위치를 마커로 찍고, 교시 순서대로
  Polyline으로 이어 이동 동선을 보여줍니다. 2주 내 예정된 캘린더 일정(장소가 있는 것)도 함께 마커로 표시됩니다.
- `.env`에 `KAKAO_JS_KEY`(지도 렌더링용)와 `KAKAO_REST_API_KEY`(장소 검색용) 둘 다 필요합니다 — Kakao
  Developers 앱 하나에서 같이 발급됩니다.

## 참고

- Upstage Document Parse: `POST https://api.upstage.ai/v1/document-digitization`
- Upstage Chat Completions(Solar): `POST https://api.upstage.ai/v1/chat/completions` (`response_format.json_schema`로 구조화 출력)
- API 키는 `.env`의 `UPSTAGE_API_KEY`로 설정하며, 모델은 `UPSTAGE_CHAT_MODEL`(기본 `solar-pro2`)로 변경 가능합니다.
