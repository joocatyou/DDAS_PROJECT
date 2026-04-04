import streamlit as st
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine
import folium
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster
from shapely.wkt import loads
from shapely.geometry import box
import json
import base64
import pymysql
from utils import set_common_banner

# if "logged_in" not in st.session_state or not st.session_state.logged_in:
#     st.error("로그인이 필요합니다.")
#     st.stop()  # 이 아래 코드는 실행되지 않음
    
# 1. 초기 설정 및 데이터 매핑

@st.cache_resource
def get_engine():
    """
    SQLAlchemy 엔진을 생성하여 반환한다. (캐시 적용)

    st.secrets에서 MySQL 접속 정보를 읽어 엔진을 생성한다.

    Returns
    -------
    engine : sqlalchemy.engine.Engine
        MySQL 데이터베이스 연결 엔진
    """
    conf = st.secrets["mysql"]
    driver = "mysql+pymysql"
    url = f"{driver}://{conf['user']}:{conf['password']}@{conf['host']}:{conf['port']}/{conf['database']}?charset=utf8mb4"
    return create_engine(url)


FACILITY_MAP = {
    "국가중요시설": {
        "전력시설 (electricity)": ["변전소"],
        "정보통신시설 (telecommunication)": ["통신망", "금융"],
        "국가 공공기관 시설 (public)": ["국가유산", "중앙행정기관", "지방행정기관"],
        "교통 항공 항만 시설 (transportation)": ["차량기지", "철도", "공항", "교량", "터널"],
        "수원 시설 (water)": ["지방정수장", "배수지"],
        "지하공동구 (infra)": ["공동구"],
        "산업 시설 (factory)": ["산업시설"],
        "병원 (hospital)": ["병원", "혈액검사센터", "혈액원"],
        "과학연구 (science)": ["과학연구"],
        "교정 시설 (prison)": ["교정시설"],
        "방송시설 (broadcast)": ["방송국"]
    },
    "RF신호 밀집도": {
        "기지국 (frequency)": ["기지국"]
    }
}

TABLE_NAME_MAP = {
    "전력시설 (electricity)": "electricity", "정보통신시설 (telecommunication)": "telecommunication",
    "국가 공공기관 시설 (public)": "public", "교통 항공 항만 시설 (transportation)": "transportation",
    "수원 시설 (water)": "water", "지하공동구 (infra)": "infra", "산업 시설 (factory)": "factory",
    "병원 (hospital)": "hospital", "과학연구 (science)": "science", "교정 시설 (prison)": "prison",
    "방송시설 (broadcast)": "broadcast", "기지국 (frequency)": "frequency"
}

GRID_MAP = {
    "인구 밀집도": "population_raw",
    "건물 고도&밀집도": "density"
}

# 2. 데이터 처리 함수 (Business Logic)

@st.cache_data
def load_facility_data(target_mids, sel_tag):
    """
    선택된 중분류와 소분류(태그)에 해당하는 시설물 데이터를 DB에서 조회한다. (캐시 적용)

    Parameters
    ----------
    target_mids : list of str
        조회할 중분류 이름 목록 (TABLE_NAME_MAP의 키)
    sel_tag : list of str
        필터링할 소분류(태그) 이름 목록. 빈 리스트이면 전체 조회.

    Returns
    -------
    DataFrame
        조회된 시설물 데이터. 컬럼: name, latitude, longitude, tag, mid_cat.
        조회 결과가 없으면 빈 DataFrame 반환.
    """
    engine = get_engine()
    all_df = []
    for m_disp in target_mids:
        table = TABLE_NAME_MAP.get(m_disp)
        if not table: continue
        
        query = f"SELECT name, latitude, longitude, tag FROM `{table}`"
        if sel_tag:
            tag_str = "', '".join(sel_tag)
            query += f" WHERE tag IN ('{tag_str}')"
        
        df = pd.read_sql(query, engine)
        if not df.empty:
            df['mid_cat'] = m_disp
            all_df.append(df)
            
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

@st.cache_data
def load_grid_gdf(g_name):
    """
    격자 분석용 GeoDataFrame을 DB에서 로드한다. (캐시 적용)

    인구 밀집도는 SW/NE 좌표로 Polygon을 생성하고,
    건물 고도·밀집도는 WKT 형식으로 읽어 EPSG:5179 → EPSG:4326으로 변환한다.

    Parameters
    ----------
    g_name : str
        조회할 격자 레이어 이름. GRID_MAP의 키 ('인구 밀집도' 또는 '건물 고도&밀집도')

    Returns
    -------
    GeoDataFrame or None
        gid, 표시값(생활인구 or 토지이용압축도), geometry 컬럼을 포함한 GeoDataFrame.
        조회 결과가 없거나 레이어 이름이 유효하지 않으면 None 반환.
    """
    engine = get_engine()
    table = GRID_MAP.get(g_name)
    if not table: return None

    # 1. 인구 밀집도 처리 (SW/NE 좌표 기반 격자 생성)
    if g_name == "인구 밀집도":
        query = f"SELECT 격자명 as gid, 밀집도 as value, sw_lat, sw_lng, ne_lat, ne_lng FROM `{table}` WHERE 밀집도 > 0"
        df = pd.read_sql(query, engine)
        if df.empty: return None
        
        # 좌표 컬럼을 이용하여 Polygon 생성
        df['geometry'] = df.apply(lambda r: box(r['sw_lng'], r['sw_lat'], r['ne_lng'], r['ne_lat']), axis=1)
        gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
        
        display_name = "생활인구"
        gdf = gdf.rename(columns={'value': display_name})
        return gdf[['gid', display_name, 'geometry']]

    # 2. 건물 고도&밀집도 처리 (EPSG:5179 변환 필요)
    elif g_name == "건물 고도&밀집도":
        # WKT로 읽어와서 CRS 변환 수행
        query = f"SELECT gid, value, geometry FROM `{table}` WHERE value > 0"
        df = pd.read_sql(query, engine)
        if df.empty: return None
        
        df['geometry'] = df['geometry'].apply(loads)
        gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:5179").to_crs(epsg=4326)
        
        display_name = "토지이용압축도"
        gdf = gdf.rename(columns={'value': display_name})
        gdf[display_name] = gdf[display_name].round(2)
        return gdf[['gid', display_name, 'geometry']]

    return None

# 3. UI 함수 (UI Logic)
@st.dialog(" ", width="medium")
def render_help():
    """
    데이터 탐색 페이지의 도움말 다이얼로그를 렌더링한다.

    시설물 지점 분석(Point)과 인구/건물 격자 분석(Grid)의
    기능 설명 및 이용 방법을 안내한다.
    """
    st.subheader('도움말')
    st.write("본 페이지는 서울시의 **시설물(지점)**, **인구/건물(격자)** 데이터를 탐색하는 단계입니다.")
    st.write("") 

    col1, col2 = st.columns([3,3])
    
    with col1:
        # 탭 1에 대한 설명
        st.markdown("##### 시설물 지점 분석 (Point)")
        with st.container(border=True, width=400):
            st.markdown("""
            - **데이터**: 분류별 시설 위치
            - **조작**: `대분류` → `중분류` → `소분류` 순으로 선택
            - **특징**: 서울시 내 건물이나 시설의 위치 확인
            """)
            
    with col2:
        # 탭 2에 대한 설명
        st.markdown("##### 인구/건물 격자 분석 (Grid)")
        with st.container(border=True, width=400):
            st.markdown("""
            - **데이터**: 생활인구 밀집도, 토지이용 압축도
            - **조작**: 별도 분류 없이 **인구, 건물 선택**
            - **특징**: 서울시 전역의 밀집도/고도 흐름 파악
            """)

    st.divider()
    
    # 공통 이용 방법
    st.markdown("##### 이용 방법")
    st.caption("""
        1. 탭 메뉴에서 **시설물 or 인물/건물**을 먼저 선택하세요.  
        2. 원하는 **데이터 조건**을 설정한 후 **[데이터 조회]** 버튼을 클릭하세요.  
        3. 지도에서 결과를 확인하고, 필요한 경우 하단에서 **CSV/GeoJson 파일로 다운로드**하세요.
        """)
    
    st.info("데이터를 확인하고 다음 단계에서 어떤 변수를 얼마만큼의 가중치로 설정할 건지 고려해보세요")

def render_facility_tab():
    """
    시설물 지점 분석 탭을 렌더링한다.

    대분류 → 중분류 → 소분류(태그) 순으로 필터를 선택하고,
    [시설물 데이터 조회] 버튼 클릭 시 Folium 지도에 마커 클러스터로 결과를 표시한다.
    조회 결과는 CSV 파일로 다운로드할 수 있다.
    """
    # 좌측(지도)과 우측(필터)으로 컬럼 분할
    col_map, col_filter = st.columns([4, 1])

    # 1. 오른쪽 컬럼: 필터 및 결과 출력
    with col_filter:
        with st.container(border=True):
            st.markdown("##### 필터 설정")
            sel_main = st.multiselect("대분류 선택", list(FACILITY_MAP.keys()), placeholder="전체 조회",
                                      help='미선택시 전체 선택')
            
            mid_opts = []
            main_list = sel_main if sel_main else list(FACILITY_MAP.keys())
            for m in main_list:
                mid_opts.extend(list(FACILITY_MAP[m].keys()))
            
            sel_mid = st.multiselect("중분류 선택", sorted(list(set(mid_opts))), placeholder="전체 조회")
            
            target_mids = sel_mid if sel_mid else mid_opts
            tag_opts = []
            for m in target_mids:
                for main in FACILITY_MAP:
                    if m in FACILITY_MAP[main]:
                        tag_opts.extend(FACILITY_MAP[main][m])
            
            sel_tag = st.multiselect("소분류(Tag) 선택", sorted(list(set(tag_opts))), placeholder="전체 조회")
            
            # 조회 버튼
            search_btn = st.button("시설물 데이터 조회", key="btn_f", use_container_width=True)

        # --- 버튼 클릭 시 결과(메시지 + 다운로드)를 필터 아래에 표시 ---
        final_df = pd.DataFrame() # 초기화
        if search_btn:
            final_df = load_facility_data(target_mids, sel_tag)
            if not final_df.empty:
                st.success(f"총 {len(final_df)}개 시설물 조회 완료")
                
                csv_data = final_df.to_csv(index=False).encode('utf_8_sig')
                st.download_button(
                    label="CSV 다운로드", 
                    data=csv_data, 
                    file_name='facility_analysis.csv', 
                    mime='text/csv', 
                    use_container_width=True
                )
            else:
                st.warning("조건에 해당하는 데이터가 없습니다.")

    # 2. 왼쪽 컬럼: 지도 출력
    with col_map:
        m = folium.Map(location=[37.549268, 126.988717], zoom_start=12,
                       tiles=None)
        folium.TileLayer(
                    tiles='https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
                    attr='© OpenStreetMap contributors',
                    name='Layer',   # ← 레이어 컨트롤에 표시될 이름
                    show=True
                ).add_to(m)
        
        # 버튼이 눌렸을 때만 지도의 Marker 추가 로직 실행
        if search_btn and not final_df.empty:
            mc = MarkerCluster(name="시설물 클러스터").add_to(m)
            for _, row in final_df.iterrows():
                popup_text = f"<b>{row['name']}</b><br>{row['mid_cat']}<br>Tag: {row['tag']}"
                folium.Marker(
                    [row['latitude'], row['longitude']], 
                    popup=folium.Popup(popup_text, max_width=250),
                    icon=folium.Icon(color='blue', icon='info-sign')
                ).add_to(mc)
        
        folium.LayerControl().add_to(m)
        folium_static(m, width=1200, height=650)


def render_grid_tab():
    """
    인구/건물 격자 분석 탭을 렌더링한다.

    인구 밀집도·건물 고도&밀집도 레이어를 선택하여
    Choropleth 지도로 시각화하고, GeoJSON 파일로 다운로드할 수 있다.
    두 레이어가 모두 선택되면 공간 결합(sjoin)을 통해 통합 툴팁을 제공한다.
    """
    
    # 1. 레이아웃 분할 (지도 4 : 필터 1)
    col_map, col_filter = st.columns([4, 1], gap="medium")

    # 2. 오른쪽 컬럼: 필터 설정 및 결과 출력
    with col_filter:
        with st.container(border=True):
            st.markdown("#####  격자 설정")
            # 분석할 레이어 선택
            sel_grid = st.multiselect(
                "분석 레이어 선택", 
                list(GRID_MAP.keys()), 
                default=list(GRID_MAP.keys()),
                help="지도에 표시할 격자 데이터를 선택하세요."
            )
            
            st.write("")
            # 조회 버튼 (강조색 적용)
            search_btn = st.button("격자 데이터 조회", use_container_width=True)

        # 결과 알림 및 다운로드 버튼 (조회 후에만 등장)
        # 이 영역은 조회 버튼 클릭 시 아래 '지도 로직'에서 생성된 변수를 활용해 채워집니다.
        placeholder_result = st.empty() 

    # 3. 왼쪽 컬럼: 지도 출력
    with col_map:
        # 기본 지도 객체 생성 (기본 서울 중심)
        m_g = folium.Map(location=[37.5665, 126.9780], zoom_start=12, tiles=None)
        folium.TileLayer(
                    tiles='cartodbpositron',
                    name='Layer',   # ← 레이어 컨트롤에 표시될 이름
                    show=True
                ).add_to(m_g)
        
        COLOR_THEME = {"인구 밀집도": "YlOrRd", "건물 고도&밀집도": "PuBu"}
        gdfs_dict = {}
        combined_gdf = None

        if search_btn:
            # 데이터 로드 및 레이어 추가 로직
            for g_name in sel_grid:
                gdf = load_grid_gdf(g_name)
                if gdf is not None:
                    display_col = gdf.columns[1] # '생활인구' 또는 '토지이용압축도'
                    vals = gdf[display_col].dropna()
                    
                    if not vals.empty:
                        # 동적 구간(Bins) 설정
                        thresholds = sorted(list(set([vals.min()] + vals.quantile([0.5, 0.8, 0.9, 0.95, 1.0]).tolist())))
                        
                        # Choropleth 추가
                        folium.Choropleth(
                            geo_data=gdf, 
                            name=g_name, 
                            data=gdf,
                            columns=['gid', display_col], 
                            key_on='feature.properties.gid',
                            bins=thresholds, 
                            fill_color=COLOR_THEME.get(g_name, "Greens"),
                            fill_opacity=0.5, 
                            line_opacity=0.3, 
                            line_color='gray', 
                            highlight=True
                        ).add_to(m_g)
                        
                        gdfs_dict[display_col] = gdf

            # --- 공간 결합 및 툴팁 로직 ---
            if "생활인구" in gdfs_dict and "토지이용압축도" in gdfs_dict:
                pop_gdf = gdfs_dict["생활인구"].copy()
                area_gdf = gdfs_dict["토지이용압축도"].copy()
                pop_gdf['centroid'] = pop_gdf.geometry.centroid
                combined_gdf = gpd.sjoin(
                    pop_gdf.set_geometry('centroid'), 
                    area_gdf[['토지이용압축도', 'geometry']], 
                    how='left', predicate='within'
                )
                combined_gdf = combined_gdf.set_geometry('geometry').drop(columns=['centroid', 'index_right'], errors='ignore')
            elif len(gdfs_dict) == 1:
                combined_gdf = list(gdfs_dict.values())[0]

            # 통합 툴팁 레이어 추가
            if combined_gdf is not None:
                active_fields, active_aliases = ['gid'], ['ID:']
                if '생활인구' in combined_gdf.columns:
                    active_fields.append('생활인구'); active_aliases.append('인구밀도:')
                if '토지이용압축도' in combined_gdf.columns:
                    active_fields.append('토지이용압축도'); active_aliases.append('건물압축도:')

                folium.GeoJson(
                    combined_gdf,
                    name="통합 데이터 툴팁",
                    style_function=lambda x: {'fillColor': 'transparent', 'color': 'transparent'},
                    tooltip=folium.GeoJsonTooltip(fields=active_fields, aliases=active_aliases, localize=True)
                ).add_to(m_g)

                # 우측 필터창 하단에 결과 및 다운로드 버튼 표시
                with placeholder_result.container():
                    st.success(f"{len(combined_gdf)}개 격자 분석 완료")
                    geojson_data = combined_gdf.to_json()
                    st.download_button(
                        label="GeoJSON 다운로드", 
                        data=geojson_data, 
                        file_name='grid_analysis.geojson', 
                        mime='application/json',
                        use_container_width=True
                    )

        # 3. 최종 지도 출력 (버튼 밖: 항상 실행됨)
        folium.LayerControl().add_to(m_g)
        folium_static(m_g, width=1200, height=650)

# 4. 앱 실행

def main():
    """
    데이터 탐색 페이지 진입점.

    공통 배너를 적용하고 시설물 지점 분석·격자 분석 탭을 구성한다.
    """
    set_common_banner()
    st.set_page_config(layout="wide", page_title="C-UAS 통합 분석")

    header_col, help_col = st.columns([10, 1])
    with header_col:
        st.subheader("데이터 탐색")
    with help_col:
        st.write("") # 수직 정렬용 여백
        if st.button("도움말"):
            render_help()


    tab1, tab2 = st.tabs(["시설물 지점 분석", "인구/건물 격자 분석"])
    with tab1:
        render_facility_tab()
    with tab2: 
        render_grid_tab()

if __name__ == "__main__":
    main()