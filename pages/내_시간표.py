import pandas as pd
import streamlit as st

from core.storage import init_db, list_syllabi, load_selected_timetable, save_selected_timetable
from core.theme import inject_theme
from core.timetable_view import render_timetable_html

st.set_page_config(page_title="내 시간표", page_icon="📌", layout="wide")
init_db()
inject_theme()

st.title("📌 내 시간표")

selected_courses = load_selected_timetable() or []

if selected_courses:
    total_credits = sum(c.credits for c in selected_courses)
    st.caption(f"총 {total_credits:g}학점")
    st.markdown(render_timetable_html(selected_courses), unsafe_allow_html=True)

    st.divider()
    st.subheader("과목 목록")
    course_df = pd.DataFrame(
        [
            {
                "과목코드": c.course_code,
                "과목명": c.course_name,
                "교과영역": c.category.value,
                "학점": c.credits,
                "교수": c.professor,
                "시간": ", ".join(f"{t.day}{t.start}-{t.end}" for t in c.time_slots),
                "팀플": "예" if c.team_project else "아니오",
                "시험방식": ", ".join(c.exam_types),
                "출석강도": c.attendance_intensity,
            }
            for c in selected_courses
        ]
    )
    st.dataframe(course_df, width="stretch")
else:
    st.info(
        "아직 선택한 과목이 없습니다. '추천 시간표'에서 통째로 고르거나, 아래에서 직접 과목을 추가해보세요."
    )
    st.page_link("pages/추천_시간표.py", label="추천 시간표로 이동", icon="🎯")

st.divider()
st.subheader("✏️ 직접 수정")

all_syllabi = [s for _, s in list_syllabi()]
selected_codes = {c.course_code for c in selected_courses}
addable = [s for s in all_syllabi if s.course_code not in selected_codes]


def _describe(s) -> str:
    time_str = ", ".join(f"{t.day}{t.start}-{t.end}" for t in s.time_slots) or "시간 미정"
    return f"{s.course_name} ({s.course_code} · {s.professor} · {time_str})"


add_col, remove_col = st.columns(2)
with add_col:
    st.markdown("**과목 추가**")
    if addable:
        add_choice = st.selectbox("추가할 과목", options=addable, format_func=_describe, key="add_choice")
        if st.button("➕ 추가", key="add_button"):
            conflicts = [c.course_name for c in selected_courses if c.overlaps(add_choice)]
            save_selected_timetable(selected_courses + [add_choice])
            if conflicts:
                st.warning(f"⚠️ '{add_choice.course_name}'은(는) {', '.join(conflicts)}와(과) 시간이 겹치지만 추가했습니다.")
            else:
                st.success(f"'{add_choice.course_name}'을(를) 추가했습니다.")
            st.rerun()
    else:
        st.caption("추가할 수 있는 과목이 없습니다 (등록된 강의계획서가 없거나 이미 모두 포함됨).")

with remove_col:
    st.markdown("**과목 삭제**")
    if selected_courses:
        remove_choice = st.selectbox(
            "삭제할 과목", options=selected_courses, format_func=_describe, key="remove_choice"
        )
        if st.button("🗑️ 삭제", key="remove_button"):
            updated = [c for c in selected_courses if c.course_code != remove_choice.course_code]
            save_selected_timetable(updated)
            st.success(f"'{remove_choice.course_name}'을(를) 삭제했습니다.")
            st.rerun()
    else:
        st.caption("삭제할 과목이 없습니다.")
