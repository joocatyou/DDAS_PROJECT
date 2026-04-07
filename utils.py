import streamlit as st
import pymysql
import base64

def require_login():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.switch_page("DDAS.py")

def apply_input_style():
    st.markdown("""
    <style>
    div[data-baseweb="input"],
    div[data-baseweb="base-input"] {
        background-color: #f0f2f6 !important;
    }
    div[data-baseweb="input"] input,
    div[data-baseweb="base-input"] input {
        background-color: #f0f2f6 !important;
    }
    div[data-baseweb="textarea"] textarea {
        background-color: #f0f2f6 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# -----------------------------------------------
# 회원가입 함수
# -----------------------------------------------

def get_connection():
    return pymysql.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
        charset="utf8mb4"
    )


def create_table(conn):
    
    with conn.cursor() as cursor:
        sql='''create table if not exists users (
        user_id varchar(500) not null primary key,
        password varchar(1000) not null,
        name varchar(500) not null,
        email varchar(1000) not null
        ) ;'''
        cursor.execute(sql)
        conn.commit()



def register_user(user_id: str, password: str, name: str, email: str,conn) -> bool:
# sql 구문으로 MySQL에 사용자 정보 저장하는 함수    
    with conn.cursor() as cursor:

        sql = "INSERT INTO users (user_id, password, name, email) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (user_id, password, name, email))
        conn.commit()
    return True 


def is_duplicate_id(user_id: str) -> bool:
# sql 구문으로 MySQL에서 사용자 아이디 중복 여부 확인하는 함수  
    return False  # 연동 전까지 항상 중복 없음으로 처리

# -----------------------------------------------
# DDAS.py 회원가입 팝업 함수
# -----------------------------------------------

def show_signup_form():
    # 1. 회원가입 폼 컨테이너 (기존 구조 유지)
    with st.container(border=True):
        st.markdown("#### 회원가입")
        st.write('')

        with st.form("signup_form", clear_on_submit=True):
            user_id  = st.text_input("아이디", placeholder="영문, 숫자 조합 6자 이상")
            name     = st.text_input("이름",   placeholder="이름을 입력하세요")
            email    = st.text_input("이메일", placeholder="example@email.com")
            pw       = st.text_input("비밀번호",    type="password", placeholder="8자 이상")
            pw_check = st.text_input("비밀번호 확인", type="password", placeholder="비밀번호를 다시 입력하세요")

            st.write('')
            submitted = st.form_submit_button("가입하기", use_container_width=True, type="primary")

        # 2. 폼 제출 처리 (기존 로직 유지)
        if submitted:
            if not all([user_id, name, email, pw, pw_check]):
                st.error("모든 항목을 입력해주세요.")
            elif len(user_id) < 6:
                st.error("아이디는 6자 이상이어야 합니다.")
            elif len(pw) < 8:
                st.error("비밀번호는 8자 이상이어야 합니다.")
            elif pw != pw_check:
                st.error("비밀번호가 일치하지 않습니다.")
            elif is_duplicate_id(user_id): # 이 함수는 utils.py 내에 정의되어 있어야 함
                st.error("이미 사용 중인 아이디입니다.")
            else:
                conn=get_connection()
                create_table(conn)
                success = register_user(user_id, pw, name, email, conn) # 이 함수는 utils.py 내에 정의되어 있어야 함
                if success:
                    st.success("회원가입이 완료되었습니다! 창을 닫고 로그인해주세요.")
                    conn.close()

# -----------------------------------------------
# 배너 함수
# -----------------------------------------------

# 1. 로컬 이미지를 Base64로 변환
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return ""

# 2. 모든 페이지에 적용될 공통 레이아웃 함수
def set_common_banner():
    # 이미지 경로 (절대 경로 혹은 프로젝트 상대 경로 확인 필요)
    img_path = r"D:\workspaces\00_Project\crawlProject\project\images\DDAS_logo.png"
    img_base64 = get_base64_image(img_path)

    # 폰트어썸 아이콘 CDN
    st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">', unsafe_allow_html=True)

    # 공통 CSS 및 헤더 (f-string 적용)
    st.markdown(
        f"""
        <style>
        /* 1. 커스텀 배너 설정 (고정된 70px 높이) */
        .custom-header {{
            position: fixed; top: 0; left: 0; width: 100vw; height: 70px;
            background-color: #000000; color: white;
            display: flex; justify-content: space-between; align-items: center;
            padding: 0 40px; 
            z-index: 999999; /* 가장 최상단으로 띄움 */
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }}
        .header-icons {{ display: flex; gap: 30px; }}
        .header-icons a {{ color: white; text-decoration: none; font-size: 20px; transition: 0.3s; }}
        .header-icons a:hover {{ color: #00aaff; transform: scale(1.2); }}
        
        /* 💡 핵심 1: Streamlit 기본 헤더 영역 전체를 배너 밑으로 70px 밀어냄 */
        header[data-testid="stHeader"] {{ 
            top: 70px !important; 
            background: transparent !important; 
        }}

        /* 💡 핵심 2: 사이드바 본문도 배너에 가려지지 않게 70px 밑에서 시작 */
        section[data-testid="stSidebar"] {{ 
            top: 70px !important; 
            height: calc(100vh - 70px) !important; 
            z-index: 99998 !important;
        }}

        /* 💡 핵심 3: 혹시 버튼이 분리되어 있는 버전을 위한 강력한 마진(margin) 푸시 */
        [data-testid="collapsedControl"] {{
            margin-top: 75px !important; 
            margin-left: 10px !important;
            background-color: rgba(255, 255, 255, 0.8) !important; /* 버튼이 잘 보이게 흰 바탕 추가 */
            border-radius: 5px !important;
            z-index: 99999 !important;
        }}
        
        /* 메인 컨텐츠가 배너에 가려지지 않도록 여백 추가 */
        .main .block-container {{ 
            padding-top: 40px !important; 
            margin-top: 70px !important; 
        }}

        /* 사이드바 내부 아이템 스타일링 */
        [data-testid="stSidebarNav"] ul li:nth-child(1) {{
            border-bottom: 2px solid #000000 !important;
            margin-bottom: 15px !important;
            padding-bottom: 5px !important;
        }}
        [data-testid="stSidebarNav"] ul li:nth-child(1) span {{
            color: #000000 !important;
            font-weight: 800 !important;
            font-size: 1.1rem !important;
        }}
        [data-testid="stSidebarNav"] ul li:not(:first-child) {{
            margin-left: 10px !important;
            opacity: 0.8;
        }}
        </style>
        
        <div class="custom-header">
            <div class="header-logo">
                <img src="data:image/png;base64,{img_base64}" alt="DDAS Logo" style="height: 45px; width: auto;">
            </div>
            <div class="header-icons">
                <a href="/" target="_self" title="홈으로 이동"><i class="fa-solid fa-house"></i></a>
                <a href="#" target="_self" title="도움말"><i class="fa-solid fa-circle-question"></i></a>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    # 사이드바 이용 가이드
    with st.sidebar:
        with st.expander("**유의사항**", expanded=False):
            st.write("")
            st.write("")

            st.markdown("각 페이지의 **도움말** 버튼에서  \n해당 페이지의 자세한 사용법을 확인할 수 있습니다.")
            st.divider()
            st.markdown("""
                **시나리오 분석**은  \n후보지 계산 페이지에서  \n시나리오를 **2개 이상** 저장해야  \n이용할 수 있습니다.""")
            st.write("")
