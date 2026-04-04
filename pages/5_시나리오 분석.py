import streamlit as st
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree
import plotly.graph_objects as go
from utils import set_common_banner

# 1. 페이지 설정
st.set_page_config(layout="wide")
set_common_banner()

@st.dialog(" ", width="medium")
def render_help():
    """
    시나리오 분석 페이지의 도움말 다이얼로그를 렌더링한다.

    3단계에서 저장한 시나리오를 불러와
    상호 비교하는 방법을 안내한다.
    """
    st.subheader('도움말')
    st.write("이 페이지는 **3단계에서 저장한 시나리오**를 불러와 상호 비교 할 수 있도록 지원합니다.")
    st.write("")
    st.info('예: 같은 지역에서 사정거리가 다른 무기 운용 시 등')

# 페이지 헤더 + 도움말 버튼
header_col, help_col = st.columns([10, 1])
with header_col:
    st.subheader("시나리오 비교")
with help_col:
    st.write("")  # 수직 정렬용 여백
    if st.button("도움말"):
        render_help()

# 2. 분석 함수

def building_cover(coords_grid, coords_building, RANGE_KM):
    """
    BallTree를 이용해 각 격자 좌표의 반경 내 건물 인덱스를 반환한다.

    Parameters
    ----------
    coords_grid     : numpy.ndarray (n, 2) — 격자 중심 좌표 (위도, 경도, degree)
    coords_building : numpy.ndarray (m, 2) — 건물 좌표 (위도, 경도, degree)
    RANGE_KM        : float                — 탐색 반경 (km)

    Returns
    -------
    DataFrame
        - grid_id          : 격자 인덱스
        - building_count   : 반경 내 건물 수
        - building_indices : 반경 내 건물 인덱스 배열
    """
    grid_rad     = np.deg2rad(coords_grid)
    building_rad = np.deg2rad(coords_building)
    tree         = BallTree(building_rad, metric='haversine')
    indices      = tree.query_radius(grid_rad, r=RANGE_KM / 6371)
    return pd.DataFrame({
        'grid_id':          range(len(coords_grid)),
        'building_count':   [len(idx) for idx in indices],
        'building_indices': indices,
    })


def get_cumulative_coverage(dfs, df_rank, range_km):
    """
    후보지를 순서대로 추가했을 때의 누적 커버율(%)을 반환한다.

    Parameters
    ----------
    dfs      : dict of DataFrame — 카테고리별 시설 데이터 딕셔너리
    df_rank  : pandas.DataFrame  — 후보지 순위 DataFrame (lat, lng 컬럼 포함)
    range_km : float             — 탐색 반경 (km)

    Returns
    -------
    cumulative : list of float
        후보지를 하나씩 추가할 때마다의 누적 커버율(%) 목록
    """
    df_all = dfs
    cover_result = building_cover(
        df_rank[['lat', 'lng']].values,
        df_all[['latitude', 'longitude']].values,
        range_km,
    )

    total       = len(df_all)
    covered_set = set()
    cumulative  = []
    for indices in cover_result['building_indices']:
        covered_set.update(indices)
        cumulative.append(round(len(covered_set) / total * 100, 1))
    return cumulative

# 3. UI 렌더링 함수

def show_conditions(s):
    """
    시나리오의 입력 조건을 화면에 표시한다.

    Parameters
    ----------
    s : dict
        시나리오 딕셔너리. range_km, radar_num, weights 키를 포함해야 한다.
    """
    weights = s['weights']
    top3    = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:3]

    st.metric("사정 거리", f"{s['range_km']} km")
    st.metric("후보지 수", f"{s['radar_num']} 개")
    st.caption("Top 3 카테고리")
    for cat, w in top3:
        st.markdown(f"- **{cat}** `{w:.5f}`")


def show_score_comparison(s1, s2):
    """
    두 시나리오의 후보지 순위별 점수를 한 차트에 겹쳐서 표시한다.

    Parameters
    ----------
    s1 : dict — 시나리오 A 딕셔너리 (name, df_rank 키 포함)
    s2 : dict — 시나리오 B 딕셔너리 (name, df_rank 키 포함)
    """
    st.markdown("##### 후보지 순위별 점수 비교")

    fig = go.Figure()
    for s, dash in [(s1, 'solid'), (s2, 'dot')]:
        ranks  = s['df_rank']['rank'].tolist()
        scores = s['df_rank']['score'].tolist()
        fig.add_trace(go.Scatter(
            x=ranks, y=scores,
            mode='lines+markers+text',
            name=s['name'],
            line=dict(width=2, dash=dash),
            marker=dict(size=8),
            text=[f"{v:.4f}" for v in scores],
            textposition='top center',
            textfont=dict(size=10),
            hovertemplate=f"{s['name']}<br>%{{x}}순위: %{{y:.5f}}<extra></extra>",
        ))

    # x축 눈금은 두 시나리오의 순위를 합친 범위로 설정
    all_ranks = sorted(set(
        s1['df_rank']['rank'].tolist() + s2['df_rank']['rank'].tolist()
    ))
    fig.update_layout(
        xaxis=dict(title='후보지 순위', tickmode='array', tickvals=all_ranks, ticktext=[f"{r}순위" for r in all_ranks]),
        yaxis=dict(title='점수'),
        plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(t=10, b=40, l=60, r=30),
        height=360,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0),
    )
    st.plotly_chart(fig, use_container_width=True)


def show_coverage_comparison(s1, s2):
    """
    두 시나리오의 누적 커버율을 한 차트에 표시한다.

    Parameters
    ----------
    s1 : dict — 시나리오 A 딕셔너리 (name, df_rank, dfs, range_km 키 포함)
    s2 : dict — 시나리오 B 딕셔너리 (name, df_rank, dfs, range_km 키 포함)
    """
    st.markdown("##### 누적 커버율 비교")

    fig = go.Figure()
    for s, dash in [(s1, 'solid'), (s2, 'dot')]:
        ranks      = s['df_rank']['rank'].tolist()
        cumulative = get_cumulative_coverage(s['dfs'], s['df_rank'], s['range_km'])
        fig.add_trace(go.Scatter(
            x=ranks, y=cumulative,
            mode='lines+markers+text',
            name=s['name'],
            line=dict(width=2, dash=dash),
            marker=dict(size=8),
            text=[f"{v}%" for v in cumulative],
            textposition='top center',
            textfont=dict(size=10),
            hovertemplate=f"{s['name']}<br>%{{x}}순위까지: %{{y}}%<extra></extra>",
        ))

    all_ranks = sorted(set(
        s1['df_rank']['rank'].tolist() + s2['df_rank']['rank'].tolist()
    ))
    fig.update_layout(
        xaxis=dict(title='후보지 수', tickmode='array', tickvals=all_ranks, ticktext=[f"{r}순위" for r in all_ranks]),
        yaxis=dict(title='누적 커버율 (%)', range=[0, 105]),
        plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(t=10, b=40, l=60, r=30),
        height=360,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0),
    )
    st.plotly_chart(fig, use_container_width=True)


def show_rank_table_comparison(s1, s2):
    """
    두 시나리오의 후보지 상세 정보(순위, 점수, 좌표)를 나란히 표시한다.

    Parameters
    ----------
    s1 : dict — 시나리오 A 딕셔너리 (name, df_rank 키 포함)
    s2 : dict — 시나리오 B 딕셔너리 (name, df_rank 키 포함)
    """
    st.markdown("##### 후보지 상세 비교")
    col1, col2 = st.columns(2)

    for col, s in [(col1, s1), (col2, s2)]:
        with col:
            st.markdown(f"**{s['name']}**")
            df = s['df_rank'][['rank', 'score', 'lat', 'lng']].copy()
            df.columns = ['순위', '종합점수 (정규화 후)', '위도', '경도']
            st.dataframe(df, hide_index=True, use_container_width=True)

# 4. 메인 로직

def main():
    """
    시나리오 분석 페이지 진입점.

    세션에 저장된 시나리오 목록을 불러와 2개를 선택하고
    입력 조건·점수·누적 커버율·후보지 상세 정보를 탭별로 비교한다.
    """
    scenarios = st.session_state.get('scenarios', [])

    # 저장된 시나리오가 2개 미만이면 안내 메시지 출력
    if len(scenarios) < 2:
        st.info(f"시나리오가 {len(scenarios)}개 저장되어 있습니다. "
                "계산 페이지에서 최소 2개를 저장해주세요.")
        if scenarios:
            st.caption(f"저장된 시나리오: {', '.join(s['name'] for s in scenarios)}")
        return

    names = [s['name'] for s in scenarios]

    # 비교할 시나리오 2개 선택
    col1, col2 = st.columns(2)
    with col1:
        name_a = st.selectbox("시나리오 A", names, index=0, key="scenario_a")
    with col2:
        name_b = st.selectbox("시나리오 B", names, index=min(1, len(names) - 1), key="scenario_b")

    if name_a == name_b:
        st.warning("서로 다른 시나리오를 선택해주세요.")
        return

    s1 = next(s for s in scenarios if s['name'] == name_a)
    s2 = next(s for s in scenarios if s['name'] == name_b)

    tab1, tab2, tab3, tab4 = st.tabs(['입력 조건 비교', '점수 비교', '누적 커버율', '상세 비교'])

    with tab1:
        st.markdown("##### 입력 조건 비교")
        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.markdown(f"**{s1['name']}**")
                show_conditions(s1)
        with col2:
            with st.container(border=True):
                st.markdown(f"**{s2['name']}**")
                show_conditions(s2)

    with tab2:
        show_score_comparison(s1, s2)

    with tab3:
        show_coverage_comparison(s1, s2)

    with tab4:
        show_rank_table_comparison(s1, s2)

        # 저장된 시나리오 목록 및 삭제
        with st.expander("저장된 시나리오 관리"):
            for s in scenarios:
                c1, c2 = st.columns([4, 1])
                c1.write(s['name'])
                if c2.button("삭제", key=f"del_{s['name']}"):
                    st.session_state['scenarios'] = [
                        x for x in scenarios if x['name'] != s['name']
                    ]
                    st.rerun()


main()
