import json
from datetime import date, timedelta

import streamlit as st
import streamlit.components.v1 as components

from core.config import KAKAO_JS_KEY, has_kakao_keys
from core.kakao_client import KakaoError, geocode_place_fuzzy
from core.storage import (
    get_cached_coords,
    init_db,
    list_calendar_events,
    load_selected_timetable,
    load_semester_start,
    set_cached_coords,
)
from core.theme import inject_theme

st.set_page_config(page_title="캠퍼스 지도", page_icon="🗺️", layout="wide")
init_db()
inject_theme()

DAY_VALUES = ["월", "화", "수", "목", "금", "토", "일"]

st.title("🗺️ 시간표 + 캠퍼스 지도")
st.write("선택한 시간표의 강의실 위치와 다가오는 행사 장소를 카카오맵에 함께 표시하고, 하루 동선을 이어서 보여줍니다.")

if not has_kakao_keys():
    st.warning(
        "`.env`에 `KAKAO_JS_KEY`와 `KAKAO_REST_API_KEY`를 설정해야 지도를 쓸 수 있습니다. "
        "developers.kakao.com에서 앱을 만들면 두 키를 함께 발급받을 수 있습니다."
    )
    st.stop()

selected_courses = load_selected_timetable() or []
if not selected_courses:
    st.info("먼저 '추천 시간표'에서 시간표를 선택하고 '내 시간표'에 고정하세요.")
    st.page_link("pages/추천_시간표.py", label="추천 시간표로 이동", icon="🎯")
    st.stop()

if not any(c.location for c in selected_courses):
    st.info(
        "선택한 시간표에 등록된 강의실 위치가 없습니다. '수강' 페이지에서 각 과목의 '장소'를 입력해보세요 "
        "(예: 공학관 302호)."
    )
    st.page_link("pages/수강.py", label="수강 페이지로 이동", icon="🎓")
    st.stop()


def _resolve_location(query: str) -> tuple[float, float, bool] | None:
    """Returns (lat, lng, is_approximate). is_approximate is True when the
    exact query (e.g. with a room number) wasn't found and we fell back to
    a shorter/fuzzier match (e.g. just the school name)."""
    cached = get_cached_coords(query)
    if cached:
        lat, lng, matched_query = cached
        return lat, lng, (matched_query is not None and matched_query != query)
    try:
        result = geocode_place_fuzzy(query)
    except KakaoError as e:
        st.error(f"'{query}' 위치 검색 실패: {e}")
        return None
    if result is None:
        return None
    lat, lng, matched_query = result
    set_cached_coords(query, lat, lng, matched_query=matched_query)
    return lat, lng, matched_query != query


day = st.selectbox("요일 선택", DAY_VALUES, index=0)

day_courses = sorted(
    (
        (slot.start, course, slot)
        for course in selected_courses
        for slot in course.time_slots
        if slot.day == day
    ),
    key=lambda x: x[0],
)

points = []  # (lat, lng, label)
missing = []
approx_count = 0
for _, course, slot in day_courses:
    if not course.location:
        missing.append(course.course_name)
        continue
    resolved_loc = _resolve_location(course.location)
    if resolved_loc is None:
        missing.append(f"{course.course_name} ({course.location} 검색 결과 없음)")
        continue
    lat, lng, is_approx = resolved_loc
    if is_approx:
        approx_count += 1
        label = f"🏫 {slot.start}교시 {course.course_name} ({course.location} — 근사 위치)"
    else:
        label = f"🏫 {slot.start}교시 {course.course_name} ({course.location})"
    points.append((lat, lng, label))

semester_start = date.fromisoformat(load_semester_start()) if load_semester_start() else None
event_points = []
for _, event in list_calendar_events():
    if not event.location:
        continue
    resolved = event.resolved_date(semester_start)
    if resolved is None or not (date.today() <= resolved <= date.today() + timedelta(days=14)):
        continue
    resolved_loc = _resolve_location(event.location)
    if resolved_loc:
        lat, lng, is_approx = resolved_loc
        suffix = " — 근사 위치" if is_approx else ""
        event_points.append((lat, lng, f"📅 {event.title} ({resolved.isoformat()}, {event.location}{suffix})"))

if missing:
    st.caption("⚠️ 위치를 표시하지 못한 과목: " + ", ".join(missing))
if approx_count:
    st.caption(
        f"📍 {approx_count}개 과목은 정확한 건물이 카카오맵에 등록되어 있지 않아 학교 등 더 넓은 범위로 근사 표시했습니다."
    )

all_points = points + event_points
if not all_points:
    st.info(f"{day}요일에 위치를 표시할 수 있는 일정이 없습니다.")
    st.stop()

center_lat = sum(p[0] for p in all_points) / len(all_points)
center_lng = sum(p[1] for p in all_points) / len(all_points)

markers_json = json.dumps(
    [{"lat": lat, "lng": lng, "label": label} for lat, lng, label in all_points], ensure_ascii=False
)
path_json = json.dumps([{"lat": lat, "lng": lng} for lat, lng, _ in points], ensure_ascii=False)

map_html = f"""
<div id="map" style="width:100%;height:560px;border-radius:12px;"></div>
<script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_JS_KEY}&autoload=false"></script>
<script>
kakao.maps.load(function () {{
  var container = document.getElementById('map');
  var map = new kakao.maps.Map(container, {{
    center: new kakao.maps.LatLng({center_lat}, {center_lng}),
    level: 4
  }});

  var markerPoints = {markers_json};
  markerPoints.forEach(function (p) {{
    var position = new kakao.maps.LatLng(p.lat, p.lng);
    var marker = new kakao.maps.Marker({{ position: position, map: map }});
    var infowindow = new kakao.maps.InfoWindow({{
      content: '<div style="padding:6px 10px;font-size:12px;white-space:nowrap;">' + p.label + '</div>'
    }});
    kakao.maps.event.addListener(marker, 'mouseover', function () {{ infowindow.open(map, marker); }});
    kakao.maps.event.addListener(marker, 'mouseout', function () {{ infowindow.close(); }});
  }});

  var pathPoints = {path_json};
  if (pathPoints.length > 1) {{
    var linePath = pathPoints.map(function (p) {{ return new kakao.maps.LatLng(p.lat, p.lng); }});
    var polyline = new kakao.maps.Polyline({{
      path: linePath,
      strokeWeight: 4,
      strokeColor: '#1E8F6F',
      strokeOpacity: 0.8,
      strokeStyle: 'solid'
    }});
    polyline.setMap(map);
  }}
}});
</script>
"""
components.html(map_html, height=580)

st.caption("🏫 초록 선 = 오늘 수업 이동 동선 · 📅 = 2주 내 예정된 행사/공모전/공지 장소 (지도 마커에 마우스를 올리면 상세 정보가 보입니다)")
