# 🛒 BuyOrWait : 실시간 최저가 구매 타이밍 추천 및 AI 시계열 예측 플랫폼

> **삼성중공업 DT 교육 1차 프로젝트 (BuyOrWait)**  
> 이커머스 플랫폼의 상시 할인(가짜 할인) 눈속임을 감지하고, **3계층 데이터 웨어하우스(DW)** 및 **통계적 시계열 AI 모델(Auto-ARIMA)**을 결합하여 향후 14일간의 미래 가격 파동을 예측하는 스마트 구매 타이밍 의사결정 웹 서비스입니다.

---

## 📌 1. 프로젝트 핵심 기능 (Key Features)

### 1. 🔍 다나와 실시간 최저가 크롤링 & 스펙 분석 (`collector.py`)
- **다나와(Danawa) 실시간 연동**: 다나와 정식 상품 코드(`pcode`), 실시간 최저가, 판매처, 대표 이미지, 스펙 태그 자동 파싱.
- **용량/단가 자동 산출**: 상품별 용량 및 수량(예: 16GB 2개, 500ml, 100g당) 감지 단가 표시.
- **상시 할인(가짜 할인) 탐지 엔진**: 최근 가격 변동성(2% 이하) 및 평소 대비 정가 부풀리기 패턴을 판별하여 경고 뱃지 부여.

### 2. 🏛️ PostgreSQL 3계층 데이터 웨어하우스 & 데이터 마트 (`database.py`)
- **Layer 1 (Raw Ingestion)**: `raw_price_logs` ➔ 수집된 1회성 크롤링 로 로그를 100% 영구 적재.
- **Layer 2 (Data Mart)**: `dm_daily_price_clean` ➔ 5단계 전처리(선형보간 3일 제한 + 2.5x IQR 스파이크 정정) 완료 시계열 마트.
- **Layer 2 (Forecast Mart)**: `dm_model_forecasts` ➔ Auto-ARIMA 모델이 예측한 미래 14일 수치 및 MAPE 오차율 보관 마트.
- **Layer 3 (Serving Mart)**: `product_price_summary` ➔ Streamlit 웹 화면에 0.001초 만에 최저가 추천 카드를 띄우는 서빙 마트.
- **외래키(FK) 참조 무결성 100% 완비**: `products` 마스터를 축으로 5개 자식 마트 테이블이 `ON DELETE CASCADE`로 결합되어 고아 데이터(Orphan Record) 0건 실증.

### 3. 🤖 통계적 시계열 AI 파이프라인 & 14일 미래 예측 (`ml_forecaster.py` & `report.ipynb`)
- **ADF + KPSS 3-Way 동적 정상성 검정**: 단위근 및 정상성 불일치 시 1차 차분($d=1$) 적용을 통한 100% 정상성 확보.
- **3-Fold Walk-Forward Cross Validation**: 데이터 유출(Data Leakage)을 차단하는 시간 순서 준수 교차 검증을 거쳐 `Auto-ARIMA` 1위 동적 채택.
- **융-박스(Ljung-Box) 잔차 진단**: $p \ge 0.05$ (p=0.871) 도출로 오차가 순수 무작위 화이트 노이즈(White Noise) 상태임을 학술적 입증.
- **전처리 성능 개선 실증**: Raw(2.44%) vs Preprocessed(1.24%) 백테스팅 오차 **1.20%p 감축 실증 완료**.

### 4. 📧 bcrypt 보안 회원가입 & Resend API 이메일 알림 (`db_manager.py`)
- **보안 회원 인증**: `bcrypt` 단방향 암호화 해시를 적용한 회원가입 및 세션 관리.
- **자동 이메일 알림**: 찜한 관심 상품이 설정한 목표가 이하로 하락(`lprice ≤ target_price`) 시 Resend API를 통해 수신자 메일로 목표가 달성 알림 자동 발송.

---

## 🛠️ 2. 기술 스택 (Tech Stack)

| 구분 | 기술 스택 |
| :--- | :--- |
| **Frontend / UI** | Streamlit, Vanilla CSS, Plotly Express & Graph Objects |
| **Backend & Analytics** | Python 3.10+, Pandas, NumPy, Statsmodels (ARIMA/Decomposition/ADF/KPSS/Ljung-Box), Pmdarima (Auto-ARIMA), Scikit-Learn |
| **Database & DW** | PostgreSQL 15+ (`buyorwait_db`), psycopg2 커넥션 풀 |
| **Data Pipeline** | APScheduler (하루 1회 자동 수집 및 마트 동기화), BeautifulSoup4, Requests |
| **Security & Email** | bcrypt (비밀번호 해시), Resend Email API |
| **Dev & Documentation** | VS Code, Jupyter Notebook (`report.ipynb`), Git/GitHub |

---

## 🏗️ 3. 3계층 데이터 아키텍처 & ERD 스키마

```text
[Layer 1: Raw Ingestion]       [Core Master Dimension]        [Layer 2 & 3: Data Marts / Serving]

 ┌──────────────────┐               ┌──────────────┐               ┌────────────────────────┐
 │  raw_price_logs  │──────────────>│   products   │<──────────────│  dm_daily_price_clean  │
 └──────────────────┘               └──────────────┘               └────────────────────────┘
                                           │                                   │
                                           │                       ┌────────────────────────┐
                                           ├──────────────────────>│   dm_model_forecasts   │
                                           │                       └────────────────────────┘
                                           │                                   │
                                           │                       ┌────────────────────────┐
                                           ├──────────────────────>│ product_price_summary  │
                                           │                       └────────────────────────┘
                                           │
                                    ┌──────────────┐               ┌────────────────────────┐
                                    │  favorites   │──────────────>│ shopping_sales_events  │
                                    └──────────────┘               └────────────────────────┘
                                           │
                                    ┌──────────────┐
                                    │    users     │
                                    └──────────────┘
```

---

## 🚀 4. 설치 및 실행 가이드 (Installation & Setup)

### 4-1. 사전 필수 요구사항 (Prerequisites)
- **Python 3.10** 이상 설치
- **PostgreSQL 15** 이상 서버 가동 (기본 포트: 5432)
- **Git**

### 4-2. 저장소 클론 및 패키지 설치
```bash
# 1. 원격 저장소 클론
git clone https://github.com/pihet/samsung_project.git
cd samsung_project/1차프로젝트

# 2. 파이썬 가상환경 생성 및 활성화 (선택)
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. 필수 패키지 일괄 설치
pip install -r requirements.txt
```

### 4-3. 환경 변수 및 PostgreSQL DB 연결 설정 (`.env`)
프로젝트 루트 경로에 `.env` 파일을 생성하고 본인의 PostgreSQL 연결 정보를 작성합니다.
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=buyorwait_db
DB_USER=postgres
DB_PASSWORD=1111

# 이메일 알림 연동 API 키 (선택)
RESEND_API_KEY=re_your_api_key_here
```

### 4-4. 데이터베이스 및 데이터 마트 초기화
```bash
# PostgreSQL buyorwait_db 3계층 테이블 생성 및 마트 동기화 실행
python database.py

# 하루 1회 수집 및 데이터 마트 동기화 수동 1회 배치 실행
python daily_collector.py
```

### 4-5. Streamlit 웹 서비스 구동
```bash
streamlit run app.py
```
브라우저에서 `http://localhost:8501`로 접속하여 실시간 차트 및 구매 추천 서비스를 이용합니다.

---

## 📂 5. 프로젝트 주요 산출물 (Project Artifacts)

- [`report.ipynb`](file:///c:/project_git/samsung_project/1차프로젝트/report.ipynb) : 16단계 엄격한 시계열 파이프라인 분석 최종 노트북
- [`report.pdf`](file:///c:/project_git/samsung_project/1차프로젝트/report.pdf) : 16단계 통계 보고서 PDF (원본)
- [`re_report.pdf`](file:///c:/project_git/samsung_project/1차프로젝트/re_report.pdf) : 16단계 통계 보고서 PDF (고화질 최종)
- [`BuyOrWait_최종결과보고서.pptx`](file:///c:/project_git/samsung_project/1차프로젝트/BuyOrWait_최종결과보고서.pptx) : 14슬라이드 팀 발표 파워포인트
- [`BuyOrWait_AppleStyle_발표자료.pptx`](file:///c:/project_git/samsung_project/1차프로젝트/BuyOrWait_AppleStyle_발표자료.pptx) : 29슬라이드 애플 미니멀리즘 스타일 발표 파워포인트

---

## 📜 6. 라이선스 및 문의
- **프로젝트 팀**: TEAM 1조 (김○○, 박○○, 정○○ / 멘토: 이○○)
- **저작권**: Copyright (c) 2026 BuyOrWait Team. All Rights Reserved.
