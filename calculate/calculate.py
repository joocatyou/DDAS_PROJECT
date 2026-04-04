import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree
import json
from shapely.geometry import Point, Polygon

# ────────────────────────────────────────────────────────────────────────────────
# 건물 커버 계산
# ────────────────────────────────────────────────────────────────────────────────
def building_cover(coords_grid, coords_building, RANGE_KM=1):
    """
    격자 좌표를 기준으로 반경 내 포함되는 건물 정보를 계산하는 함수

    Parameters
    ----------
    coords_grid     : array-like (n, 2) — 격자 중심 좌표 (위도, 경도, degree)
    coords_building : array-like (m, 2) — 건물 좌표 (위도, 경도, degree)
    RANGE_KM        : float — 탐색 반경 (km), 기본값 1km

    Returns
    -------
    df_result : DataFrame
        - grid_id          : 격자 인덱스
        - building_count   : 포함된 건물 개수
        - building_indices : 포함된 건물 인덱스 리스트
    """

    # degree → radian 변환
    grid_rad     = np.deg2rad(coords_grid)
    building_rad = np.deg2rad(coords_building)

    # 건물 좌표 기준 BallTree 생성
    tree = BallTree(building_rad, metric='haversine')

    # 반경 km → radian 변환 (지구 반지름 6371km)
    radius = RANGE_KM / 6371

    # 각 격자 기준으로 반경 내 건물 인덱스 조회
    indices = tree.query_radius(grid_rad, r=radius)

    building_indices = indices
    building_count   = [len(idx) for idx in building_indices]

    df_result = pd.DataFrame({
        'grid_id'          : range(len(coords_grid)),
        'building_count'   : building_count,
        'building_indices' : building_indices,
    })

    return df_result


# ────────────────────────────────────────────────────────────────────────────────
# 단일 좌표 기준 격자 커버 탐색
# ────────────────────────────────────────────────────────────────────────────────
def grid_cover_single(center_coord, all_coords, RANGE_KM=1):
    """
    단일 기준 좌표에서 반경 내 격자 인덱스를 반환하는 함수

    Parameters
    ----------
    center_coord : [lat, lng] — 기준 단일 좌표
    all_coords   : (n, 2) array — 전체 격자 좌표
    RANGE_KM     : float — 커버 반경 (km)

    Returns
    -------
    indices : 반경 내 격자 인덱스 배열 (자기 자신 제외)
    """

    # degree → radian 변환
    all_coords_rad = np.deg2rad(all_coords)
    center_rad     = np.deg2rad(center_coord).reshape(1, -1)

    # 전체 격자 기준 BallTree 생성
    tree = BallTree(all_coords_rad, metric='haversine')

    # 반경 내 이웃 격자 탐색
    radius  = RANGE_KM / 6371
    indices = tree.query_radius(center_rad, r=radius)[0]

    # 자기 자신(중심 좌표와 동일한 격자) 제외
    indices = indices[~np.all(all_coords[indices] == center_coord, axis=1)]

    return indices


# ────────────────────────────────────────────────────────────────────────────────
# 격자별 점수 산출
# ────────────────────────────────────────────────────────────────────────────────
def calc_score(df_building_filtered, df_grid, RANGE_KM):
    """
    각 격자의 커버 점수를 계산하는 함수

    Parameters
    ----------
    df_building_filtered : 필터링된 건물 DataFrame
    df_grid              : 격자 정보 DataFrame
    RANGE_KM             : 레이더 사정거리 (km)

    Returns
    -------
    df_result : 격자별 score가 추가된 DataFrame
    """

    coords_building = df_building_filtered[['latitude', 'longitude']].values
    coords_grid     = df_grid[['center_lat', 'center_lng']].values

    # 각 격자가 커버하는 건물 인덱스 계산
    df_result = building_cover(coords_grid, coords_building, RANGE_KM)

    # 커버된 건물의 score 합산
    scores = []
    for cover in df_result['building_indices'].values:
        sc = sum(df_building_filtered.iloc[grid_no]['score'] for grid_no in cover)
        scores.append(sc)

    df_result['score'] = scores
    return df_result


# ────────────────────────────────────────────────────────────────────────────────
# 최적 레이더 설치 위치 순위 계산
# ────────────────────────────────────────────────────────────────────────────────
def calc_rank(dfs, df_grid, RANGE_KM, radar_num=50, polygon_coords=None):
    """
    최적 레이더 설치 위치를 순위별로 계산하는 함수

    Parameters
    ----------
    dfs            : 건물 DataFrame 딕셔너리 {tag: DataFrame}
    df_grid        : 격자 정보 DataFrame
    RANGE_KM       : 레이더 커버 반경 (km)
    radar_num      : 최대 레이더 수 (기본값 50)
    polygon_coords : 격자 생성에 사용한 다각형 꼭짓점 리스트 [(lat, lng), ...]
                     None이면 bounding box 방식으로 동작

    Returns
    -------
    rank_dic      : {격자 인덱스: 점수} 순위별 레이더 위치
    max_radar_num : 실제 사용된 레이더 수
    """

    rank_dic = {}

    # ── 1. 격자 범위 (bounding box) 계산 ──────────────────────────
    grid_lat_min = df_grid["sw_lat"].min()
    grid_lat_max = df_grid["ne_lat"].max()
    grid_lon_min = df_grid["sw_lng"].min()
    grid_lon_max = df_grid["ne_lng"].max()

    # ── 2. 다각형 또는 bounding box로 건물 필터링 ─────────────────
    if polygon_coords is not None:
        # 다각형 객체 생성 (lat/lng → lng/lat 순서로 변환)
        poly = Polygon([(lng, lat) for lat, lng in polygon_coords])
        lat_list = [c[0] for c in polygon_coords]
        lng_list = [c[1] for c in polygon_coords]
        bb_lat_min, bb_lat_max = min(lat_list), max(lat_list)
        bb_lng_min, bb_lng_max = min(lng_list), max(lng_list)
    else:
        poly = None

    filtered_list = []

    for key, df in dfs.items():
        if polygon_coords is not None:
            # 1차: bounding box로 빠르게 후보 추림
            filtered = df[
                (df['latitude']  >= bb_lat_min) &
                (df['latitude']  <= bb_lat_max) &
                (df['longitude'] >= bb_lng_min) &
                (df['longitude'] <= bb_lng_max)
            ].copy()
            # 2차: 실제 다각형 내부 건물만 필터링
            mask     = filtered.apply(lambda r: poly.contains(Point(r['longitude'], r['latitude'])), axis=1)
            filtered = filtered[mask]
        else:
            # bounding box 방식
            filtered = df[
                (df['latitude']  >= grid_lat_min) &
                (df['latitude']  <= grid_lat_max) &
                (df['longitude'] >= grid_lon_min) &
                (df['longitude'] <= grid_lon_max)
            ].copy()

        filtered_list.append(filtered)

    df_building_filtered = pd.concat(filtered_list, ignore_index=True)

    # ── 3. 건물 태그별 가중치 정규화 ──────────────────────────────
    # 구역 내 태그별 건물 총 개수로 원본 score를 나누어 단위 점수로 변환
    tag_counts = df_building_filtered['tag'].value_counts()
    df_building_filtered['score'] = df_building_filtered.apply(
        lambda row: row['score'] / tag_counts[row['tag']] if tag_counts[row['tag']] > 0 else 0.0,
        axis=1
    )

    # 가중치가 0인 건물(중요도 없음) 제외
    df_building_filtered = df_building_filtered[df_building_filtered['score'] != 0]

    # 반복 소거용 임시 복사본
    df_building_temp = df_building_filtered.copy()

    # ── 4. 순위별 최적 위치 선정 (Greedy) ─────────────────────────
    max_radar_num = radar_num  # 조기 종료 없을 경우 기본값

    for i in range(radar_num):

        # 현재 남은 건물 기준으로 각 격자 점수 계산
        df_result = calc_score(df_building_temp, df_grid, RANGE_KM)

        # 최고 점수 및 해당 격자 인덱스 추출
        max_score   = df_result['score'].max()
        best_points = list(df_result[df_result['score'] == max_score].index)

        # ── 4-1. 동점 격자 → 커버 범위 가장 넓은 격자 선택 ────────
        if len(best_points) != 1:
            cover_list = []
            for point in best_points:
                center_coord  = df_grid.loc[point, ['center_lat', 'center_lng']].values
                all_coords    = df_grid[['center_lat', 'center_lng']].values
                pos_indices   = grid_cover_single(center_coord, all_coords, RANGE_KM)
                label_indices = df_grid.index[pos_indices]
                cover_list.append(label_indices)

            best_idx      = max(range(len(cover_list)), key=lambda x: len(cover_list[x]))
            position_grid = best_points[best_idx]

        # ── 4-2. 최고 점수 격자가 하나 → 바로 선택 ─────────────────
        else:
            position_grid = best_points[0]

        # 선택된 격자 저장
        rank_dic[position_grid] = max_score
        pos = df_grid.loc[position_grid, ['center_lat', 'center_lng']].values

        # ── 5. 커버된 건물 소거 ────────────────────────────────────
        all_building_coords  = df_building_temp[['latitude', 'longitude']].values
        building_pos_indices = grid_cover_single(pos, all_building_coords, RANGE_KM)

        covered_set      = set(map(tuple, all_building_coords[building_pos_indices]))
        df_building_temp = df_building_temp[
            ~df_building_temp.apply(lambda r: (r['latitude'], r['longitude']) in covered_set, axis=1)
        ]

        # ── 6. 진행 상황 출력 ──────────────────────────────────────
        print('-' * 30)
        print(f'{i+1}순위')
        print(f'위치 : {pos}')
        print(f'점수 : {rank_dic[position_grid]}')
        print(f'남은 시설물 : {len(df_building_temp)}개')

        # 최고점이 음수가 될 때 루프 종료
        if max_score <= 0:
            max_radar_num = i 
            print('-' * 30)
            print(f'수익성이 있는 최대 radar 개수: {max_radar_num}')
            break

    return rank_dic, max_radar_num, df_building_filtered
# ────────────────────────────────────────────────────────────────────────────────
# 건물 태그별 가중치 설정
# ────────────────────────────────────────────────────────────────────────────────
def set_score(dfs, weight_dic):
    """태그별 가중치를 각 건물 DataFrame의 score 컬럼에 일괄 적용"""
    for tag in dfs.keys():
        dfs[tag]['score'] = [weight_dic[tag]] * len(dfs[tag])


# ────────────────────────────────────────────────────────────────────────────────
# 최종 결과 DataFrame 생성
# ────────────────────────────────────────────────────────────────────────────────
def get_df_final(rank_dic, df_grid, df_population, df_area_density, RANGE_KM):
    """
    레이더 순위별 위치·점수·커버 밀집도를 통합한 최종 DataFrame 반환

    Parameters
    ----------
    rank_dic        : {격자 인덱스: 점수} — calc_rank 반환값
    df_grid         : 격자 정보 DataFrame
    df_population   : grid_id, population_density 포함 DataFrame
    df_area_density : grid_id, area_density 포함 DataFrame
    RANGE_KM        : 레이더 커버 반경 (km)

    Returns
    -------
    df_final : 레이더 순위별 결과 DataFrame
    """

    all_coords = df_grid[['center_lat', 'center_lng']].values
    results    = []

    for rank, (grid_idx, score) in enumerate(rank_dic.items(), start=1):
        center_coord = df_grid.loc[grid_idx, ['center_lat', 'center_lng']].values

        # 커버되는 격자 인덱스 추출
        pos_indices   = grid_cover_single(center_coord, all_coords, RANGE_KM)
        covered_grids = df_grid.index[pos_indices]

        # 커버 격자의 인구밀집도 평균
        covered_population = df_population[
            df_population['grid_id'].isin(covered_grids)
        ]['population_density'].sum() / len(covered_grids)

        # 커버 격자의 면적밀집도 평균
        covered_area_density = df_area_density[
            df_area_density['grid_id'].isin(covered_grids)
        ]['area_density'].sum() / len(covered_grids)

        results.append({
            'rank'                : rank,
            'grid_idx'            : grid_idx,
            'center_lat'          : center_coord[0],
            'center_lng'          : center_coord[1],
            'radar_score'         : score,
            'covered_population'  : covered_population,
            'covered_area_density': covered_area_density
        })

    df_final = pd.DataFrame(results)
    return df_final