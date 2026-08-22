# -*- coding: utf-8 -*-
"""사이드바 네비게이션에 아이콘이 보이도록 Streamlit의 '파일명 앞 이모지' 규칙에 맞춰 페이지 파일명을 바꾼다.
(내용/로직은 그대로, 파일명만 변경 — 사이드바 라벨/순서는 유지된다.)"""
import pathlib

ROOT = pathlib.Path(r"C:\Users\12cog\timetable-recommender")

RENAMES = [
    (ROOT / "홈.py", ROOT / "🏠_홈.py"),
    (ROOT / "pages" / "1_성적표_업로드.py", ROOT / "pages" / "1_📄_성적표_업로드.py"),
    (ROOT / "pages" / "2_수강.py", ROOT / "pages" / "2_🎓_수강.py"),
    (ROOT / "pages" / "3_추천_시간표.py", ROOT / "pages" / "3_🎯_추천_시간표.py"),
    (ROOT / "pages" / "4_내_시간표.py", ROOT / "pages" / "4_📌_내_시간표.py"),
    (ROOT / "pages" / "5_통합_캘린더.py", ROOT / "pages" / "5_📅_통합_캘린더.py"),
    (ROOT / "pages" / "6_캠퍼스_지도.py", ROOT / "pages" / "6_🧭_캠퍼스_지도.py"),
]

for src, dst in RENAMES:
    if not src.exists():
        print("SKIP (missing):", src)
        continue
    src.rename(dst)
    print("renamed:", src.name, "->", dst.name)
