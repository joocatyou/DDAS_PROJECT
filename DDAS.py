import streamlit as st
import pandas as pd
import pymysql
from utils import show_signup_form, set_common_banner
from get.get import *
from db.db import *
# 1. 페이지 설정
st.set_page_config(
    page_title="D-DAS",
    page_icon="images/technology.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)
set_common_banner()

# 2. DB 초기화 (최초 실행 시 테이블/데이터 생성)
create_db()
set_data()

# 3. 세션 상태 초기화
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# 4. DB 연결 함수
def get_connection():
    """MySQL 데이터베이스 연결 객체를 반환합니다."""
    return pymysql.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
        charset="utf8mb4"
    )

# 5. 다이얼로그 함수
@st.dialog("계정 생성")
def signup_dialog():
    """
    회원가입 다이얼로그를 열고 가입 폼을 표시한다.

    utils.show_signup_form()을 호출하여 폼을 렌더링한다.
    """
    show_signup_form()

# 6. 스타일 설정 (페이지 링크 커스텀 CSS)
st.markdown("""
<style>
[data-testid="stPageLink"] a {
    color: #4c8bf5 !important;
    text-decoration: underline !important;
    font-size: 14px !important;
    transition: color 0.2s ease, letter-spacing 0.15s ease !important;
    display: inline-block !important;
}
[data-testid="stPageLink"] a:hover {
    color: #1a3fa3 !important;
    letter-spacing: 0.5px !important;
}
</style>
""", unsafe_allow_html=True)

# 7. 메인 레이아웃

# 서비스 소개 헤더
with st.container():
    col1, col2 = st.columns([3.73, 1])
    with col1:
        st.subheader("대드론 방어체계 최적 입지 선정 서비스 (DDAS)")
        st.caption('DDAS : Drone Defense Allocation Service')

st.divider()

# 이용 가이드 + 로그인 박스 (좌우 분할)
chan1, id_log = st.columns([5, 2])

with chan1:
    st.subheader("이용 가이드")
    st.write("본 서비스는 국내 도심 환경을 고려한 대드론 방어체계(C-UAS) 최적 입지 선정을 위한 데이터와 분석을 제공합니다.")
    st.write("")

    # 단계별 안내 카드 (4열)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        with st.container(border=True):
            st.markdown("### 1.")
            st.markdown("##### **데이터 탐색**")
            st.write('')
            st.write("서울시 전역의 **데이터를 지도에서 확인**하고, 데이터 분포 현황을 파악합니다.")

    with col2:
        with st.container(border=True):
            st.markdown("### 2.")
            st.markdown("##### **후보지 조건 설정**")
            st.write('')
            st.write("분석할 **격자 영역을 생성**하고, 방어무기 **사정거리** 및 시설별 **가중치**를 설정합니다.")

    with col3:
        with st.container(border=True):
            st.markdown("### 3.")
            st.markdown("##### **후보지 계산**")
            st.write('')
            st.write("설정된 시나리오를 바탕으로 **최적의 배치 지점**을 알고리즘이 자동 산출합니다.")

    with col4:
        with st.container(border=True):
            st.markdown("### 4.")
            st.markdown("##### **결과 활용**")
            st.write('')
            st.write("도출된 후보지의 **상세 점수를 확인**하고 여러 시나리오를 상호 비교합니다.")

st.markdown("---")

with id_log:
    with st.container(border=True, height=450):
        st.subheader("로그인")
        st.write('')
        st.caption("D-DAS 서비스 이용을 위해 로그인하세요.")
        st.write('')

        input_sender    = st.text_input('ID', placeholder='아이디를 입력하세요',    key='login_id', label_visibility='collapsed')
        input_recipient = st.text_input('PW', placeholder='비밀번호를 입력하세요', type='password', key='login_pw', label_visibility='collapsed')

        st.write("")
        st.write('')
        sub_butt = st.button('로그인', use_container_width=True, type="primary")
        st.write('')
        st.write('')

        # 회원가입 안내
        c1, c2 = st.columns([5, 3])
        with c1:
            st.caption("계정이 없으신가요?")
        with c2:
            if st.button("회원가입", use_container_width=True):
                signup_dialog()

# 8. 로그인 처리
if sub_butt:
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = "SELECT * FROM users WHERE user_id = %s AND password = %s"
        cursor.execute(sql, (input_sender, input_recipient))

        if cursor.fetchone():
            st.session_state.logged_in = True
            st.switch_page("pages/1_데이터 탐색.py")
