import streamlit as st
import pandas as pd
import folium
import os
from get.get import *
from calculate.calculate import *
from visualize.visualize import *
from db.db import upload_result
from utils import set_common_banner

# 1. 페이지 설정
st.set_page_config(layout="wide")
set_common_banner()

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

# 2. 상수 정의 (시설 카테고리별 지도 아이콘)
ICON_MAP = {
    "broadcast":         folium.Icon(color="orange",    icon="broadcast-tower",  prefix="fa"),
    "electricity":       folium.Icon(color="green",     icon="bolt",             prefix="fa"),
    "factory":           folium.Icon(color="blue",      icon="industry",         prefix="fa"),
    "hospital":          folium.Icon(color="red",       icon="hospital",         prefix="fa"),
    "infra":             folium.Icon(color="darkblue",  icon="cogs",             prefix="fa"),
    "prison":            folium.Icon(color="black",     icon="university",       prefix="fa"),
    "public":            folium.Icon(color="cadetblue", icon="building",         prefix="fa"),
    "science":           folium.Icon(color="pink",      icon="flask",            prefix="fa"),
    "telecommunication": folium.Icon(color="beige",     icon="satellite-dish",   prefix="fa"),
    "transportation":    folium.Icon(color="darkgreen", icon="train",            prefix="fa"),
    "water":             folium.Icon(color="lightblue", icon="tint",             prefix="fa"),
    "frequency":         folium.Icon(color="darkred",   icon="signal",           prefix="fa"),
}

# 3. 다이얼로그 함수

@st.dialog(" ", width="medium")
def render_help():
    """페이지 기능 안내 다이얼로그"""
    st.subheader('도움말')
    st.write("이 페이지는 **2단계에서 설정한 조건에 따라 최적의 후보지를 자동으로 계산**하고 결과를 시각화합니다.")
    st.write("")

    col1, col2 = st.columns([3, 3])
    with col1:
        with st.container(border=True, height=150):
            st.markdown("<h4 style='text-align: center;'> 지도 시각화</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; font-size: 14px;'>계산된 후보지를 지도 위에 표시하고, 각 후보지의 사정거리 내 시설물 분포를 확인합니다.</p>", unsafe_allow_html=True)
        with st.container(border=True, height=150):
            st.markdown("<h4 style='text-align: center;'> 시나리오 저장</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; font-size: 14px;'>현재 분석 결과를 시나리오로 저장하여 다른 분석 결과와 비교할 수 있습니다.</p>", unsafe_allow_html=True)
    with col2:
        with st.container(border=True, height=150):
            st.markdown("<h4 style='text-align: center;'> 분석 조건 요약</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; font-size: 14px;'>사정거리, 후보지 수, 선택된 시설 등 현재 분석 조건을 한 눈에 확인합니다.</p>", unsafe_allow_html=True)
        with st.container(border=True, height=150):
            st.markdown("<h4 style='text-align: center;'> 모든 조건 초기화</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; font-size: 14px;'>분석 조건을 초기화하고 처음부터 새로운 분석을 시작할 수 있습니다.</p>", unsafe_allow_html=True)


@st.dialog("시설 변경")
def facility_dialog():
    """선택된 시설과 가중치를 변경하고 재계산하는 다이얼로그"""
    options = [
        '전력시설', '정보통신시설', '국가 공공기관 시설', '교통 항공 항만 시설',
        '수원 시설', '지하공동구', '산업 시설', '기지국', '병원', '과학연구',
        '교정 시설', '방송시설'
    ]
    current_weights = st.session_state['user_input']['selected_weights']

    st.write('후보지 고려 사항을 선택하세요')
    with st.container(border=True):
        for opt in options:
            c1, c2 = st.columns([2, 1])
            with c1:
                checked = st.checkbox(opt, key=f'dialog_check_{opt}', value=current_weights.get(opt, 0) != 0)
            with c2:
                if checked:
                    st.text_input('가중치', value=str(current_weights.get(opt, 0)),
                                  key=f'dialog_weight_{opt}', label_visibility='collapsed', placeholder='가중치')

    st.write('')
    if st.button("재계산", type="primary", use_container_width=True):
        selected_weights = {}
        for opt in options:
            if st.session_state.get(f'dialog_check_{opt}', False):
                try:
                    w = float(st.session_state.get(f'dialog_weight_{opt}', '0'))
                except (ValueError, TypeError):
                    w = 0.0
            else:
                w = 0.0
            selected_weights[opt] = w
        st.session_state['user_input']['selected_weights'] = selected_weights
        st.session_state.pop('calc_results', None)
        st.rerun()


@st.dialog("가중치 변경", width="small")
def weight_dialog():
    """가중치만 빠르게 수정하고 재계산하는 다이얼로그"""
    st.caption("각 시설의 가중치를 조정하고 재계산하세요.")

    current_weights = st.session_state['user_input']['selected_weights']
    new_weights = {}

    cols = st.columns(2)
    for i, (name, val) in enumerate(current_weights.items()):
        with cols[i % 2]:
            st.caption(name)
            new_weights[name] = st.text_input(name, value=str(val),
                                              key=f'weight_{name}', label_visibility='collapsed', placeholder='가중치')

    if st.button("재계산", type="primary", use_container_width=True):
        st.session_state['user_input']['selected_weights'] = {k: float(v) for k, v in new_weights.items()}
        st.session_state.pop('calc_results', None)
        st.rerun()


# 4. 메인 로직

def main():
    """
    후보지 계산 페이지 진입점.

    2단계에서 설정한 조건(user_input)을 세션에서 읽어
    점수 계산 → 순위 산출 → 지도 생성 순으로 실행한다.
    계산 결과는 세션(calc_results)에 저장되어 이후 페이지에서 재사용된다.
    """
    df_grid, grid_bd_points = get_latest_grid_data()
    dfs1 = get_dfs1()
    dfs2 = get_dfs2(df_grid)

    # 이전 단계 입력값 없으면 중단
    if 'user_input' not in st.session_state:
        st.error('사용자 입력 페이지에서 조건을 먼저 입력해주세요.')
        st.page_link("pages/2_후보지 조건 설정.py", label="조건 설정 페이지로 이동")
        st.stop()

    if 'calc_results' not in st.session_state:
        user_input = st.session_state['user_input']
        weight     = user_input['selected_weights']

        # 한글 시설명 → 영문 카테고리키 매핑
        weight_dic = {
            'broadcast':         weight['방송시설'],
            'electricity':       weight['전력시설'],
            'factory':           weight['산업 시설'],
            'hospital':          weight['병원'],
            'infra':             weight['지하공동구'],
            'prison':            weight['교정 시설'],
            'public':            weight['국가 공공기관 시설'],
            'science':           weight['과학연구'],
            'telecommunication': weight['정보통신시설'],
            'transportation':    weight['교통 항공 항만 시설'],
            'water':             weight['수원 시설'],
            'frequency':         weight['기지국'],
        }
        RANGE_KM  = float(user_input['range_km'])
        radar_num = int(user_input['radar_num'])

        with st.status('후보지 계산 중...', expanded=False) as calc_status:
            # 1. 시설별 점수 계산
            set_score(dfs1, weight_dic)

            # 2. 최적 후보지 순위 계산
            st.write('최적 후보지 계산 중... ')
            rank_dic, _,df_filtered_building = calc_rank(
                dfs1, df_grid, RANGE_KM, radar_num, polygon_coords=grid_bd_points
            )

            # 3. 인구/밀도 데이터와 결합하여 최종 결과 생성
            df_population   = dfs2['population']
            df_area_density = dfs2['area_density']
            df_final = get_df_final(rank_dic, df_grid, df_population, df_area_density, RANGE_KM)
            st.session_state.final_df = df_final

            # 4. 결과 지도 생성
            st.write('지도 생성 중...')
            visualize(df_grid, dfs1, rank_dic, RANGE_KM, ICON_MAP,
                      show_rank=None, polygon_coords=grid_bd_points, df_final=df_final)

            # 5. 순위 데이터프레임 생성
            df_rank = pd.DataFrame([
                {
                    'rank':  i + 1,
                    'score': score,
                    'lat':   df_grid.loc[idx, 'center_lat'],
                    'lng':   df_grid.loc[idx, 'center_lng'],
                }
                for i, (idx, score) in enumerate(rank_dic.items())
            ])

            # 가중치 > 0인 시설 이름 목록 추출
            name_list = st.session_state['user_input']['selected_weights']
            select_name_list = [name for name, weight in name_list.items() if weight != 0]

            # 계산 결과를 세션에 저장
            st.session_state['calc_results'] = {
                'df_rank':             df_rank,
                'dfs':                 df_filtered_building,
                'range_km':            RANGE_KM,
                'radar_num':           radar_num,
                'weights':             weight_dic,
                'selected_facilities': select_name_list,
            }

            calc_status.update(label=f'{len(rank_dic)}개 후보지 선정', state='complete', expanded=False)

            

    results  = st.session_state['calc_results']
    df_rank  = results['df_rank']
    range_km = st.session_state['user_input']['range_km']

    # 페이지 헤더 + 도움말 버튼
    header_col, help_col = st.columns([10, 1])
    with header_col:
        st.subheader("후보지 탐색 결과")
    with help_col:
        st.write("")  # 수직 정렬용 여백
        if st.button("도움말"):
            render_help()

    col1, col2 = st.columns([6, 3])

    with col1:
        with st.container(border=True):
            map_file = os.path.join(os.path.dirname(__file__), '../map.html')
            if os.path.exists(map_file):
                with open(map_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                st.components.v1.html(html_content, height=650)

    with col2:
        # 분석 조건 요약
        with st.container(border=True):
            sub_col1, sub_col2 = st.columns([2, 4.1])

            with sub_col1:
                st.markdown("###### 분석 조건 요약")
                st.metric("사정 거리", f"{range_km}km")
                st.metric("후보지 수", f"{len(results['df_rank'])}개")

            with sub_col2:
                name_list = st.session_state['user_input']['selected_weights']
                select_name_list = [name for name, weight in name_list.items() if weight != 0]

                st.markdown(f"###### 선택 시설 ({len(select_name_list)}개)")
                if select_name_list:
                    f_c1, f_c2 = st.columns(2)
                    for i, name in enumerate(select_name_list):
                        target_col = f_c1 if i % 2 == 0 else f_c2
                        target_col.markdown(f"• {name}")
                else:
                    st.caption("선택된 시설 없음")

        # 시나리오 저장
        with st.container(border=True):
            st.markdown("###### 시나리오 저장")
            st.caption('현재 분석 조건을 보관하여 나중에 비교하세요.')

            scenario_name = st.text_input(
                '시나리오 이름',
                placeholder='예) 사정거리 2km 설정안',
                key='scenario_input'
            )

            if st.button('시나리오 저장하기', use_container_width=True, type="primary"):
                if not scenario_name.strip():
                    st.warning('시나리오 이름을 입력하세요.')
                else:
                    # 같은 이름의 기존 시나리오를 덮어쓰기 후 저장
                    scenario  = {'name': scenario_name.strip(), **results}
                    scenarios = st.session_state.get('scenarios', [])
                    scenarios = [s for s in scenarios if s['name'] != scenario_name.strip()]
                    scenarios.append(scenario)
                    st.session_state['scenarios'] = scenarios
                    st.success(f"'{scenario_name.strip()}' 저장 완료!")

            col1, col2 = st.columns([1, 1])
            with col2:
                if st.button('시설 변경', use_container_width=True):
                    facility_dialog()

        # 초기화
        with st.container(border=True):
            st.markdown("###### 초기화")
            st.caption('분석 조건을 초기화하고 처음부터 설정하세요.')
            if st.button('모든 조건 초기화', use_container_width=True, type="secondary"):
                st.session_state.pop('user_input', None)
                st.session_state.pop('calc_results', None)
                st.session_state.pop('final_df', None)
                st.success('모든 조건이 초기화되었습니다. 2단계 페이지로 돌아가 다시 설정해주세요.')
                st.switch_page('pages/2_후보지 조건 설정.py')


main()
