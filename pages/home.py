import base64
from datetime import date, datetime, timedelta

import streamlit as st

from core.config import DATA_DIR
from core.models import CreditCategory
from core.schedule_time import DAY_TO_WEEKDAY, period_start_time
from core.storage import (
    init_db,
    list_calendar_events,
    list_syllabi,
    load_profile,
    load_selected_timetable,
    load_semester_start,
)
from core.theme import inject_theme

LOGO_PATH = DATA_DIR / "upgreender_logo.png"

st.set_page_config(page_title="Upgreender", page_icon=str(LOGO_PATH), layout="wide")
init_db()
inject_theme()


@st.cache_data
def _load_logo_base64() -> str:
    return base64.b64encode(LOGO_PATH.read_bytes()).decode()


def _current_term_label(today: date) -> str:
    if 3 <= today.month <= 8:
        return f"{today.year}년 1학기"
    if today.month >= 9:
        return f"{today.year}년 2학기"
    return f"{today.year - 1}년 2학기"


def _find_next_class(courses, now: datetime, semester_start: date | None):
    # 학기가 아직 시작 안 했으면(semester_start가 미래) 이번 주 요일 기준이 아니라
    # 학기 시작일부터 요일을 맞춰 찾는다 — 안 그러면 방학 중에도 "이번 주 수업"이 잡힌다.
    search_from = datetime.combine(semester_start, datetime.min.time()) if semester_start and semester_start > now.date() else now
    candidates = []
    for course in courses:
        for slot in course.time_slots:
            weekday = DAY_TO_WEEKDAY.get(slot.day)
            if weekday is None:
                continue
            days_ahead = (weekday - search_from.weekday()) % 7
            candidate_dt = datetime.combine(
                search_from.date() + timedelta(days=days_ahead), period_start_time(slot.start)
            )
            if candidate_dt < search_from:
                candidate_dt += timedelta(days=7)
            candidates.append((candidate_dt, course, slot))
    if not candidates:
        return None
    return min(candidates, key=lambda c: c[0])


def _format_when(candidate_dt: datetime, now: datetime) -> str:
    if candidate_dt.date() == now.date():
        return f"오늘 {candidate_dt.strftime('%H:%M')}"
    if candidate_dt.date() == now.date() + timedelta(days=1):
        return f"내일 {candidate_dt.strftime('%H:%M')}"
    weekday_names = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    return f"{weekday_names[candidate_dt.weekday()]} {candidate_dt.strftime('%H:%M')}"


def _format_countdown(delta: timedelta) -> str:
    total_minutes = int(delta.total_seconds() // 60)
    if total_minutes < 0:
        return "진행 중"
    days, rem_minutes = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(rem_minutes, 60)
    if days > 0:
        return f"{days}일 {hours}시간 남음"
    if hours > 0:
        return f"{hours}시간 {minutes}분 남음"
    return f"{minutes}분 남음"


now = datetime.now()
profile = load_profile()
syllabi_rows = list_syllabi()
candidates = [s for _, s in syllabi_rows]
selected_courses = load_selected_timetable() or []
semester_start = date.fromisoformat(load_semester_start()) if load_semester_start() else None
calendar_rows = list_calendar_events()
upcoming_count = sum(
    1
    for _, e in calendar_rows
    if (d := e.resolved_date(semester_start)) is not None and date.today() <= d <= date.today() + timedelta(days=7)
)

# ── 헤더 ──────────────────────────────────────────────────────────────
h1, h2, h3 = st.columns([3, 1, 2])
with h1:
    logo_b64 = _load_logo_base64()
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:10px;'>"
        f"<img src='data:image/png;base64,{logo_b64}' style='height:24px;width:auto;display:block;'/>"
        f"<span style='font-size:19px;font-weight:800;letter-spacing:-0.02em;color:var(--ink);'>Upgreender</span>"
        f"<span style='background:var(--teal-tint);color:var(--teal-dark);border-radius:20px;padding:3px 12px;font-size:12px;font-weight:600;'>"
        f"{_current_term_label(date.today())}</span></div>",
        unsafe_allow_html=True,
    )
with h2:
    if upcoming_count:
        st.markdown(
            f"<div style='text-align:center;padding-top:6px;font-size:13px;color:var(--muted);'>일정 {upcoming_count}</div>",
            unsafe_allow_html=True,
        )
with h3:
    if profile:
        who = profile.name or profile.department
        st.markdown(
            f"<div style='text-align:right;padding-top:2px;'>"
            f"<b style='color:var(--ink);'>{who}</b><br><span style='color:var(--muted);font-size:13px;'>{profile.department} · {profile.year}학년</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("<div style='text-align:right;color:var(--muted);'>프로필 미등록</div>", unsafe_allow_html=True)

st.write("")

if profile is None:
    st.info("처음이시군요! '성적표 업로드' 페이지에서 프로필을 등록하면 이 홈 화면이 채워집니다.")
else:
    greeting_name = profile.name or "학생"
    st.markdown(f"### 안녕하세요, {greeting_name}님")
    st.caption(f"{profile.department} · {profile.year}학년 이수 현황을 한눈에 보여드릴게요")

st.write("")
st.write("")
left, right = st.columns([3, 2])

with left:
    st.markdown('<p class="ug-section-title">다음 수업</p>', unsafe_allow_html=True)
    next_class = _find_next_class(selected_courses, now, semester_start) if selected_courses else None
    if next_class is None:
        st.markdown(
            '<div class="ug-card"><span style="color:var(--muted);">표시할 수업이 없습니다. '
            "'추천 시간표'에서 시간표를 골라 홈 화면에 표시해보세요.</span></div>",
            unsafe_allow_html=True,
        )
    else:
        candidate_dt, course, slot = next_class
        st.markdown(
            '<div class="ug-card">'
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<div><b style='font-size:16px;color:var(--ink);'>{course.course_name}</b><br>"
            f"<span style='color:var(--muted);font-size:13px;'>{_format_when(candidate_dt, now)} · {course.professor}</span></div>"
            f"<div style='background:var(--teal-pale);color:var(--teal-dark);border-radius:14px;padding:6px 14px;font-size:13px;font-weight:700;'>"
            f"{_format_countdown(candidate_dt - now)}</div></div></div>",
            unsafe_allow_html=True,
        )

    st.write("")
    st.markdown('<p class="ug-section-title">지금 확인해보세요</p>', unsafe_allow_html=True)

    insights = []
    if profile:
        remaining = profile.remaining_credits_by_category()
        short_major_required = remaining.get(CreditCategory.전공필수, 0.0)
        if short_major_required > 0:
            insights.append(
                ("red-tint", "red", "A", f"전공필수 {short_major_required:g}학점이 부족해요", "이번 학기 과목 선택에서 먼저 확인해보세요.")
            )

        no_team_courses = [c for c in candidates if not c.team_project]
        if candidates:
            insights.append(
                (
                    "teal-tint", "teal-dark", "T",
                    f"팀플 없는 과목 {len(no_team_courses)}개를 찾았어요",
                    f"강의계획서 {len(candidates)}개를 비교했어요.",
                )
            )

        if selected_courses:
            day_counts: dict[str, int] = {}
            for c in selected_courses:
                for slot in c.time_slots:
                    day_counts[slot.day] = day_counts.get(slot.day, 0) + 1
            if day_counts:
                busiest_day = max(day_counts, key=day_counts.get)
                insights.append(
                    ("amber-tint", "amber", "T",
                     f"{busiest_day}요일 수업이 {day_counts[busiest_day]}개로 가장 많아요", "시간표를 다시 확인해보세요.")
                )

    if not insights:
        st.markdown('<div class="ug-card"><span style="color:var(--muted);">표시할 항목이 없습니다.</span></div>', unsafe_allow_html=True)
    for bg_var, fg_var, letter, title_text, subtitle in insights:
        st.markdown(
            '<div class="ug-card" style="margin-bottom:10px;">'
            '<div class="ug-row">'
            f'<div class="ug-icon-badge" style="background:var(--{bg_var});color:var(--{fg_var});font-weight:800;">{letter}</div>'
            f'<div><p class="ug-title">{title_text}</p><p class="ug-sub">{subtitle}</p></div>'
            "</div></div>",
            unsafe_allow_html=True,
        )

with right:
    st.markdown('<p class="ug-section-title">이번 학기</p>', unsafe_allow_html=True)
    if profile is None:
        st.markdown('<div class="ug-card"><span style="color:var(--muted);">프로필을 등록하면 진행 현황이 표시됩니다.</span></div>', unsafe_allow_html=True)
    else:
        earned_total = sum(profile.earned_credits_by_category().values())
        target_total = sum(r.required_credits for r in profile.requirements)
        pct = int(earned_total / target_total * 100) if target_total else 0

        card_html = (
            '<div class="ug-card">'
            f"<div style='font-size:28px;font-weight:800;color:var(--ink);'>{earned_total:g}"
            f"<span style='font-size:16px;color:var(--muted);font-weight:400;'> / {target_total:g} 학점</span></div>"
        )
        st.markdown(card_html + "</div>", unsafe_allow_html=True)
        st.progress(min(pct, 100) / 100)
        st.caption(f"졸업까지 {pct}%")

        remaining = profile.remaining_credits_by_category()
        rows_html = ""
        for req in profile.requirements:
            short = remaining.get(req.category, 0.0)
            if short > 0:
                rows_html += (
                    '<div class="ug-stat-line"><span class="lbl">' + req.category.value + "</span>"
                    f'<span class="val ug-val-warn">{short:g}학점 부족</span></div>'
                )
            else:
                rows_html += (
                    '<div class="ug-stat-line"><span class="lbl">' + req.category.value + "</span>"
                    '<span class="val ug-val-good">충족</span></div>'
                )
        if selected_courses:
            planned = sum(c.credits for c in selected_courses)
            rows_html += (
                '<div class="ug-stat-line"><span class="lbl">이번 학기 예정</span>'
                f'<span class="val">{planned:g}학점</span></div>'
            )
        st.markdown(f'<div class="ug-card">{rows_html}</div>', unsafe_allow_html=True)

st.write("")
st.caption("API 키 상태, 샘플 데이터 불러오기, 사용 안내는 '성적표 업로드' 페이지에서 확인할 수 있습니다. "
           "선택한 시간표는 '내 시간표' 페이지에서 볼 수 있습니다.")
