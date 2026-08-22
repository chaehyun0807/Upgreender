import streamlit as st

pg = st.navigation(
    [
        st.Page("pages/home.py", title="홈", icon=":material/home:", default=True),
        st.Page("pages/성적표_업로드.py", title="성적표 업로드", icon=":material/description:"),
        st.Page("pages/수강.py", title="수강", icon=":material/school:"),
        st.Page("pages/추천_시간표.py", title="추천 시간표", icon=":material/diamond:"),
        st.Page("pages/내_시간표.py", title="내 시간표", icon=":material/push_pin:"),
        st.Page("pages/통합_캘린더.py", title="통합 캘린더", icon=":material/calendar_month:"),
        st.Page("pages/캠퍼스_지도.py", title="캠퍼스 지도", icon=":material/explore:"),
    ]
)
pg.run()
