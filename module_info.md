# 모듈 설명서

---

## 1. get 모듈

데이터를 다루는 모듈. DB로부터 필요한 데이터를 받아오고, 받아온 데이터를 전처리하는 등 순위 계산 전 필요한 데이터들을 불러오기 위한 함수들을 모아놓은 모듈이다.

---

### `get_all_data(engine, data_list)`

지정한 데이터 테이블들을 DB로부터 가져온다.

---

### `get_dfs1()`

중요시설 데이터들을 DB로부터 가져오는 함수.

**실행 순서**

1. `secrets.toml`에 저장되어 있는 정보로 DB 연결
2. 지정한 이름의 데이터베이스가 없으면 생성
3. `final_data`에 들어있는 CSV, GeoJSON 형태의 파일들을 모두 DB에 업로드
4. 업로드한 테이블 중 중요시설 데이터들만 필터링하여 `dfs1`으로 저장 후 반환

---

### `get_latest_grid_data()`

다운로드 폴더에서 가장 최근에 생성된 CSV와 JSON 파일을 로드하는 함수.

생성한 구역 격자 및 경계 포인트를 가져오기 위해 사용한다.

---

### `get_df_population(df_pop_raw, df_grid)`

Raw 인구 데이터를 전처리하는 함수. 구역에 맞는 인구 밀집도 데이터로 변환이 필요하기 때문에, 반드시 격자 생성 후 `get_latest_grid_data()`로 `df_grid`를 받아온 뒤에 이 함수를 사용해야 한다.

---

### `get_df_area_density(df_den_raw, df_grid)`

Raw 면적 밀집 데이터를 전처리하는 함수. 구역에 맞는 면적 밀집 데이터로 변환이 필요하기 때문에, 반드시 격자 생성 후 `get_latest_grid_data()`로 `df_grid`를 받아온 뒤에 이 함수를 사용해야 한다.

---

### `get_dfs2(df_grid)`

인구/면적 밀집 데이터를 가져오는 함수.

**실행 순서**

1. DB 연결
2. DB에서 두 가지 테이블을 가져옴
3. `get_df_population(df_pop_raw, df_grid)` 함수와 `get_df_area_density(df_den_raw, df_grid)` 함수를 사용하여 전처리 진행
4. `dfs2`에 저장 후 반환, 연결 해제

---

## 2. db 모듈

MySQL 데이터베이스를 다루는 모듈. DB의 생성, 연결, 연결 해제, 테이블 업로드 등 DB 관련 함수들이 모여있는 모듈이다.

---

### `create_db()`

`secrets`에 담겨있는 정보로 접속해서 데이터베이스가 존재하지 않으면 생성하는 함수.

---

### `get_engine(db_name=None)`

SQLAlchemy를 이용해 DB와 연결하는 함수.

- `db_name=None`이면 `secrets.toml`에 적힌 데이터베이스로 접속
- `db_name`이 `None`이 아니면 해당 이름을 가진 데이터베이스에 연결

---

### `test_connection(engine)`

연결이 잘 되었는지 확인하는 함수.

---

### `set_data()`

`final_data` 폴더 내 CSV와 JSON 파일을 모두 DB에 업로드하는 함수.

이미 Database에 같은 이름의 테이블이 있으면 건너뛰고, 없을 경우에만 올리는 조건을 달아서 나중에 `final_data` 폴더에 포맷에 맞는 다른 데이터들을 올려두면 언제든지 순위 계산 알고리즘에 반영될 수 있게 한다.

---

### `disconnect_db(engine)`

연결된 DB의 연결을 해제하는 함수.

---

### `upload_result(df)`

`result`라는 이름의 데이터베이스를 생성·연결하여 결과로 나온 데이터프레임을 테이블로 업로드하는 함수.

테이블명을 `case1`, `case2`, `case3`… 으로 자동 지정하여 순위 계산으로 진행한 다양한 케이스들의 결과를 `result` 데이터베이스에 누적 저장할 수 있게 한다.

---

### `delete_result(case_name)`

DB에 저장한 특정 케이스를 삭제하는 함수.

---

## 3. calculate 모듈

알고리즘 계산에 들어가는 모든 함수들을 모아놓은 모듈이다.

---

### `building_cover(coords_grid, coords_building, RANGE_KM=1)`

BallTree 패키지를 사용하여 사용자가 지정한 구역 내 모든 격자들마다 사정거리 안에 들어오는 중요 시설물의 인덱스와 총 시설 수를 구해서 `df_result` 데이터프레임으로 만들어 반환한다.

---

### `grid_cover_single(center_coord, all_coords, RANGE_KM=3)`

`building_cover` 함수와 같은 원리로 동작한다. 단일 위도·경도 좌표(`center_coord`)와 여러 개의 위도·경도를 가지고 있는 `all_coords` 리스트를 입력하면, 단일 위도·경도 좌표에 `RANGE_KM` 사정거리의 레이더를 배치했을 때 커버하는 인덱스들을 반환한다. 이 인덱스들은 `all_coords` 중에 커버되는 위치에 있는 인덱스들이다.

---

### `calc_score(df_building_filtered, df_grid, RANGE_KM)`

`building_cover` 함수를 이용해 각 격자가 커버하는 중요시설들의 인덱스를 구한 후, 그 시설들의 가중치에 따라 점수를 합산하여 `score` 컬럼을 추가한 데이터프레임을 반환한다.

---

### `calc_rank(dfs, df_grid, RANGE_KM, radar_num=50, polygon_coords=None)`

최적 레이더 위치를 찾는 핵심 함수.

**실행 순서**

1. `polygon_coords`(사용자가 구역을 생성할 때 찍었던 포인트의 좌표)를 이용해 구역 내부에 있는 중요시설만 필터링
2. 필터링된 중요시설 위치 데이터프레임들을 `concat`으로 합침
3. 점수 정규화 진행
4. `calc_score` 함수를 이용해 구역 내 격자들의 점수 계산
5. 최고 점수를 받은 격자의 인덱스와 점수를 `rank_dic`에 저장
   - 동점자가 발생할 경우, `grid_cover_single` 함수를 이용해 구역 내 더 많은 다른 격자들을 포함한 쪽을 1등으로 선정
6. 1등이 이미 커버한 중요시설들은 소거
7. 모든 중요시설이 커버될 때까지 루프 반복, 모두 커버되면 `break`
8. `rank_dic`과 `min_radar_num`(모두 커버될 때의 레이더 개수) 반환

---

### `set_score(dfs, weight_dic)`

`weight_dic`에 명시된 가중치를 `dfs`에 부여하는 함수.

---

### `get_df_final(rank_dic, df_grid, df_population, df_area_density, RANGE_KM)`

순위가 부여된 격자들이 커버하는 다른 격자들의 인구/면적 밀집도 데이터를 모두 합산하고 평균낸 후, 순위·격자 인덱스·위경도·최종 점수·인구/면적 밀집도 평균값을 모두 담은 `df_result` 데이터프레임으로 만들어 반환한다.

---

## 4. visualize 모듈

순위 계산을 완료한 레이더들의 시각화를 담당하는 모듈이다.

---

### `visualize(df_grid, dfs, rank_dic, RANGE_KM, ICON_MAP, show_rank=None, polygon_coords=None, df_final=None)`

레이더 설치 결과를 지도에 시각화하는 함수.

**실행 순서**

1. 사용자가 지정한 구역의 중간점을 계산하여 Folium map 객체 생성
2. 사용자가 지정한 격자 내부를 필터링하여 반투명한 파란색으로 구역 표시
3. 구역 내 중요 시설물들을 마커로 표시
4. `rank_dic`에 저장되어 있는 순위권 레이더들의 위치를 표시
5. 순위별로 1, 2, 3… 의 숫자를 마커 위에 표시하고, 색도 랜덤으로 겹치지 않게 하여 구분
6. 레이더 커버 반경 원 표시
7. `map.html`로 저장

---

## 5. setup.py

프로그램 실행에 필요한 가상환경과 패키지 설치를 자동화한 스크립트이다.

실행하면 DDAS 프로그램 구동을 위한 새로운 가상환경을 생성하고, 필요한 패키지들을 자동으로 설치한 뒤, DDAS 프로그램까지 자동으로 실행된다. `setup.bat` Windows 배치 파일로 함께 제공되어 파일을 클릭하는 것만으로 전체 과정이 진행된다.

> **※ 아나콘다(Anaconda) 또는 미니콘다(Miniconda)가 반드시 사전에 설치되어 있어야 한다.**

---

## 참고

`get_server`, `db_server`는 각각 `get`, `db` 모듈의 서버 버전으로, 메커니즘은 모두 동일하고 연결되는 DB만 달라지므로 별도로 정리하지 않았다.