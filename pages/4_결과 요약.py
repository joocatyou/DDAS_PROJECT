import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
import plotly.graph_objects as go
from calculate.calculate import building_cover
from utils import set_common_banner

st.set_page_config(layout="wide")
set_common_banner()

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
PALETTE = ['#E57535','#72AF26','#38AADD','#D43D2A','#00375D','#3D3D3D','#436978','#E07DBF','#CBBE73','#728224','#A3CAC5','#A23336']

if st.session_state.get('calc_results') is None:
    st.error('3페이지에서 계산을 먼저 실행해주세요.')
    st.stop()

results      = st.session_state['calc_results']
df_rank      = results['df_rank']
df_buildings = results['dfs']
range_km     = results['range_km']
weights      = results['weights']

@st.cache_data
def compute_coverage(rank_coords, building_coords, range_km):
    return building_cover(rank_coords, building_coords, range_km)

cover_result = compute_coverage(
    df_rank[['lat', 'lng']].values,
    df_buildings[['latitude', 'longitude']].values,
    range_km,
)

ranks  = df_rank['rank'].tolist()
scores = df_rank['score'].tolist()
elbow_idx = [scores[i] - scores[i+1] for i in range(len(scores)-1)].index(max([scores[i] - scores[i+1] for i in range(len(scores)-1)])) if len(scores) >= 2 else 0

st.subheader("결과 요약")
tab1, tab2, tab3 = st.tabs(['후보지 상세정보', '후보지 간 비교 1', '후보지 간 비교 2'])

# ── Tab 1 ────────────────────────────────────────────────────────────────────
with tab1:
    col_map, col_info = st.columns([5, 2])

    with col_info:
        with st.container(border=True):
            selected_rank = st.selectbox("후보지 순위 선택", df_rank['rank'].astype(int).tolist(), format_func=lambda x: f"{x}순위")
            st.divider()
            candidate   = df_rank.iloc[selected_rank - 1]
            covered_idx = cover_result.iloc[selected_rank - 1]['building_indices']
            covered_df  = df_buildings.iloc[covered_idx].copy()
            cat_counts  = covered_df['tag'].value_counts()
            st.metric("순위",         f"{selected_rank}위")
            st.metric("커버 건물 수", f"{len(covered_idx)}개")
            st.metric("가중치 점수",  f"{candidate['score']:.4f}")
            st.metric("반경",         f"{range_km} km")

    with col_map:
        with st.container(border=True):
            st.markdown(f"##### {selected_rank}순위 후보지 커버리지")
            st.caption(f"위도 {candidate['lat']:.6f} | 경도 {candidate['lng']:.6f} | 반경 {range_km}km")
            m = folium.Map(location=[candidate['lat'], candidate['lng']], zoom_start=14, tiles=None)
            folium.TileLayer(tiles='https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png', attr='© OpenStreetMap contributors', show=True).add_to(m)
            folium.Circle(location=[candidate['lat'], candidate['lng']], radius=range_km*1000, color='#3B82F6', weight=2, fill=True, fill_color='#3B82F6', fill_opacity=0.08).add_to(m)
            folium.Marker(
                location=[candidate['lat'], candidate['lng']],
                icon=folium.DivIcon(html=f'<div style="background:#EF4444;color:white;font-weight:bold;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;font-size:13px;border:2px solid white;">{int(candidate["rank"])}</div>', icon_size=(32,32), icon_anchor=(16,16)),
            ).add_to(m)
            for cat in covered_df['tag'].unique():
                cat_df = covered_df[covered_df['tag'] == cat]
                layer  = folium.FeatureGroup(name=f"{CAT_KR.get(cat, cat)} ({len(cat_df)}개)", show=True)
                mc     = MarkerCluster().add_to(layer)
                color, icon_name = CAT_ICON.get(cat, ('blue', 'info-sign'))
                for _, row in cat_df.iterrows():
                    folium.Marker(
                        location=[row['latitude'], row['longitude']],
                        popup=folium.Popup(f"<b>{row.get('name', row.get('시설명', row.get('건물명', '')))}</b><br>{CAT_KR.get(cat, cat)}", max_width=250),
                        icon=folium.Icon(color=color, icon=icon_name, prefix='fa'),
                    ).add_to(mc)
                layer.add_to(m)
            folium.LayerControl(collapsed=False).add_to(m)
            st.components.v1.html(m._repr_html_(), height=500)

    st.divider()
    col_chart, col_table = st.columns([5, 2])
    bar_df = pd.DataFrame([
        {'카테고리': CAT_KR.get(cat, cat), '건물 수': int(cat_counts.get(cat, 0)),
         '가중치': weights.get(cat, 0), '가중치 점수 (정규화 전)': round(int(cat_counts.get(cat, 0)) * weights.get(cat, 0), 4)}
        for cat in covered_df['tag'].unique()
    ]).sort_values('건물 수', ascending=False)

    with col_chart:
        with st.container(border=True):
            st.markdown("##### 카테고리별 건물 수")
            fig = go.Figure(go.Bar(
                x=bar_df['카테고리'], y=bar_df['건물 수'],
                marker_color=[PALETTE[i % len(PALETTE)] for i in range(len(bar_df))],
                text=bar_df['건물 수'], textposition='outside',
                hovertemplate='<b>%{x}</b><br>건물 수: %{y}개<extra></extra>',
            ))
            fig.update_layout(xaxis_tickangle=-40, yaxis_title='건물 수', plot_bgcolor='white', paper_bgcolor='white', margin=dict(t=20, b=80, l=50, r=20), height=400)
            st.plotly_chart(fig, use_container_width=True)

    with col_table:
        with st.container(border=True):
            st.markdown("##### 카테고리별 상세")
            st.dataframe(bar_df[['카테고리', '건물 수']], hide_index=True, use_container_width=True, height=400)


# ── Tab 2 ────────────────────────────────────────────────────────────────────
with tab2:
    with st.container(border=True):
        final_df = st.session_state.get('final_df')
        if final_df is None:
            st.info("계산을 먼저 실행해주세요.")
        else:
            final_df.columns = ['순위', '격자ID', '위도', '경도', '종합 점수 (정규화 후)', '인구 밀도', '건물 밀집도']
            st.markdown('<h5>종합점수 및 생활인구/토지이용 압축도 비교</h5>', unsafe_allow_html=True)
            st.dataframe(final_df, use_container_width=True, hide_index=True)

    st.divider()

    with st.container(border=True):
        st.markdown('<h5>커버 건물 개수 비교</h5>', unsafe_allow_html=True)
        summary_rows = []
        for i, (_, cand) in enumerate(df_rank.iterrows()):
            c_idx    = cover_result.iloc[i]['building_indices']
            c_counts = df_buildings.iloc[c_idx]['tag'].value_counts()
            row      = {'순위': int(cand['rank']), '위도': round(cand['lat'], 6), '경도': round(cand['lng'], 6), '커버 건물 수': len(c_idx)}
            for cat in sorted(df_buildings['tag'].unique()):
                row[CAT_KR.get(cat, cat)] = int(c_counts.get(cat, 0))
            summary_rows.append(row)
        summary_df = pd.DataFrame(summary_rows)
        st.dataframe(
            summary_df.style.apply(lambda row: ['background-color:#FEF9C3']*len(row) if row['순위'] == selected_rank else ['']*len(row), axis=1),
            hide_index=True, use_container_width=True,
        )


# ── Tab 3 ────────────────────────────────────────────────────────────────────
with tab3:
    col_chart, col_summary = st.columns([6, 3])

    with col_chart:
        with st.container(border=True):
            st.markdown('<h5>후보지 순위별 종합점수 그래프</h5>', unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ranks, y=scores, mode='lines', line=dict(color='#94a3b8', width=2), showlegend=False, hoverinfo='skip'))
            fig.add_trace(go.Scatter(
                x=ranks, y=scores, mode='markers+text',
                marker=dict(color=['#ffab44' if i==elbow_idx else '#8d8d8d' for i in range(len(ranks))], size=[16 if i==elbow_idx else 10 for i in range(len(ranks))], line=dict(color='white', width=2)),
                text=[f"{s:.4f}" for s in scores], textposition='top center',
                hovertemplate='%{x}순위<br>점수: %{y:.5f}<extra></extra>', showlegend=False,
            ))
            fig.update_layout(
                xaxis=dict(title='후보지 순위', tickmode='array', tickvals=ranks, ticktext=[f"{r}순위" for r in ranks]),
                yaxis=dict(title='점수'), plot_bgcolor='white', paper_bgcolor='white',
                margin=dict(t=30, b=40, l=60, r=30), height=380,
            )
            st.plotly_chart(fig, use_container_width=True)

            if len(scores) >= 2:
                st.dataframe(
                    pd.DataFrame([
                        {'구간': f"{ranks[i]}순위 → {ranks[i+1]}순위", '점수 차이': round(scores[i]-scores[i+1], 5), '증감률': f"{(scores[i]-scores[i+1])/scores[0]*100:.1f}%"}
                        for i in range(len(scores)-1)
                    ]).style.apply(lambda row: ['background-color:#FEF9C3;font-weight:bold;' if row.name==elbow_idx else '' for _ in row], axis=1),
                    hide_index=True, use_container_width=True,
                )

    with col_summary:
        with st.container(border=True):
            sub1, sub2 = st.columns(2)
            with sub1:
                st.markdown("###### 분석 조건 요약")
                st.metric("사정 거리", f"{range_km}km")
                st.metric("후보지 수", f"{len(df_rank)}개")
            with sub2:
                user_input = st.session_state.get('user_input', {})
                selected_names = [n for n, w in user_input.get('selected_weights', {}).items() if w != 0]
                st.markdown(f"###### 선택 시설 ({len(selected_names)}개)")
                for name in selected_names:
                    st.markdown(f"• {name}")
