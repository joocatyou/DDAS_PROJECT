from get.get_server import get_engine_server
from sqlalchemy import text

def upload_result_server(df):
    """
    서버 DB 내 새로운 케이스 테이블로 DataFrame 데이터를 업로드한다.

    'master' DB에 연결하여 'result' 데이터베이스 존재 여부를 확인 및 생성하고,
    'result' DB 내 기존 'case' 테이블 번호를 추적하여 다음 순번으로 데이터를 저장한다.

    Parameters
    ----------------------
    df : pandas.DataFrame
        서버 데이터베이스에 저장하고자 하는 결과 데이터셋.

    Returns
    ----------------------
    None
        이 함수는 값을 반환하지 않으며, 작업 단계별 메시지를 출력한다.

    Notes
    ----------------------
    - DB 생성 시 isolation_level="AUTOCOMMIT"을 설정하여 트랜잭션 외부에서 실행한다.
    - 테이블명은 'case{n}' 형식으로 자동 지정되며, 중복 시 'replace' 방식으로 덮어쓴다.
    """

    engine_master = get_engine_server(db_name='master')
    
    autocommit_engine = engine_master.execution_options(isolation_level="AUTOCOMMIT")
    
    with autocommit_engine.connect() as conn:
        # DB 존재 확인
        db_exists = conn.execute(text("SELECT COUNT(*) FROM sys.databases WHERE name = 'result'")).scalar()
        
        if not db_exists:
            print("'result' 데이터베이스가 없어 생성을 시도한다...")
            conn.execute(text("CREATE DATABASE result"))
            print("'result' 데이터베이스 생성 완료!")
        else:
            print("'result' 데이터베이스가 이미 존재한다.")
            
    engine_result = get_engine_server(db_name='result')
    
    try:
        with engine_result.connect() as conn:

            res = conn.execute(text("SELECT name FROM sys.tables WHERE name LIKE 'case%'"))
            tables = [row[0] for row in res]
            
            indices = [int(t.replace('case', '')) for t in tables if t.replace('case', '').isdigit()]
            next_index = max(indices) + 1 if indices else 1
            table_name = f"case{next_index}"

    
            df.to_sql(name=table_name, con=engine_result, if_exists='replace', index=False)
            conn.commit()
            print(f"[{table_name}] 테이블에 저장 성공!")
    except Exception as e:
        print(f"데이터 적재 실패: {e}")
    finally:
        engine_master.dispose()


def delete_result_server(case_name):
    """
    'result' 데이터베이스에서 특정 결과 테이블을 삭제한다.

    Parameters
    ----------------------
    case_name : str
        삭제하고자 하는 테이블의 이름 (예: 'case1').
        SQL Injection 방지 및 특수문자 대응을 위해 대괄호([])로 감싸서 처리한다.

    Returns
    ----------------------
    None
        이 함수는 값을 반환하지 않는다.

    Raises
    ----------------------
    Exception
        DB 연결 실패 또는 DROP TABLE 쿼리 실행 중 오류 발생 시 예외를 출력한다.
    """
    # 1. result DB에 연결 (인자로 'result' 전달)
    engine = get_engine_server(db_name='result')
    
    try:
        with engine.connect() as conn:
            print(f" [{case_name}] 테이블 삭제 시도 중...")

            query = text(f"DROP TABLE IF EXISTS [{case_name}]")
            conn.execute(query)
            
            conn.commit()
            print(f"[{case_name}] 삭제 완료!")
            
    except Exception as e:
        print(f"삭제 중 오류 발생: {e}")
        
    finally:
        engine.dispose()