import streamlit as st
from sqlalchemy import create_engine, text, inspect
from glob import glob
import pandas as pd
import os
import geopandas as gpd

# ────────────────────────────────────────────────────────────────────────────────
# DB 연결 데이터베이스 생성
# ────────────────────────────────────────────────────────────────────────────────
def create_db():
    """

    st.secrets에 정의된 MySQL 정보를 바탕으로 서버에 접속하며,
    기존 DB가 없을 경우 생성한다.

    Parameters
    ----------------------
    None

    Returns
    ----------------------
    None
    """
    db = st.secrets["mysql"]

    # 특정 DB를 지정하지 않고 서버 자체에 연결 (관리자 권한)
    base_url = (
        f"mysql+pymysql://{db['user']}:{db['password']}"
        f"@{db['host']}:{db['port']}/?charset={db['charset']}"
    )

    # CREATE/DROP DATABASE는 트랜잭션 밖에서 즉시 실행해야 하므로 AUTOCOMMIT 필수
    temp_engine = create_engine(base_url, isolation_level="AUTOCOMMIT")

    try:
        with temp_engine.connect() as conn:
            # 새 DB 생성
            conn.execute(text(f"CREATE DATABASE {db['database']} IF NOT EXISTS CHARACTER SET {db['charset']}"))

    except Exception as e:
        print(f"데이터베이스 초기화 실패: {e}")
    finally:
        temp_engine.dispose()    # 임시 엔진 연결 해제

# ────────────────────────────────────────────────────────────────────────────────
# DB 연결 엔진 생성
# ────────────────────────────────────────────────────────────────────────────────
def get_engine(db_name=None):
    """
    SQLAlchemy 엔진을 생성하여 반환한다.

    Parameters
    ----------------------
    db_name : str, optional
        연결할 데이터베이스의 이름. 지정하지 않으면 st.secrets의 
        기본 database 설정을 사용한다.

    Returns
    ----------------------
    sqlalchemy.engine.base.Engine
        생성된 SQLAlchemy 데이터베이스 엔진 객체.
    """
    db = st.secrets["mysql"]
    database = db_name if db_name else db['database']
    url = (
        f"mysql+pymysql://{db['user']}:{db['password']}"
        f"@{db['host']}:{db['port']}/{database}"
        f"?charset={db['charset']}"
    )
    engine = create_engine(url, pool_pre_ping=True)
    return engine


# ────────────────────────────────────────────────────────────────────────────────
# DB 연결 상태 확인
# ────────────────────────────────────────────────────────────────────────────────
def test_connection(engine):
    """
    단순 쿼리(SELECT 1)를 실행하여 DB 연결 상태를 확인한다.

    Parameters
    ----------------------
    engine : sqlalchemy.engine.base.Engine
        상태를 확인할 데이터베이스 엔진.

    Returns
    ----------------------
    int
        연결 성공 시 1을 반환한다.
    """
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return result.scalar()

# ────────────────────────────────────────────────────────────────────────────────
# 데이터 세팅
# ────────────────────────────────────────────────────────────────────────────────
def set_data():
    """
    로컬의 CSV 및 GeoJSON 파일을 읽어 DB 테이블로 적재한다.

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
    db = st.secrets["mysql"]
    base_url = f"mysql+pymysql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/"
    base_engine = create_engine(base_url)

    with base_engine.connect() as conn:
        result = conn.execute(text("SHOW DATABASES"))
        existing_dbs = [row[0] for row in result]
        if db['database'] not in existing_dbs:
            conn.execute(text(f'CREATE SCHEMA {db['database']} CHARACTER SET {db['charset']}'))
        else:
            print(f"'{db['database']}' 데이터베이스가 이미 존재한다.")
    disconnect_db(base_engine)

    # IMPORT data
    engine = get_engine(db['database'])
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # 2. CSV 파일 처리
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

    # 3. GeoJSON 파일 처리
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


# ────────────────────────────────────────────────────────────────────────────────
# DB 연결 해제
# ────────────────────────────────────────────────────────────────────────────────
def disconnect_db(engine):
    """
    데이터베이스 엔진 연결 풀을 해제하고 리소스를 정리한다.

    Parameters
    ----------------------
    engine : sqlalchemy.engine.base.Engine
        해제할 데이터베이스 엔진.

    Returns
    ----------------------
    None
    """
    engine.dispose()

# ────────────────────────────────────────────────────────────────────────────────
# DB 업로드
# ────────────────────────────────────────────────────────────────────────────────
def upload_result(df):
    """
    DataFrame 데이터를 DB 내 새로운 케이스 테이블로 업로드한다.

    'result' 데이터베이스가 존재하지 않으면 생성하고, 기존에 존재하는 'case' 
    테이블들의 인덱스를 확인하여 그 다음 번호로 새 테이블을 생성해 데이터를 저장한다.

    Parameters
    ----------------------
    df : pandas.DataFrame
        데이터베이스에 저장하고자 하는 결과 데이터셋. 
        비어있지 않은 데이터프레임이어야 한다.

    Returns
    ----------------------
    None
        이 함수는 값을 반환하지 않으며, 작업 완료 메시지를 출력한다.
    """
 
    # DB 생성 
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("CREATE DATABASE IF NOT EXISTS result CHARACTER SET utf8mb4"))
    disconnect_db(engine)

    # result DB에 연결
    engine = get_engine(db_name='result')

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'result' 
            AND table_name LIKE 'case%'
        """))
        tables = [str(row[0]) for row in result]
        if tables:
            max_index = max(int(t.replace('case', '')) for t in tables)
        else:
            max_index = 0

        next_index = max_index + 1

    table_name = f"case{next_index}"
    df.to_sql(name=table_name, con=engine, if_exists='replace', index=False)
    print(f"저장 완료: {table_name}")

    disconnect_db(engine)

# ────────────────────────────────────────────────────────────────────────────────
# DB 테이블 삭제
# ────────────────────────────────────────────────────────────────────────────────
def delete_result(case_name):
    """
    지정한 이름의 결과 테이블을 데이터베이스에서 삭제한다.

    Parameters
    ----------
    case_name : str
        삭제할 테이블의 이름 (예: 'case1', 'case10').
        존재하지 않는 테이블 이름을 입력해도 오류가 발생하지 않도록 처리됨.

    Returns
    ----------
    None

    Raises
    ---------
    sqlalchemy.exc.SQLAlchemyError
        데이터베이스 접속에 실패하거나 SQL 실행 중 예외가 발생할 경우 전달된다.
    """
    engine = get_engine(db_name='result')
    with engine.connect() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS `{case_name}`"))  # 없는 테이블 삭제 시 오류 방지
        conn.commit()

    disconnect_db(engine)



