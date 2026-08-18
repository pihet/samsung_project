# 🛒 BuyOrWait : 실시간 최저가 구매 타이밍 추천 및 AI 시계열 예측 플랫폼

> **삼성 프로젝트 1차 결과보고서 (BuyOrWait)**  
> 이커머스 플랫폼의 상시 할인(가짜 할인) 눈속임을 감지하고, **3계층 데이터 웨어하우스(DW)** 및 **통계적 시계열 AI 모델(Auto-ARIMA)**을 결합하여 향후 14일간의 미래 가격 파동을 예측해 주는 스마트 쇼핑 구매 타이밍 의사결정 웹 서비스입니다.

---

## 📌 1. 프로젝트 핵심 기능 (Key Features)

1. **🔍 다나와 실시간 최저가 수집 & 스펙 파싱 (`collector.py`)**
   - 다나와 정식 상품 코드(`pcode`), 실시간 최저가, 판매처, 대표 이미지, 규격 스펙 자동 수집 및 정제.
2. **🏛️ PostgreSQL 3계층 데이터 웨어하우스 & 데이터 마트 (`database.py`)**
   - **Layer 1 (Raw Ingestion)**: `raw_price_logs` (원천 1회성 크롤링 수집 로그 100% 영구 보존)
   - **Layer 2 (Data Mart)**: `dm_daily_price_clean` (5단계 정밀 전처리 완료 일별 시계열 데이터 마트)
   - **Layer 2 (Forecast Mart)**: `dm_model_forecasts` (Auto-ARIMA 14일 미래 예측가 및 MAPE 오차 보관)
   - **Layer 3 (Serving Mart)**: `product_price_summary` (Streamlit 웹 화면 0.001초 실시간 서빙)
3. **🤖 통계적 시계열 AI 파이프라인 & 14일 미래 예측 (`ml_forecaster.py` & `report.ipynb`)**
   - **ADF + KPSS 3-Way 동적 정상성 검정**: 단위근 및 비정상성 진단 시 1차 차분($d=1$) 적용으로 100% 정상성 확보.
   - **3-Fold Walk-Forward CV**: 시간 순서를 준수하는 교차 검증을 통해 `Auto-ARIMA` 1위 최적 모델 동적 채택.
   - **융-박스(Ljung-Box) 잔차 진단**: $p \ge 0.05$ ($p=0.871$) 도출로 오차가 순수 무작위 화이트 노이즈(White Noise) 상태임을 학술적 검증.
   - **백테스팅 오차 감축 실증**: Raw(2.44%) 대비 Preprocessed(1.24%) 백테스팅으로 **1.20%p 오차 감축 실증 완료**.
4. **📧 bcrypt 보안 회원가입 & Resend API 이메일 알림 (`db_manager.py`)**
   - `bcrypt` 비밀번호 단방향 암호화 해시 및 찜한 상품이 목표가 이하로 하락 시 Resend API 자동 이메일 발송.

---

## 🛠️ 2. 필수 개발 환경 및 시스템 요구사항 (Requirements)

프로젝트를 처음 구동하는 사용자는 다음 개발 환경을 준비해야 합니다.

### 2-1. 시스템 요구사항 (System Requirements)
- **OS**: Windows 10/11, macOS, 또는 Ubuntu Linux
- **Python**: **Python 3.10** 이상 (3.10 ~ 3.12 권장)
- **PostgreSQL**: **PostgreSQL 15** 이상 (기본 포트: 5432)
- **Git**: 최신버전

### 2-2. 파이썬 필수 의존성 패키지 목록 (`requirements.txt`)
아래 패키지들이 `requirements.txt`에 정의되어 있으며, 한 줄 명령어로 자동 설치됩니다.

| 패키지명 | 버전 | 주요 역할 |
| :--- | :--- | :--- |
| **`requests`** | `>=2.31.0` | 다나와 최저가 웹 크롤링 HTTP 요청 |
| **`pandas`** | `>=2.0.0` | 일별 리샘플링, 선형 보간, 시계열 데이터프레임 가공 |
| **`numpy`** | `>=1.24.0` | IQR 통계 수치 연산 및 행렬 계산 |
| **`streamlit`** | `>=1.30.0` | 실시간 인터랙티브 웹 대시보드 UI 프레임워크 |
| **`plotly`** | `>=5.18.0` | 실시간 가격 추세 및 14일 미래 예측 인터랙티브 그래프 |
| **`python-dotenv`** | `>=1.0.0` | `.env` 환경 변수(DB 비밀번호, API 키) 로더 |
| **`scikit-learn`** | `>=1.2.0` | 시계열 회귀 모델 및 평가 지표 연산 |
| **`statsmodels`** | `>=0.14.0` | 시계열 분해, ADF/KPSS 검정, ARIMA, 융-박스 잔차 진단 |
| **`pmdarima`** | `>=2.0.0` | Auto-ARIMA 시계열 자동 하이퍼파라미터 최적화 |
| **`psycopg2-binary`** | `>=2.9.0` | PostgreSQL 데이터베이스 파이썬 드라이버 커넥터 |
| **`bcrypt`** | `>=4.0.0` | 비밀번호 단방향 해시 암호화 보안 |
| **`beautifulsoup4`** | `>=4.12.0` | 웹 수집 HTML 파싱 및 스펙 정보 추출 |
| **`apscheduler`** | `>=3.10.0` | 매일 1회 백그라운드 크롤링 & DW 마트 동기화 배치 |
| **`python-pptx`** | `>=1.0.0` | 파워포인트 발표 슬라이드 생성 |

---

## 🚀 3. 초보자를 위한 단계별 설치 및 실행 순서 (Step-by-Step Guide)

새로운 환경에서 프로젝트를 처음 실행할 때 **1번부터 5번까지 순서대로 실행**해 주세요.

### Step 1: 원격 저장소 클론 (Clone Repository)
터미널(또는 명령 프롬프트 / PowerShell)을 열고 저장소를 클론합니다.
```bash
git clone https://github.com/pihet/samsung_project.git
cd samsung_project/1차프로젝트
```

### Step 2: 파이썬 가상환경 생성 및 활성화 (Virtual Environment)
기존 프로젝트 환경과의 충돌을 방지하기 위해 가상환경을 생성합니다.
```bash
# 가상환경 생성 (python 3.10 이상)
python -m venv venv

# Windows (PowerShell / CMD):
venv\Scripts\activate

# macOS / Linux:
source venv/bin/activate
```

### Step 3: 필수 의존성 패키지 일괄 설치 (Install Dependencies)
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: 환경 변수 설정 (`.env` 파일 작성)
프로젝트 루트 디렉토리(`1차프로젝트/`) 안에 `.env` 파일을 생성하고 본인의 PostgreSQL 접속 정보 및 옵션 API 키를 입력합니다.

```env
# PostgreSQL 설정 (.env)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=buyorwait_db
DB_USER=postgres
DB_PASSWORD=1111

# 이메일 알림 연동 API 키 (선택사항, 없어도 기본 작동 가능)
RESEND_API_KEY=re_your_api_key_here
```

### Step 5: 데이터베이스 초기화 및 수동 1회 배치 실행 (Database Setup)
PostgreSQL에 `buyorwait_db` 데이터베이스가 생성되어 있어야 하며, 아래 명령어로 3계층 DW 테이블을 생성하고 초기 데이터 마트를 빌드합니다.

```bash
# 1. 3계층 DW 스키마 테이블 생성 및 데이터 마트 초기화
python database.py

# 2. 다나와 인기 키워드 수집 및 데이터 마트 동기화 1회 배치 실행
python daily_collector.py
```

### Step 6: Streamlit 웹 애플리케이션 가동 (Run Streamlit App)
```bash
streamlit run app.py
```
명령어를 실행하면 웹 서버가 가동되며, 브라우저에서 자동으로 `http://localhost:8501` 이 열립니다.

---

## 📂 4. 디렉토리 구조 및 핵심 파일 안내 (Project Structure)

```text
1차프로젝트/
├── app.py                      # 메인 Streamlit 웹 애플리케이션 (GNB, 탭, 모달, UI 카드리아아웃)
├── collector.py                # 다나와 실시간 웹 크롤러 및 규격/단가 파서
├── analyzer.py                 # AI 가격 분석, 가짜 할인 탐지기 & 대체 상품 추천 엔진
├── ml_forecaster.py            # Holt + Ridge + 요일 계절성 14일 예측 ML 엔진
├── database.py                 # PostgreSQL 3계층 DW 데이터 마트 관리자
├── db_manager.py               # 회원인증, 찜목록, 목표가 이메일 알림, 세일 캘린더 DB 관리자
├── daily_collector.py          # 하루 1회 수집 & 데이터 마트 동기화 스케줄러 배치
├── config.py                   # 환경 변수 (.env) 로더
├── requirements.txt            # 필수 파이썬 라이브러리 목록
├── .env.example                # 환경 변수 설정 예시 템플릿
├── report.ipynb                # 16단계 정밀 시계열 분석 최종 Jupyter Notebook
├── report.pdf / re_report.pdf  # 16단계 통계 분석 결과 보고서 (PDF)
├── BuyOrWait_최종결과보고서.pptx# 팀 발표용 14슬라이드 파워포인트
└── BuyOrWait_AppleStyle_발표자료.pptx # 애플 미니멀리즘 스타일 29슬라이드 발표 파워포인트
```

---

## 🏛️ 5. PostgreSQL 3계층 DW ERD 스키마 (`buyorwait_db`)

본 시스템은 **Star Schema 구조의 3계층 데이터 웨어하우스**로 작동하며, 8개 전체 테이블이 `products(product_id)` 및 `users(user_id)`를 중심으로 **100% 참조 무결성(ON DELETE CASCADE)**을 보장합니다.

- **`products`**: 마스터 기준 차원 테이블 (Product Master Dimension)
- **`raw_price_logs`**: Layer 1 원천 크롤링 수집 로 로그 테이블
- **`dm_daily_price_clean`**: Layer 2 5단계 전처리 완료 일별 시계열 데이터 마트
- **`dm_model_forecasts`**: Layer 2 Auto-ARIMA 14일 미래 예측가 마트
- **`product_price_summary`**: Layer 3 실시간 웹 대시보드 서빙 마트
- **`users`**: 회원 마스터 테이블
- **`favorites`**: 찜 목록 및 목표 알림가 설정 테이블
- **`shopping_sales_events`**: 쇼핑몰 세일 캘린더 이벤트 테이블

---

## 📜 6. 라이선스 및 문의 (License & Info)
- **팀 프로젝트**: TEAM 1조 (김○○, 박○○, 정○○ / 멘토: 이○○)
- **저작권**: Copyright (c) 2026 BuyOrWait Team. All Rights Reserved.
