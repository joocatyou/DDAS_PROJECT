# D-DAS : 대드론 방어체계 최적 입지 선정 서비스

<div align="center">

**Drone Defense Allocation Service**

> 서울시 도심 환경을 고려한 대드론 방어체계(C-UAS) 최적 배치 지점을 자동 산출하는 데이터 기반 의사결정 지원 웹 서비스

[![Python](https://img.shields.io/badge/Python-3.14+-blue?logo=python)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red?logo=streamlit)](https://streamlit.io/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-orange?logo=mysql)](https://www.mysql.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

</div>

---

## 목차

1. [프로젝트 개요](#-프로젝트-개요)
2. [주요 기능](#-주요-기능)
3. [서비스 흐름](#-서비스-흐름)
4. [기술 스택](#-기술-스택)
5. [폴더 구조](#-폴더-구조)
6. [설치 및 실행](#-설치-및-실행)
7. [데이터 수집 방법](#-데이터-수집-방법)
8. [알고리즘 설명](#-알고리즘-설명)
9. [화면 구성](#-화면-구성)
10. [환경 변수 설정](#-환경-변수-설정)
11. [팀원 소개](#-팀원-소개)

---

## 프로젝트 개요

D-DAS(**Drone Defense Allocation Service**)는 도심 내 드론 위협에 대응하기 위한 **대드론 방어 무기(C-UAS)의 최적 배치 지점**을 자동으로 산출하는 웹 기반 의사결정 지원 서비스입니다.

### 배경 및 필요성

최근 소형 드론의 급격한 보급으로 인해 도심 상공에서의 불법 드론 침입, 테러, 정보 수집 등 드론 관련 보안 위협이 증가하고 있습니다. 특히 서울과 같은 고밀도 도심 환경에서는:

- 주요 시설(공항, 군사 시설, 정부 청사 등)에 대한 방어 필요성 증가
- 드론 방어 무기의 한정된 자원을 **최적 배치**하여 커버리지를 극대화할 필요
- 복수의 시설과 위협 가중치를 동시에 고려한 **데이터 기반 의사결정** 부재

D-DAS는 이러한 문제를 해결하기 위해 서울시 전역 데이터를 크롤링·수집하고, 격자(Grid) 기반의 최적화 알고리즘을 적용하여 방어 무기 배치 최적 후보지를 자동으로 추천합니다.

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **데이터 탐색** | 서울시 전역의 수집 데이터를 인터랙티브 지도에서 시각화 |
| **후보지 조건 설정** | 격자 크기, 사정거리, 시설 유형별 가중치를 사용자가 직접 설정 |
| **후보지 자동 계산** | 설정된 조건에 따라 알고리즘이 최적 배치 지점을 자동 산출 |
| **결과 시각화** | 후보지별 상세 점수 확인 및 지도 위 시각화 |
| **시나리오 비교** | 서로 다른 변수 조합(시나리오)을 저장하고 상호 비교 |
| **회원 인증** | 로그인/회원가입 기반의 사용자 관리 및 개인별 시나리오 저장 |

---

## 서비스 흐름

```
[로그인 / 회원가입]
        ↓
[1단계] 데이터 탐색
  └─ 서울시 주요 시설 데이터를 지도에서 확인
  └─ 시설 유형별 분포 현황 파악
        ↓
[2단계] 후보지 조건 설정
  └─ 분석 구역(격자) 생성
  └─ 방어 무기 사정거리 설정
  └─ 시설 유형별 위협 가중치 설정
        ↓
[3단계] 후보지 계산
  └─ 격자별 커버 가능 시설 탐색
  └─ 가중치 합산 기반 점수 산출
  └─ 상위 N개 최적 배치 지점 선정
        ↓
[4단계] 결과 확인 및 활용
  └─ 후보지 점수 상세 조회
  └─ 지도 위 배치 결과 시각화
  └─ 시나리오 저장 및 비교 분석
```

---

## 기술 스택

### Frontend / UI
| 기술 | 설명 |
|------|------|
| [Streamlit](https://streamlit.io/) | Python 기반 멀티페이지 웹 앱 프레임워크 |
| [Folium](https://python-visualization.github.io/folium/) | Leaflet.js 기반 인터랙티브 지도 시각화 |
| [Plotly](https://plotly.com/python/) | 차트 및 데이터 시각화 |

### Backend / 데이터 처리
| 기술 | 설명 |
|------|------|
| Python 3.10+ | 메인 개발 언어 |
| pandas / numpy | 데이터 전처리 및 수치 연산 |
| scikit-learn | 거리 계산에 활용 |
| pymysql | MySQL 데이터베이스 연결 |

### 데이터베이스
| 기술 | 설명 |
|------|------|
| MySQL 8.0 | 사용자 계정, 시나리오, 전처리 데이터 저장 |

### 데이터 수집
| 기술 | 설명 |
|------|------|
| BeautifulSoup | 정적 웹페이지 HTML 파싱 및 크롤링 |
| Selenium | 동적 웹페이지 자동화 크롤링 |
| Jupyter Notebook | 탐색적 데이터 분석(EDA) 및 프로토타이핑 |

---

## 폴더 구조

```
project/
│
├── DDAS.py                  # 메인 앱 진입점 (로그인 & 홈 화면)
├── run.py                   # 앱 실행 보조 스크립트
├── setup.py                 # 가상환경 생성 및 패키지 설치 스크립트
├── setup.bat                # 가상환경 생성 및 패키지 설치 스크립트
├── utils.py                 # 공통 유틸 함수 (배너, 회원가입 폼 등)
├── data_crawl.ipynb         # 데이터 크롤링 탐색 노트북
├── main_test.ipynb          # 기능 통합 테스트 노트북
├── make_grid.html           # 격자 생성 시각화 HTML
├── map.html                 # 지도 시각화 HTML
├── git                      # git 관련 설정 파일
├── .gitignore               # git 추적 제외 파일 목록
│
├── .streamlit/
│   └── secrets.toml         # DB 연결 정보 (로컬에서 직접 생성 필요)
│
├── .vscode/
│   └── settings.json        # VSCode 편집기 설정
│
├── pages/                   # Streamlit 멀티페이지 모듈
│   ├── 1_데이터 탐색.py       # 서울시 데이터 지도 시각화
│   ├── 2_후보지 조건 설정.py  # 격자/사정거리/가중치 설정
│   ├── 3_후보지 계산.py       # 최적 입지 알고리즘 실행
│   ├── 4_결과 요약.py         # 결과 상세 점수 및 시각화
│   └── 5_시나리오 분석.py     # 다중 시나리오 비교
│
├── get/                     # 데이터 수집(크롤링) 모듈
│   └── get.py               # DB 초기화 및 데이터 삽입 함수 (create_db, set_data 등)
│   └── get_server.py        # DB SERVER 초기화 및 데이터 삽입 함수 (create_db_server, set_data_server 등)
│
├── calculate/               
│   └── calculate.py         # 최적 입지 계산 알고리즘 모듈
│
├── visualize/               
│   └── visualize.py         # 지도/차트 시각화 모듈
│
├── db/                      
│   └── db.py                # DB 스키마 및 push 모듈
│   └── db_server.py         # DB SERVER 스키마 및 push 모듈
│
├── data/                    # 원본 크롤링 데이터 (CSV, JSON 등)
│
├── final_data/              # 전처리 완료 데이터
│
└── images/                  # UI에 사용되는 이미지 리소스
```

---

## 설치 및 실행

### 사전 요구사항

- Python **3.10** 이상
- MySQL **8.0** 이상 (로컬 또는 원격 서버)
- Git

---

### 1단계 — 저장소 클론

```bash
git clone https://github.com/crawlteam4/project.git
cd project
```

---

### 2단계 — 환경 설정 (가상환경 + 패키지 설치)

**macOS / Linux:**

```bash
python setup.py
```

**Windows:**

```bat
setup.bat
```

> `setup.py` / `setup.bat`을 실행하면 자동으로 Python 가상환경을 생성하고 필요한 패키지를 설치합니다.

수동으로 설치하려면:

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt   # (또는 setup.py 내 목록 참고)
```

---

### 3단계 — DB 연결 정보 설정

프로젝트 루트에 `.streamlit/secrets.toml` 파일을 생성하고 아래 내용을 입력합니다:

```toml
[mysql]
host     = "your_mysql_host"       # 예: "localhost" 또는 원격 IP
port     = 3306
user     = "your_mysql_username"
password = "your_mysql_password"
database = "your_database_name"
```

> 이 파일은 `.gitignore`에 포함되어 있어 절대 Git에 커밋되지 않습니다. 로컬에서만 관리하세요.

---

### 4단계 — 앱 실행

```bash
streamlit run DDAS.py
```

브라우저에서 `http://localhost:8501` 로 접속하면 서비스가 실행됩니다.

> 앱 최초 실행 시 `create_db()` 및 `set_data()` 함수가 자동으로 호출되어 MySQL에 테이블 생성과 초기 데이터 삽입이 이루어집니다.

---

## 데이터 수집 방법

D-DAS는 서울시 전역의 주요 시설 데이터를 웹 크롤링을 통해 수집합니다.

### 수집 데이터 범주 (예시)

| 데이터 종류 | 수집 방법 | 비고 |
|-------------|-----------|------|
| 공항 및 군사 시설 위치 | 공공 데이터 포털 API | 고정밀 좌표 포함 |
| 정부 청사, 국가 주요 시설 | BeautifulSoup (정적 크롤링) | HTML 파싱 |
| 기지국 데이터 | Selenium (동적 크롤링) | JS 렌더링 필요 페이지 |
| 인구 밀도 데이터 | 공공 데이터 포털 CSV | 서울 행정동 단위 |

### 크롤링 파이프라인

```
[웹사이트 / 공공 API]
        ↓
[get/get.py] — BeautifulSoup / Selenium 크롤링
        ↓
[data/] — 원본 데이터 저장 (CSV/JSON)
        ↓
[data_crawl.ipynb] — 탐색적 분석 및 전처리
        ↓
[final_data/] — 정제된 최종 데이터
        ↓
[MySQL DB] — set_data()로 적재
```

---

## 알고리즘 설명

### 격자(Grid) 기반 최적 입지 탐색

1. **격자 생성**: 서울시 영역을 사용자가 설정한 크기(예: 500m × 500m)의 격자로 분할합니다.
2. **커버리지 계산**: 각 격자 셀 중심에서 사용자가 설정한 **사정거리(반경)** 내에 포함되는 주요 시설 목록을 탐색합니다.
3. **가중치 합산 점수 계산**:
   - 각 시설 유형에 사용자가 설정한 **가중치(Weight)**를 곱하여 합산
   - `Score = Σ (시설_가중치 × 포함 여부)`
4. **최적 후보지 선정**: 점수가 높은 상위 N개 격자를 최적 배치 후보지로 선정합니다.
5. **결과 시각화**: Folium 지도 위에 선정된 후보지를 마커 및 반경 원으로 표시합니다.

### 핵심 모듈

```python
# calculate/ 모듈 내 핵심 로직 (개략)

def calculate_optimal_positions(grid_size, range_km, weights, facilities_df):
    """
    grid_size  : 격자 한 변의 길이 (km)
    range_km   : 방어 무기 사정거리 (km)
    weights    : 시설 유형별 가중치 딕셔너리
    facilities : 수집된 시설 좌표 데이터프레임
    """
    grids = generate_grid(seoul_bounds, grid_size)
    scores = []
    for cell in grids:
        nearby = find_facilities_in_range(cell.center, range_km, facilities_df)
        score = sum(weights[f.type] for f in nearby)
        scores.append((cell, score))
    return sorted(scores, key=lambda x: x[1], reverse=True)
```

---

## 화면 구성

### 홈 (로그인 화면)
- D-DAS 서비스 소개 및 4단계 이용 가이드 표시
- ID/PW 기반 로그인 폼
- 회원가입 다이얼로그 (모달)

### 1. 데이터 탐색
- 서울시 전역 수집 데이터를 Folium 인터랙티브 지도에 마커로 표시
- 시설 유형 필터링 및 분포 현황 확인

### 2. 후보지 조건 설정
- 격자 크기 슬라이더 (예: 0.5km ~ 5km)
- 방어 무기 사정거리 설정
- 시설 유형별 가중치 설정 (공항, 군사, 정부, 인구 밀집 등)

### 3. 후보지 계산
- 조건 요약 확인 후 계산 실행
- 실시간 진행 표시 (Streamlit progress bar)
- 결과 상위 후보지 테이블 및 지도 표시

### 4. 결과 요약
- 후보지별 상세 점수 및 포함 시설 목록
- Plotly 차트를 활용한 비교 시각화

### 5. 시나리오 분석
- 복수의 시나리오를 저장(MySQL)하고 조건/결과를 나란히 비교

---

## 환경 변수 설정

| 변수 | 설명 | 예시 |
|------|------|------|
| `mysql.host` | MySQL 서버 호스트 | `"localhost"` |
| `mysql.port` | MySQL 포트 | `3306` |
| `mysql.user` | MySQL 사용자명 | `"root"` |
| `mysql.password` | MySQL 비밀번호 | `"password123"` |
| `mysql.database` | 사용할 DB 이름 | `"ddas_db"` |

모든 환경 변수는 `.streamlit/secrets.toml`에 작성하며, `st.secrets["mysql"]["host"]` 형태로 코드 내에서 참조됩니다.

---

## 팀원 소개

| 이름 | 역할 | 담당 업무 |
|------|------|-----------|
| 안찬이 | 프로젝트 매니저 | 기획서 작성, 역할 분담, 일정 조율, 발표 |
| 주진성 | 알고리즘 개발 | 최적 입지 계산 알고리즘, 함수 모듈화 |
| 김민주 | UI/UX 디자인 | Streamlit 페이지 설계, 시각화 모듈, pages 구성 |
| 권희성 | 데이터 크롤링 | 데이터 수집 자동화, 전처리, DB 설계 및 적재 |

---

## 참고 자료

- [Streamlit 공식 문서](https://docs.streamlit.io/)
- [Folium 공식 문서](https://python-visualization.github.io/folium/)
- [서울 열린데이터 광장](https://data.seoul.go.kr/)
- [공공데이터포털](https://www.data.go.kr/)

---

## 라이선스

본 프로젝트는 학습 및 연구 목적으로 개발되었습니다.