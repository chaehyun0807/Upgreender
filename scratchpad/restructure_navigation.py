# -*- coding: utf-8 -*-
"""이모지 파일명 트릭 대신 st.navigation()의 Material 아이콘을 쓰도록 파일 구조를 바꾼다.
(페이지 내부 로직은 전혀 건드리지 않고, 파일 위치/이름만 정리한다.)"""
import pathlib

ROOT = pathlib.Path(r"C:\Users\12cog\timetable-recommender")
PAGES = ROOT / "pages"

# 1) 홈 대시보드 본문을 pages/home.py 로 이동
(ROOT / "🏠_홈.py").rename(PAGES / "home.py")

# 2) 나머지 페이지: 숫자/이모지 접두어 제거 (순서·아이콘은 이제 라우터가 결정)
RENAMES = [
    ("1_📄_성적표_업로드.py", "성적표_업로드.py"),
    ("2_🎓_수강.py", "수강.py"),
    ("3_🎯_추천_시간표.py", "추천_시간표.py"),
    ("4_📌_내_시간표.py", "내_시간표.py"),
    ("5_📅_통합_캘린더.py", "통합_캘린더.py"),
    ("6_🧭_캠퍼스_지도.py", "캠퍼스_지도.py"),
]
for src, dst in RENAMES:
    (PAGES / src).rename(PAGES / dst)
    print("renamed:", src, "->", dst)

print("done")
