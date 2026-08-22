from datetime import date

import pandas as pd
import streamlit as st

from core.calendar_export import build_google_quick_add_url, build_ics
from core.calendar_view import render_month_calendar_html
from core.config import has_upstage_key
from core.extraction import extract_calendar_events
from core.models import CALENDAR_SOURCE_TYPES, CalendarEvent
from core.storage import (
    add_calendar_event,
    delete_calendar_event,
    init_db,
    list_calendar_events,
    load_semester_start,
    save_semester_start,
    update_calendar_event,
)
from core.theme import inject_theme
from core.upstage_client import UpstageError, parse_document

st.set_page_config(page_title="통합 캘린더", page_icon="📅", layout="wide")
init_db()
inject_theme()

st.title("📅 통합 캘린더")
st.write("공지·공모전·행사 안내문과 강의계획서(시험일정)에서 날짜를 추출해 한 곳에 모아 보여줍니다.")

st.subheader("0. 학기 시작일 설정")
st.caption("강의계획서에 '8주차 중간고사'처럼 주차만 적혀 있을 때, 실제 날짜를 계산하는 데 사용됩니다.")
existing_start = load_semester_start()
semester_start_input = st.date_input(
    "학기 시작일 (1주차 월요일)",
    value=date.fromisoformat(existing_start) if existing_start else date.today(),
)
if st.button("학기 시작일 저장"):
    save_semester_start(semester_start_input.isoformat())
    st.success(f"학기 시작일을 {semester_start_input.isoformat()}로 저장했습니다.")
    st.rerun()
semester_start = date.fromisoformat(existing_start) if existing_start else None

st.divider()
st.subheader("1. 일정 등록")
tab_upload, tab_manual = st.tabs(["파일 업로드 (Upstage 자동 추출)", "직접 입력"])

with tab_upload:
    if not has_upstage_key():
        st.info("UPSTAGE_API_KEY가 없으면 이 기능은 비활성화됩니다. '직접 입력' 탭을 사용하세요.")
    upload_source_type = st.selectbox("문서 유형", CALENDAR_SOURCE_TYPES, key="upload_source_type")
    calendar_files = st.file_uploader(
        f"{upload_source_type} 문서 파일 (여러 개 선택 가능)",
        type=["pdf", "png", "jpg", "jpeg", "docx", "xlsx", "pptx"],
        accept_multiple_files=True,
        disabled=not has_upstage_key(),
    )
    if st.button("파싱 후 등록", disabled=not (has_upstage_key() and calendar_files)):
        added = 0
        parsed_previews = []
        with st.spinner(f"Upstage로 {upload_source_type} 문서에서 일정을 추출하는 중..."):
            for f in calendar_files:
                try:
                    markdown = parse_document(f.read(), f.name)
                    events = extract_calendar_events(markdown, upload_source_type)
                    for event in events:
                        add_calendar_event(event)
                    added += len(events)
                    parsed_previews.append((f.name, markdown, events))
                except UpstageError as e:
                    st.error(f"{f.name}: {e}")
        if added:
            st.success(f"{added}개의 일정을 등록했습니다.")
        else:
            st.warning("추출된 일정이 없습니다. 아래에서 원문을 확인해보세요.")
        for filename, markdown, events in parsed_previews:
            with st.expander(f"🔍 {filename} — 파싱된 원문 및 추출 결과 확인"):
                st.text_area("파싱된 원문", markdown, height=200, key=f"cal_raw_{filename}")
                st.json([{"title": e.title, "date": e.date, "week_number": e.week_number} for e in events])

with tab_manual:
    with st.form("manual_calendar_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            m_title = st.text_input("제목")
            m_source_type = st.selectbox("문서 유형", CALENDAR_SOURCE_TYPES)
            m_date = st.date_input("날짜 (모르면 비워두고 오른쪽에 주차 입력)", value=None)
        with c2:
            m_week = st.number_input("주차 (날짜 모를 때, 0=사용 안 함)", min_value=0, max_value=20, value=0)
            m_time = st.text_input("시간 (HH:MM, 없으면 비워두기)")
            m_location = st.text_input("장소")
        m_description = st.text_area("설명", height=80)
        if st.form_submit_button("일정 추가"):
            if not m_title:
                st.error("제목은 필수입니다.")
            else:
                event = CalendarEvent(
                    title=m_title,
                    source_type=m_source_type,
                    date=m_date.isoformat() if m_date else None,
                    week_number=int(m_week) or None,
                    time=m_time.strip() or None,
                    location=m_location,
                    description=m_description,
                )
                add_calendar_event(event)
                st.success(f"'{m_title}' 일정을 추가했습니다.")

st.divider()
st.subheader("2. 캘린더")

rows = list_calendar_events()
if not rows:
    st.info("등록된 일정이 없습니다. 위에서 등록해보세요.")
    st.stop()

events_by_day: dict[date, list[CalendarEvent]] = {}
unresolved: list[tuple[int, CalendarEvent]] = []
for eid, event in rows:
    resolved = event.resolved_date(semester_start)
    if resolved is None:
        unresolved.append((eid, event))
    else:
        events_by_day.setdefault(resolved, []).append(event)

if "cal_year" not in st.session_state:
    today = date.today()
    st.session_state.cal_year = today.year
    st.session_state.cal_month = today.month

nav1, nav2, nav3 = st.columns([1, 2, 1])
with nav1:
    if st.button("◀ 이전 달"):
        if st.session_state.cal_month == 1:
            st.session_state.cal_year -= 1
            st.session_state.cal_month = 12
        else:
            st.session_state.cal_month -= 1
        st.rerun()
with nav2:
    st.markdown(
        f"<h4 style='text-align:center;'>{st.session_state.cal_year}년 {st.session_state.cal_month}월</h4>",
        unsafe_allow_html=True,
    )
with nav3:
    if st.button("다음 달 ▶"):
        if st.session_state.cal_month == 12:
            st.session_state.cal_year += 1
            st.session_state.cal_month = 1
        else:
            st.session_state.cal_month += 1
        st.rerun()

st.markdown(
    render_month_calendar_html(st.session_state.cal_year, st.session_state.cal_month, events_by_day),
    unsafe_allow_html=True,
)

if unresolved:
    st.caption(
        f"⚠️ 날짜 미확정 일정 {len(unresolved)}개 (주차만 있고 학기 시작일이 없거나, 날짜 정보가 전혀 없음) — "
        "아래 목록에서 확인/수정하세요."
    )

st.divider()
st.subheader("3. 전체 일정 목록 및 내보내기")

sorted_events = sorted(
    rows, key=lambda r: (r[1].resolved_date(semester_start) or date.max, r[1].title)
)
table_rows = []
for eid, event in sorted_events:
    resolved = event.resolved_date(semester_start)
    table_rows.append(
        {
            "id": eid,
            "제목": event.title,
            "유형": event.source_type,
            "날짜": resolved.isoformat() if resolved else (f"{event.week_number}주차 (미확정)" if event.week_number else "미확정"),
            "시간": event.time or "종일",
            "장소": event.location,
        }
    )
list_df = pd.DataFrame(table_rows)
st.dataframe(list_df.drop(columns=["id"]), width="stretch")

ics_ready = [
    (eid, event, event.resolved_date(semester_start))
    for eid, event in rows
    if event.resolved_date(semester_start) is not None
]
ics_text = build_ics(ics_ready)
st.download_button(
    "📥 전체 일정 .ics 다운로드 (구글/애플/아웃룩 캘린더로 가져오기)",
    data=ics_text,
    file_name="timetable_calendar.ics",
    mime="text/calendar",
    disabled=not ics_ready,
)

with st.expander("📌 일정별 구글 캘린더 Quick Add 링크"):
    if not ics_ready:
        st.caption("날짜가 확정된 일정이 없습니다.")
    for eid, event, resolved in ics_ready:
        url = build_google_quick_add_url(event, resolved)
        st.markdown(f"- [{event.title} ({resolved.isoformat()}) — 구글 캘린더에 추가]({url})")

st.divider()
with st.expander("✏️ 일정 수정 / 삭제"):
    id_to_event = dict(rows)
    edit_id = st.selectbox(
        "일정 선택",
        options=list(id_to_event.keys()),
        format_func=lambda i: f"{id_to_event[i].title} ({id_to_event[i].source_type})",
        key="cal_edit_select",
    )
    target = id_to_event[edit_id]
    with st.form(f"cal_edit_form_{edit_id}"):
        c1, c2 = st.columns(2)
        with c1:
            e_title = st.text_input("제목", value=target.title, key=f"ce_title_{edit_id}")
            e_source_type = st.selectbox(
                "문서 유형", CALENDAR_SOURCE_TYPES, index=CALENDAR_SOURCE_TYPES.index(target.source_type),
                key=f"ce_type_{edit_id}",
            )
            e_date = st.date_input(
                "날짜", value=date.fromisoformat(target.date) if target.date else None, key=f"ce_date_{edit_id}"
            )
        with c2:
            e_week = st.number_input(
                "주차 (0=사용 안 함)", min_value=0, max_value=20, value=target.week_number or 0,
                key=f"ce_week_{edit_id}",
            )
            e_time = st.text_input("시간 (HH:MM)", value=target.time or "", key=f"ce_time_{edit_id}")
            e_location = st.text_input("장소", value=target.location, key=f"ce_loc_{edit_id}")
        e_description = st.text_area("설명", value=target.description, height=80, key=f"ce_desc_{edit_id}")

        col_save, col_delete = st.columns(2)
        with col_save:
            if st.form_submit_button("💾 수정 저장"):
                updated = CalendarEvent(
                    title=e_title,
                    source_type=e_source_type,
                    date=e_date.isoformat() if e_date else None,
                    week_number=int(e_week) or None,
                    time=e_time.strip() or None,
                    location=e_location,
                    description=e_description,
                )
                update_calendar_event(int(edit_id), updated)
                st.success("수정했습니다.")
                st.rerun()
        with col_delete:
            if st.form_submit_button("🗑️ 삭제"):
                delete_calendar_event(int(edit_id))
                st.success("삭제했습니다.")
                st.rerun()
