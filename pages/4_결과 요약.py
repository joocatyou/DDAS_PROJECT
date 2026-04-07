import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
import plotly.graph_objects as go
from calculate.calculate import building_cover
from utils import set_common_banner

# ── 페이지 기본 설정 ──────────────────────────────────────────────────────────
st.set_page_config(layout="wide")
set_common_banner()

# ── 카테고리 한글 매핑 및 아이콘/색상 정의 ──────────────────────────────────
CAT_KR = {
    'broadcast': '방송시설', 'electricity': '전력시설', 'factory': '산업 시설',
    'hospital': '병원', 'infra': '지하공동구', 'prison': '교정 시설',
    'public': '국가 공공기관 시설', 'science': '과학연구', 'telecommunication': '정보통신시설',
    'transportation': '교통 항공 항만 시설', 'water': '수원 시설', 'frequency': '기지국',
}
CAT_ICON = {
    'broadcast': ('orange', 'broadcast-tower'), 'electricity': ('green', 'bolt'),
    'factory': ('blue', 'industry'), 'hospital': ('red', 'hospital'),
    'infra': ('darkblue', 'cogs'), 'prison': ('black', 'university'),
    'public': ('cadetblue', 'building'), 'science': ('pink', 'flask'),
    'telecommunication': ('beige', 'satellite-dish'), 'transportation': ('darkgreen', 'train'),
    'water': ('lightblue', 'tint'), 'frequency': ('darkred', 'signal'),
}
# 카테고리별 차트 색상 팔레트
PALETTE = ['#E57535','#72AF26','#38AADD','#D43D2A','#00375D','#3D3D3D','#436978','#E07DBF','#CBBE73','#728224','#A3CAC5','#A23336']


# ── 세션 데이터 로드 ──────────────────────────────────────────────────────────
def load_session_data():
    """세션 상태에서 계산 결과를 불러옵니다. 결과가 없으면 에러 메시지 후 종료합니다."""
    if st.session_state.get('calc_results') is None:
        st.error('3페이지에서 계산을 먼저 실행해주세요.')
        st.stop()

    results = st.session_state['calc_results']
    return (
        results['df_rank'],       # 순위별 후보지 좌표 및 점수
        results['dfs'],           # 전체 건물 데이터프레임
        results['range_km'],      # 커버리지 반경 (km)
        results['weights'],       # 카테고리별 가중치
    )


# ── 커버리지 계산 (캐시 적용) ─────────────────────────────────────────────────
@st.cache_data
def compute_coverage(rank_coords, building_coords, range_km):
    """후보지 좌표 기준으로 반경 내 건물 커버리지를 계산합니다. (결과 캐시)"""
    return building_cover(rank_coords, building_coords, range_km)


# ── 엘보우 인덱스 계산 ────────────────────────────────────────────────────────
def compute_elbow_index(scores):
    """
    점수 구간별 차이가 가장 큰 위치(엘보우 포인트)의 인덱스를 반환합니다.
    순위 그래프에서 적정 후보지 수를 시각적으로 표시하는 데 사용됩니다.
    """
    if len(scores) < 2:
        return 0
    diffs = [scores[i] - scores[i + 1] for i in range(len(scores) - 1)]
    return diffs.index(max(diffs))


# ── Tab 1 관련 함수들 ─────────────────────────────────────────────────────────

def build_coverage_map(candidate, covered_df, range_km):
    """
    선택된 후보지의 커버리지 지도를 생성합니다.
    - 후보지 위치 마커(빨간 원형)
    - 반경 원(파란 원)
    - 카테고리별 건물 마커 클러스터 레이어
    """
    m = folium.Map(
        location=[candidate['lat'], candidate['lng']],
        zoom_start=14,
        tiles=None,
    )

    # 베이스맵 타일 추가
    folium.TileLayer(
        tiles='https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
        attr='© OpenStreetMap contributors',
        show=True,
    ).add_to(m)

    # 커버리지 반경 원 표시
    folium.Circle(
        location=[candidate['lat'], candidate['lng']],
        radius=range_km * 1000,
        color='#3B82F6', weight=2,
        fill=True, fill_color='#3B82F6', fill_opacity=0.08,
    ).add_to(m)

    # 후보지 순위 마커 (빨간 원형 배지)
    folium.Marker(
        location=[candidate['lat'], candidate['lng']],
        icon=folium.DivIcon(
            html=(
                f'<div style="background:#EF4444;color:white;font-weight:bold;'
                f'border-radius:50%;width:32px;height:32px;display:flex;'
                f'align-items:center;justify-content:center;font-size:13px;'
                f'border:2px solid white;">{int(candidate["rank"])}</div>'
            ),
            icon_size=(32, 32),
            icon_anchor=(16, 16),
        ),
    ).add_to(m)

    # 카테고리별 건물 마커 레이어 추가
    for cat in covered_df['tag'].unique():
        cat_df = covered_df[covered_df['tag'] == cat]
        layer = folium.FeatureGroup(name=f"{CAT_KR.get(cat, cat)} ({len(cat_df)}개)", show=True)
        mc = MarkerCluster().add_to(layer)
        color, icon_name = CAT_ICON.get(cat, ('blue', 'info-sign'))

        for _, row in cat_df.iterrows():
            # 건물명 컬럼명이 다를 수 있으므로 순서대로 탐색
            name = row.get('name', row.get('시설명', row.get('건물명', '')))
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(
                    f"<b>{name}</b><br>{CAT_KR.get(cat, cat)}",
                    max_width=250,
                ),
                icon=folium.Icon(color=color, icon=icon_name, prefix='fa'),
            ).add_to(mc)

        layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


def build_category_bar_chart(bar_df):
    """카테고리별 건물 수를 막대 그래프로 생성합니다."""
    fig = go.Figure(go.Bar(
        x=bar_df['카테고리'],
        y=bar_df['건물 수'],
        marker_color=[PALETTE[i % len(PALETTE)] for i in range(len(bar_df))],
        text=bar_df['건물 수'],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>건물 수: %{y}개<extra></extra>',
    ))
    fig.update_layout(
        xaxis_tickangle=-40,
        yaxis_title='건물 수',
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(t=20, b=80, l=50, r=20),
        height=400,
    )
    return fig


def render_tab1(df_rank, df_buildings, cover_result, range_km):
    """
    [Tab 1] 후보지 상세정보 탭을 렌더링합니다.
    - 좌측: 커버리지 지도
    - 우측: 순위 선택 및 요약 메트릭
    - 하단: 카테고리별 건물 수 막대 그래프 + 테이블
    """
    col_map, col_info = st.columns([5, 2])

    with col_info:
        with st.container(border=True):
            # 순위 선택 박스
            selected_rank = st.selectbox(
                "후보지 순위 선택",
                df_rank['rank'].astype(int).tolist(),
                format_func=lambda x: f"{x}순위",
            )
            st.divider()

            # 선택된 후보지 정보 추출
            candidate = df_rank.iloc[selected_rank - 1]
            covered_idx = cover_result.iloc[selected_rank - 1]['building_indices']
            covered_df = df_buildings.iloc[covered_idx].copy()
            cat_counts = covered_df['tag'].value_counts()

            # 요약 메트릭 표시
            st.metric("순위",         f"{selected_rank}위")
            st.metric("커버 건물 수", f"{len(covered_idx)}개")
            st.metric("가중치 점수",  f"{candidate['score']:.4f}")
            st.metric("반경",         f"{range_km} km")

    with col_map:
        with st.container(border=True):
            st.markdown(f"##### {selected_rank}순위 후보지 커버리지")
            st.caption(
                f"위도 {candidate['lat']:.6f} | 경도 {candidate['lng']:.6f} | 반경 {range_km}km"
            )
            # 커버리지 지도 생성 및 렌더링
            m = build_coverage_map(candidate, covered_df, range_km)
            st.components.v1.html(m._repr_html_(), height=500)

    st.divider()

    # 카테고리별 건물 수 데이터프레임 생성
    bar_df = pd.DataFrame([
        {'카테고리': CAT_KR.get(cat, cat), '건물 수': int(cat_counts.get(cat, 0))}
        for cat in covered_df['tag'].unique()
    ]).sort_values('건물 수', ascending=False)

    col_chart, col_table = st.columns([5, 2])

    with col_chart:
        with st.container(border=True):
            st.markdown("##### 카테고리별 건물 수")
            fig = build_category_bar_chart(bar_df)
            st.plotly_chart(fig, use_container_width=True)

    with col_table:
        with st.container(border=True):
            st.markdown("##### 카테고리별 상세")
            st.dataframe(bar_df[['카테고리', '건물 수']], hide_index=True, use_container_width=True, height=400)

    return selected_rank  # Tab 2에서 강조 표시에 사용


# ── Tab 2 관련 함수들 ─────────────────────────────────────────────────────────

def build_coverage_summary_df(df_rank, df_buildings, cover_result):
    """
    후보지별 커버 건물 수 요약 데이터프레임을 생성합니다.
    각 후보지의 전체 커버 수와 카테고리별 세부 수치를 포함합니다.
    """
    summary_rows = []
    for i, (_, cand) in enumerate(df_rank.iterrows()):
        c_idx = cover_result.iloc[i]['building_indices']
        c_counts = df_buildings.iloc[c_idx]['tag'].value_counts()

        row = {
            '순위': int(cand['rank']),
            '위도': round(cand['lat'], 6),
            '경도': round(cand['lng'], 6),
            '커버 건물 수': len(c_idx),
        }
        # 카테고리별 건물 수 추가
        for cat in sorted(df_buildings['tag'].unique()):
            row[CAT_KR.get(cat, cat)] = int(c_counts.get(cat, 0))

        summary_rows.append(row)

    return pd.DataFrame(summary_rows)


def render_tab2(df_rank, df_buildings, cover_result, selected_rank):
    """
    [Tab 2] 후보지 간 비교 탭을 렌더링합니다.
    - 종합점수 및 생활인구/토지이용 압축도 비교 테이블
    - 후보지별 커버 건물 수 비교 테이블 (선택된 순위 강조)
    """
    with st.container(border=True):
        final_df = st.session_state.get('final_df')
        if final_df is None:
            st.info("계산을 먼저 실행해주세요.")
        else:
            # 컬럼명 한글로 변환
            final_df.columns = ['순위', '격자ID', '위도', '경도', '종합 점수 (정규화 후)', '인구 밀도', '건물 밀집도']
            st.markdown('<h5>종합점수 및 생활인구/토지이용 압축도 비교</h5>', unsafe_allow_html=True)
            st.dataframe(final_df, use_container_width=True, hide_index=True)

    st.divider()

    with st.container(border=True):
        st.markdown('<h5>커버 건물 개수 비교</h5>', unsafe_allow_html=True)
        summary_df = build_coverage_summary_df(df_rank, df_buildings, cover_result)

        # 선택된 순위 행을 노란색으로 강조
        st.dataframe(
            summary_df.style.apply(
                lambda row: ['background-color:#FEF9C3'] * len(row)
                if row['순위'] == selected_rank else [''] * len(row),
                axis=1,
            ),
            hide_index=True,
            use_container_width=True,
        )


# ── Tab 3 관련 함수들 ─────────────────────────────────────────────────────────

def build_score_scatter_chart(ranks, scores, elbow_idx):
    """
    후보지 순위별 종합점수 산점도 + 라인 그래프를 생성합니다.
    엘보우 포인트(점수 낙폭이 가장 큰 구간의 시작점)를 주황색으로 강조합니다.
    """
    fig = go.Figure()

    # 라인 레이어 (배경 연결선)
    fig.add_trace(go.Scatter(
        x=ranks, y=scores,
        mode='lines',
        line=dict(color='#94a3b8', width=2),
        showlegend=False,
        hoverinfo='skip',
    ))

    # 포인트 레이어 (순위별 점수 마커)
    fig.add_trace(go.Scatter(
        x=ranks, y=scores,
        mode='markers+text',
        marker=dict(
            color=['#ffab44' if i == elbow_idx else '#8d8d8d' for i in range(len(ranks))],
            size=[16 if i == elbow_idx else 10 for i in range(len(ranks))],
            line=dict(color='white', width=2),
        ),
        text=[f"{s:.4f}" for s in scores],
        textposition='top center',
        hovertemplate='%{x}순위<br>점수: %{y:.5f}<extra></extra>',
        showlegend=False,
    ))

    fig.update_layout(
        xaxis=dict(
            title='후보지 순위',
            tickmode='array',
            tickvals=ranks,
            ticktext=[f"{r}순위" for r in ranks],
        ),
        yaxis=dict(title='점수'),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(t=30, b=40, l=60, r=30),
        height=380,
    )
    return fig


def build_score_diff_df(ranks, scores, elbow_idx):
    """
    순위 간 점수 차이 및 증감률 데이터프레임을 생성합니다.
    엘보우 구간을 굵은 노란색으로 강조합니다.
    """
    diff_rows = [
        {
            '구간': f"{ranks[i]}순위 → {ranks[i+1]}순위",
            '점수 차이': round(scores[i] - scores[i + 1], 5),
            '증감률': f"{(scores[i] - scores[i + 1]) / scores[0] * 100:.1f}%",
        }
        for i in range(len(scores) - 1)
    ]
    df = pd.DataFrame(diff_rows)
    return df.style.apply(
        lambda row: ['background-color:#FEF9C3;font-weight:bold;' if row.name == elbow_idx else '' for _ in row],
        axis=1,
    )


def render_tab3(ranks, scores, elbow_idx, df_rank, range_km):
    """
    [Tab 3] 후보지 간 비교 2 탭을 렌더링합니다.
    - 좌측: 순위별 종합점수 그래프 + 점수 차이 테이블
    - 우측: 분석 조건 요약 및 선택 시설 목록
    """
    col_chart, col_summary = st.columns([6, 3])

    with col_chart:
        with st.container(border=True):
            st.markdown('<h5>후보지 순위별 종합점수 그래프</h5>', unsafe_allow_html=True)

            # 순위별 점수 그래프 렌더링
            fig = build_score_scatter_chart(ranks, scores, elbow_idx)
            st.plotly_chart(fig, use_container_width=True)

            # 점수 차이 테이블 (2개 이상 후보지일 때만 표시)
            if len(scores) >= 2:
                st.dataframe(
                    build_score_diff_df(ranks, scores, elbow_idx),
                    hide_index=True,
                    use_container_width=True,
                )

    with col_summary:
        with st.container(border=True):
            sub1, sub2 = st.columns(2)

            with sub1:
                # 분석 조건 요약 메트릭
                st.markdown("###### 분석 조건 요약")
                st.metric("사정 거리", f"{range_km}km")
                st.metric("후보지 수", f"{len(df_rank)}개")

            with sub2:
                # 사용자가 선택한 시설 목록 (가중치가 0이 아닌 항목만)
                user_input = st.session_state.get('user_input', {})
                selected_names = [
                    n for n, w in user_input.get('selected_weights', {}).items() if w != 0
                ]
                st.markdown(f"###### 선택 시설 ({len(selected_names)}개)")
                for name in selected_names:
                    st.markdown(f"• {name}")


# ── 메인 렌더링 ───────────────────────────────────────────────────────────────

# 세션 데이터 로드
df_rank, df_buildings, range_km, weights = load_session_data()

# 커버리지 계산 (좌표 배열을 캐시 키로 사용)
cover_result = compute_coverage(
    df_rank[['lat', 'lng']].values,
    df_buildings[['latitude', 'longitude']].values,
    range_km,
)

# 순위 및 점수 리스트 추출
ranks  = df_rank['rank'].tolist()
scores = df_rank['score'].tolist()

# 엘보우 포인트 인덱스 계산
elbow_idx = compute_elbow_index(scores)

st.subheader("결과 요약")
tab1, tab2, tab3 = st.tabs(['후보지 상세정보', '후보지 간 비교 1', '후보지 간 비교 2'])

with tab1:
    # Tab 1 렌더링 후 선택된 순위를 받아 Tab 2 강조에 사용
    selected_rank = render_tab1(df_rank, df_buildings, cover_result, range_km)

with tab2:
    render_tab2(df_rank, df_buildings, cover_result, selected_rank)

with tab3:
    render_tab3(ranks, scores, elbow_idx, df_rank, range_km)
