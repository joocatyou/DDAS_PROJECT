import streamlit as st
import os
from utils import set_common_banner

set_common_banner()

# 1. 상수 정의

# 시설 선택 옵션 목록
FACILITY_OPTIONS = [
    '전력시설', '정보통신시설', '국가 공공기관 시설', '교통 항공 항만 시설',
    '수원 시설', '지하공동구', '산업 시설', '기지국', '병원', '과학연구',
    '교정 시설', '방송시설'
]

# 시설별 기본 가중치 (AHP 분석 결과 기반)
DEFAULT_WEIGHTS = {
    '전력시설':           '0.242',
    '정보통신시설':        '0.153',
    '국가 공공기관 시설':  '0.116',
    '교통 항공 항만 시설': '0.081',
    '수원 시설':           '0.055',
    '지하공동구':          '0.079',
    '인구밀도 ':           '0.0',
    '토지 이용 압축도':    '0.0',
    '산업 시설':           '0.057',
    '기지국':              '0.025',
    '병원':                '0.030',
    '과학연구':            '0.013',
    '교정 시설':           '0.011',
    '방송시설':            '0.100',
}

# 2. 도움말 다이얼로그

@st.dialog(" ", width="medium")
def render_help():
    """
    후보지 조건 설정 페이지의 도움말 다이얼로그를 렌더링한다.

    주요 설정 항목(영역 지정, 방어 조건 설정)과
    따라하기 가이드(3단계: 영역 지정 → 격자 생성 → 가중치 선택)를 안내한다.
    """
    st.subheader('도움말')
    st.write("서울시 내 집중 방어 구역을 선택하고, 장비 스펙과 시설별 중요도를 설정하는 단계입니다.")
    st.write("")

    help_tab1, help_tab2 = st.tabs(["주요 설정 항목", "따라하기 가이드"])

    with help_tab1:
        col1, col2 = st.columns([3, 3])
        with col1:
            st.markdown("##### 시설물 지점 분석 (Point)")
            with st.container(border=True, width=400):
                st.markdown("""
                - 지도 위 클릭으로 분석 영역 설정
                - 격자 크기(100m 등) 조정
                - 수계 감지로 불필요한 영역 제외
                """)
        with col2:
            st.markdown("##### 방어 조건 설정")
            with st.container(border=True, width=400):
                st.markdown("""
                - 사거리(km) 및 후보지 개수 설정
                - 보호 대상 시설 선택
                - 시설별 가중치 부여
                """)

    with help_tab2:
        st.markdown("##### **[따라하기: 분석 설계 3단계]**")
        st.write("")

        # STEP 1: 영역 지정
        c1_img, c1_txt = st.columns([0.7, 0.3])
        with c1_img:
            st.image('images/guide1.png', use_container_width=True)
        with c1_txt:
            st.markdown("#### **1. 영역 지정**")
            st.markdown("- 지도 위를 **자유롭게 클릭**하여 방어하고 싶은 지역을 닫힌 다각형 형태로 그리세요.")

        st.divider()

        # STEP 2: 격자 생성
        c2_img, c2_txt = st.columns([0.7, 0.3])
        with c2_img:
            st.image('images/guide2.png', use_container_width=True)
        with c2_txt:
            st.markdown("#### **2. 격자 생성**")
            st.markdown("""
            - 좌측 생성기에서 **:blue[[셀 간격]]** 설정
            - **:orange[[구역 생성]]** 버튼 클릭
            - 파일명 선택 후 **:green[[저장]]** 버튼 클릭
            """)

        st.divider()

        # STEP 3: 가중치 선택
        c3_img, c3_txt = st.columns([0.7, 0.3])
        with c3_img:
            st.image('images/guide3.png', use_container_width=True)
        with c3_txt:
            st.markdown("#### **3. 가중치 선택**")
            st.markdown("""
            - **:orange[장비 사거리]** 및 **:green[후보지 수]** 입력
            - 보호가 필요한 시설 체크
            - 시설 체크 시 자동으로 뜨는 **:blue[가중치 값]** 입력 (default 값 제공)
            - 최하단 **:red[[Select]]** 버튼 클릭
            """)

    st.write('')
    st.warning("**주의**: 반드시 [따라하기 가이드] 순서대로 진행해야 정상적으로 계산이 실행됩니다.")

# 3. 메인 UI

def main():
    """
    후보지 조건 설정 페이지 진입점.

    격자 생성 지도와 사정거리·후보지 수·가중치 설정 UI를 렌더링한다.
    [Select] 버튼 클릭 시 입력값을 세션(user_input)에 저장하고
    3단계 계산 페이지로 이동한다.
    """
    # 페이지 헤더 + 도움말 버튼
    header_col, help_col = st.columns([10, 1])
    with header_col:
        st.subheader('후보지 조건 설정')
    with help_col:
        st.write("")  # 수직 정렬용 여백
        if st.button("도움말"):
            render_help()

    with st.container():
        col1, col2 = st.columns([7, 2])

        with col1:
            with st.container(border=True):
                map_file = os.path.join(os.path.dirname(__file__), '../make_grid.html')
                if os.path.exists(map_file):
                    with open(map_file, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    st.components.v1.html(html_content, height=700)

        with col2:
            # 사정거리 & 후보지 수 입력
            with st.container(border=True):
                sub_col1, sub_col2 = st.columns(2)
                with sub_col1:
                    st.number_input(
                        '사정 거리 (km)',
                        min_value=0.0, max_value=100.0, value=1.5,
                        step=0.2, format='%.1f', key='range_km'
                    )
                with sub_col2:
                    st.text_input(
                        '후보지 수',
                        value='3', key='radar_num',
                        placeholder='후보지 수를 입력하세요'
                    )

            # 시설 선택 & 가중치 입력
            with st.container(border=True):
                st.write('후보지 고려 사항을 선택하세요 ')
                with st.container(border=True):
                    for opt in FACILITY_OPTIONS:
                        c1, c2 = st.columns([2, 1])
                        with c1:
                            checked = st.checkbox(opt, key=f'check_{opt}', value=True)
                        with c2:
                            if checked:
                                st.text_input(
                                    '가중치', value=DEFAULT_WEIGHTS[opt],
                                    key=f'weight_{opt}',
                                    label_visibility='collapsed',
                                    placeholder='가중치'
                                )
                st.write('')

            warn_placeholder = st.empty()

            # Select 버튼: 입력값 검증 후 세션에 저장하고 다음 페이지로 이동
            if st.button("Select", key=f"button_{opt}", use_container_width=True, type='primary'):
                any_checked = any(st.session_state.get(f'check_{opt}', False) for opt in FACILITY_OPTIONS)

                if not any_checked:
                    warn_placeholder.warning('고려 사항을 선택하세요')
                else:
                    # 선택된 시설의 가중치를 수집 (미선택은 0으로 처리)
                    selected_weights = {}
                    for opt in FACILITY_OPTIONS:
                        if st.session_state.get(f'check_{opt}', False):
                            try:
                                w = float(st.session_state.get(f'weight_{opt}', '0'))
                            except (ValueError, TypeError):
                                w = 0.0
                        else:
                            w = 0.0
                        selected_weights[opt] = w

                    range_km  = float(st.session_state.get('range_km', 1.5))
                    radar_num = st.session_state.get('radar_num', '3')

                    # 세션에 사용자 입력 저장 후 계산 페이지로 이동
                    st.session_state['user_input'] = {
                        'range_km':         range_km,
                        'radar_num':        radar_num,
                        'selected_weights': selected_weights,
                    }
                    st.session_state.pop('calc_results', None)

                    st.switch_page("pages/3_후보지 계산.py")


main()
