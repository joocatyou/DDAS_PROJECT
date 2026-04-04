from get.get import * 
import streamlit as st
from sqlalchemy import create_engine, text
from glob import glob
import urllib

def create_db_server():
    """
    st.secrets에 정의된 dbserver 정보를 바탕으로 SQL 서버에 접속하며,
    기본 master DB에 연결하여 기존에 같은 이름의 데이터베이스가 없으면 생성하는 함수임.

    Parameters
    ----------------------
    None

    Returns
    ----------------------
    None
    """

    db = st.secrets["dbserver"]
    
    # Database 생성을 위해 master database로 접근
    params = urllib.parse.quote_plus(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={db['server']};"
        f"DATABASE=master;" 
        f"UID={db['username']};"
        f"PWD={db['password']};"
        f"TrustServerCertificate=yes;")

    # engine 연결
    engine = create_engine(
        f"mssql+pyodbc:///?odbc_connect={params}",
        isolation_level="AUTOCOMMIT" 
    )

    # Execute 문
    sql = text(f"""
    IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{db['database']}')
    BEGIN
        CREATE DATABASE [{db['database']}];
    END
    """)

    try:
        with engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT").execute(sql)
    except exec as e:
        print(f"데이터베이스 생성 실패: {e}")
    finally:
        engine.dispose()


def get_engine_server(db_name=None):
    """
    SQLAlchemy 엔진을 생성하여 반환함.

    Parameters
    ----------------------
    db_name : str, optional
        연결할 데이터베이스의 이름. 지정하지 않으면 st.secrets의 
        기본 database 설정을 사용함.

    Returns
    ----------------------
    sqlalchemy.engine.base.Engine
        생성된 SQLAlchemy 데이터베이스 엔진 객체.
    """
    db = st.secrets["dbserver"]

    database = db_name if db_name else db['database']
    
    params = urllib.parse.quote_plus(
        f'DRIVER={{ODBC Driver 18 for SQL Server}};'
        f'SERVER={db['server']};'
        f'DATABASE={database};'
        f'UID={db['username']};'
        f'PWD={db['password']};'
        f'TrustServerCertificate=yes;'
    )

    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
    return engine

def get_all_data_server(engine, data_list):
    """
    지정된 테이블 목록을 SQL 서버에서 SELECT하여 딕셔너리로 반환함.

    Parameters
    ----------------------
    engine : sqlalchemy.engine.base.Engine
        연결된 데이터베이스 엔진 객체.
    data_list : list
        조회하고자 하는 테이블 이름들의 리스트.

    Returns
    ----------------------
    dict
        {테이블명: DataFrame} 형태의 결과 딕셔너리.
    """
    dfs = {}
    for data in data_list:
        query = f"SELECT * FROM [{data}]"
        dfs[data] = pd.read_sql(query, engine)
    return dfs


def set_data_server():
    """
    로컬의 CSV 및 GeoJSON 파일을 읽어 DB Sever 테이블로 적재한다.

    final_data 폴더 내의 파일들을 검색하여, DB에 존재하지 않는 
    테이블일 경우에만 새로 생성하고 데이터를 임포트한다.

    Parameters
    ----------------------
    None

    Returns
    ----------------------
    None
    """
    # DATABASE 세팅
    db = st.secrets["dbserver"]

    # IMPORT data
    engine = get_engine_server(db['database'])
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # CSV 파일 처리
    print("--- CSV 데이터 확인 및 적재 시작 ---")
    file_list = glob('final_data/*.csv')

    for file in file_list:
        file_basename = os.path.basename(file)
        raw_name = os.path.splitext(file_basename)[0]
        
        table_name = raw_name[3:] if raw_name.startswith('df_') else raw_name
        
        # 기존 DB에 테이블이 없는 경우에만 적재 진행
        if table_name not in existing_tables:
            print(f"'{table_name}' 테이블 생성 및 데이터 임포트 중...")
            df = pd.read_csv(file)
            df.to_sql(name=table_name, con=engine, if_exists='fail', index=False)
        else:
            print(f"'{table_name}' 테이블은 이미 존재하여 건너뜀.")

    # GeoJSON 파일 처리
    print("\n--- GeoJSON 데이터 확인 및 적재 시작 ---")
    json_list = glob('final_data/*.geojson')

    for json_file in json_list:
        raw_name = os.path.splitext(os.path.basename(json_file))[0]
        json_name = raw_name.split('_')[-1]

        # 기존 DB에 테이블이 없는 경우에만 적재 진행
        if json_name not in existing_tables:
            print(f"'{json_name}' 테이블 생성 및 데이터 임포트 중...")
            gdf = gpd.read_file(json_file)
            
            # geometry 컬럼 문자열 변환
            gdf['geometry'] = gdf['geometry'].apply(lambda x: str(x))
            gdf.to_sql(name=json_name, con=engine, if_exists='fail', index=False)
        else:
            print(f"'{json_name}' 테이블은 이미 존재하여 건너뜀.")
            
    disconnect_db(engine)
    

def load_data_server(engine, data_list):
    """
    초기화가 완료된 DB에서 실제 서비스에 필요한 테이블들을 불러옴.
    단순 조회 기능만 수행하며 캐싱을 통해 성능을 최적화함.

    Parameters
    ----------------------
    data_list : list
        조회하고자 하는 테이블 이름 리스트.

    Returns
    ----------------------
    dict
        {테이블명: DataFrame} 형태의 데이터 딕셔너리.
    """
    try:
        dfs = get_all_data_server(engine, data_list)
    finally:
        # get_all_data_server 내에서 쓰인 엔진 자원 해제
        engine.dispose() 
        
    return dfs


@st.cache_data
def get_dfs1_server():
    """
    SQL 서버에서 데이터베이스 및 테이블을 생성/세팅하고, 특정 키워드를 제외한 
    분석용 테이블들만 필터링하여 데이터프레임 딕셔너리로 반환함.

    최초 실행 시 서버에 DB와 테이블이 없는 경우 생성을 수행하며, 
    'population_raw', 'density', 'users'와 같은 관리 및 원천 데이터 테이블은 
    제외하고 실제 알고리즘 계산에 필요한 데이터만 선택적으로 로드함.

    Parameters
    ----------------------
    None

    Returns
    ----------------------
    dict
        필터링된 {테이블명: DataFrame} 딕셔너리.
    """

    # 데이터 베이스 생성
    create_db_server()

    # 데이터 테이블 세팅
    set_data_server()

    # Connect
    engine = get_engine_server()

    # dfs1 알고리즘 계산에 들어갈 테이블만 필터링
    inspector = inspect(engine)
    all_tables = inspector.get_table_names()
    
    exclude_keywords = ['population_raw', 'density', 'users']
    table_names = []

    for table in all_tables:
        if any(keyword in table for keyword in exclude_keywords):
            continue
        table_names.append(table)

    dfs1 = load_data_server(engine, table_names)

     # 연결 해제
    disconnect_db(engine)
    return dfs1


def get_dfs2_server(df_grid):
    """
    DB에서 원시 데이터를 호출하여 격자 기준의 인구/면적밀집도 데이터프레임을 생성한다.

    Parameters
    ----------------------
    df_grid : pandas.DataFrame
        공간 조인의 기준이 되는 격자 데이터프레임.

    Returns
    ----------------------
    dict
        {'population': df_population, 'area_density': df_area_density} 형태의 딕셔너리.
    """
    engine    = get_engine_server()
    data_list = ['population_raw', 'density']
    dfs2      = get_all_data_server(engine, data_list)

    # 불필요한 인덱스 컬럼 제거 후 밀집도 계산
    df_pop_raw = dfs2['population_raw'].drop(columns='Unnamed: 0')
    df_den_raw = dfs2['density']

    df_population   = get_df_population(df_pop_raw, df_grid)
    df_area_density = get_df_area_density(df_den_raw, df_grid)

    disconnect_db(engine)

    return {
        'population'  : df_population,
        'area_density': df_area_density
    }