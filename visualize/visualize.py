import folium
from folium.plugins import MarkerCluster
from shapely.geometry import Point, Polygon
import random

# ────────────────────────────────────────────────────────────────────────────────
# 시각화
# ────────────────────────────────────────────────────────────────────────────────
def visualize(df_grid, dfs, rank_dic, RANGE_KM, ICON_MAP,
              show_rank=None, polygon_coords=None,
              df_final=None):
    """
    레이더 설치 결과를 지도에 시각화하는 함수

    Parameters
    ----------
    df_grid         : 격자 정보 DataFrame
    dfs             : 건물 DataFrame 딕셔너리 {tag: DataFrame}
    rank_dic        : {격자 인덱스: 점수} — calc_rank 반환값
    RANGE_KM        : 레이더 커버 반경 (km)
    ICON_MAP        : 건물 태그별 folium 아이콘 딕셔너리
    show_rank       : 표시할 레이더 순위 수 (None이면 전체)
    polygon_coords  : 구역 다각형 꼭짓점 [(lat, lng), ...] (None이면 bounding box)
    df_final        : 레이더별 커버 밀집도 DataFrame (없으면 팝업에 0 표시)
    """

    # ── 지도 중심 좌표 계산 및 초기화 ──────────────────────────────
    mid_lat = (df_grid["ne_lat"].max() + df_grid["sw_lat"].min()) / 2
    mid_lng = (df_grid["sw_lng"].min() + df_grid["ne_lng"].max()) / 2
    m = folium.Map(location=[mid_lat, mid_lng], 
               zoom_start=14,
               tiles=None)
    folium.TileLayer(
                        tiles='https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
                        attr='© OpenStreetMap contributors',
                        name='Layer',   # ← 레이어 컨트롤에 표시될 이름
                        show=True
                    ).add_to(m)

    # ── 구역 경계 표시 ──────────────────────────────────────────────
    if polygon_coords is not None:
        # 다각형 구역
        folium.Polygon(
            locations=polygon_coords,
            color="blue", weight=2, fill=True, fill_opacity=0.05,
            tooltip="격자 전체 영역"
        ).add_to(m)
        poly = Polygon([(lng, lat) for lat, lng in polygon_coords])
    else:
        # bounding box 구역
        grid_lat_min = df_grid["sw_lat"].min()
        grid_lat_max = df_grid["ne_lat"].max()
        grid_lon_min = df_grid["sw_lng"].min()
        grid_lon_max = df_grid["ne_lng"].max()
        folium.Rectangle(
            bounds=[[grid_lat_min, grid_lon_min], [grid_lat_max, grid_lon_max]],
            color="blue", weight=2, fill=True, fill_opacity=0.05,
            tooltip="격자 전체 영역"
        ).add_to(m)
        poly = None

    # ── 건물 마커 (태그별 레이어 + 클러스터 적용) ───────────────────
    for key, df in dfs.items():

        # 가중치 0인 태그(중요도 없음)는 지도에 표시하지 않음
        if dfs[key]['score'].iloc[0] == 0:
            continue

        # 태그별 레이어 컨트롤 그룹 생성
        layer = folium.FeatureGroup(name=key)

        # 레이어 내 마커 클러스터 생성 (밀집 마커를 자동으로 묶어줌)
        marker_cluster = MarkerCluster().add_to(layer)

        # ── 구역 내 건물 필터링 ──────────────────────────────────────
        if polygon_coords is not None:
            lat_list = [c[0] for c in polygon_coords]
            lng_list = [c[1] for c in polygon_coords]
            # 1차: bounding box로 후보 추림
            filtered = df[
                (df['latitude']  >= min(lat_list)) &
                (df['latitude']  <= max(lat_list)) &
                (df['longitude'] >= min(lng_list)) &
                (df['longitude'] <= max(lng_list))
            ].copy()
            # 2차: 실제 다각형 내부만 필터링
            mask     = filtered.apply(lambda r: poly.contains(Point(r['longitude'], r['latitude'])), axis=1)
            filtered = filtered[mask]
        else:
            filtered = df[
                (df['latitude']  >= grid_lat_min) &
                (df['latitude']  <= grid_lat_max) &
                (df['longitude'] >= grid_lon_min) &
                (df['longitude'] <= grid_lon_max)
            ].copy()

        # 해당 구역에 건물이 없으면 스킵
        if filtered.empty:
            continue

        # 건물별 마커 생성 → 클러스터에 추가
        for _, row in filtered.iterrows():
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                tooltip=row['name'],
                popup=folium.Popup(row['name'], max_width=200),
                icon=ICON_MAP.get(key, folium.Icon(color="gray", icon="question", prefix="fa"))
            ).add_to(marker_cluster)

        # 완성된 레이어(클러스터 포함)를 지도에 추가
        layer.add_to(m)

    # ── 레이더 위치 및 커버 범위 표시 ──────────────────────────────
    # df_final에서 격자 인덱스별 커버 밀집도 딕셔너리 생성
    coverage_map = {}
    if df_final is not None:
        coverage_map = df_final.set_index('grid_idx')[
            ['covered_population', 'covered_area_density']
        ].to_dict('index')

    # 레이더별 랜덤 색상 생성 함수
    def random_color():
        r = random.randint(50, 200)
        g = random.randint(50, 200)
        b = random.randint(50, 200)
        return f"#{r:02x}{g:02x}{b:02x}"

    # show_rank 지정 시 상위 N개만 표시
    rank_items = list(rank_dic.items())
    if show_rank is not None:
        rank_items = rank_items[:show_rank]

    for rank, (key, item) in enumerate(rank_items, start=1):
        loca         = df_grid.loc[key, ['center_lat', 'center_lng']].values
        color        = random_color()

        # 해당 격자의 커버 밀집도 조회 (없으면 0)
        covered_pop  = coverage_map.get(key, {}).get('covered_population', 0)
        covered_area = coverage_map.get(key, {}).get('covered_area_density', 0)
        pop_text     = f"{covered_pop:,.0f}"
        area_text    = f"{covered_area:,.0f}"

        # 순위별 레이어 생성
        radar_layer = folium.FeatureGroup(name=f'{rank}순위 레이더')

        # 레이더 위치 마커 (순위 번호 표시 커스텀 아이콘)
        folium.Marker(
            location=loca,
            tooltip=f"{rank}순위 레이더 | 점수: {item:.4f} | 커버 인구밀집도: {pop_text} | 커버 면적밀집도: {area_text}",
            popup=folium.Popup(
                f"""
                <b>{rank}순위 레이더</b><br>
                grid_id: {key}<br>
                점수: {item:.4f}<br>
                커버 인구밀집도 합: {pop_text}<br>
                커버 면적밀집도 합: {area_text}
                """,
                max_width=200
            ),
            icon=folium.DivIcon(
                html=f"""
                    <div style="
                        background-color: {color}; color: white;
                        font-size: 13px; font-weight: bold;
                        width: 28px; height: 28px; border-radius: 50%;
                        display: flex; align-items: center; justify-content: center;
                        border: 2px solid white; box-shadow: 2px 2px 4px rgba(0,0,0,0.4);
                    ">{rank}</div>
                """,
                icon_size=(28, 28), icon_anchor=(14, 14)
            )
        ).add_to(radar_layer)

        # 레이더 커버 반경 원 표시
        folium.Circle(
            location=loca, radius=RANGE_KM * 1000,
            color=color, fill=True, fill_color=color, fill_opacity=0.15,
            tooltip=f"{rank}순위 커버 범위"
        ).add_to(radar_layer)

        radar_layer.add_to(m)

    # ── 레이어 컨트롤 추가 및 저장 ─────────────────────────────────
    folium.LayerControl(collapsed=False).add_to(m)
    m.save("map.html")
    print("저장 완료: map.html")