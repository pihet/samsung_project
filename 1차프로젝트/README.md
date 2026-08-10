# 🛒 BuyOrWait : 실시간 최저가 & AI 시계열 가격 분석기

> **삼성중공업 DT 교육 1차 개인 프로젝트**  
> 다나와(Danawa) 스타일의 메인 디자인 시스템과 머신러닝(ML) 시계열 예측 엔진을 결합하여 가짜 할인을 감지하고 최적의 구매 시점을 알려주는 스마트 쇼핑 보조 웹 서비스입니다.

---

## 📌 프로젝트 핵심 기능 (Key Features)

### 1. 🔍 실시간 상품 수집 및 규격/단가 파싱 (`collector.py`)
- **네이버 쇼핑 API & 실시간 크롤링 연동**: 실시간 최저가, 판매처, 대표 이미지, 상세 스펙 태그 자동 수집.
- **스마트 단위/용량당 단가 계산**: 용량 및 수량(예: 500ml, 12개, 100g)을 자동 감지하여 1개당/100g당 단가 산출.
- **제조사명 자동 정제**: 검색 결과 및 추천 목록에서 브랜드/제조사명을 정제하여 순수 상품명만 직관적으로 표시.

### 2. 🔐 PostgreSQL DB 연동 및 회원 서비스 (`db_manager.py`)
- **보안 회원가입/로그인 모달**: `bcrypt` 단방향 해시 암호화를 적용한 안전한 사용자 인증.
- **회원 전용 찜하기 & 목표가 알림**: 관심 상품 찜 목록 DB 저장, 목표가 설정 및 알림 수신 상태 관리.

### 3. 📊 가격 추세 다중 비교 UX (`app.py` - Tab 3)
- **`[+ 비교함 담기]` & 플로팅 안내 바**: 최대 4개 상품을 선택하여 실시간 가격 추세 및 스펙 다중 비교.
- **고대비 4대 시계열 라인 차트 테마**: 브랜드별 시각적 구분이 명확한 직관적 컬러 팔레트 적용.
- **조회 기간 라디오 필터**: 1개월, 3개월, 6개월, 1년, 전체 기간별 가격 변동 흐름 조회 (기본 3개월).
- **핵심 스펙 & AI 가격 평가 종합 비교표**: 역대 최저가, 구매 적기, 보류 권장 상태를 한눈에 비교.

### 4. 🤖 AI 14일 미래 가격 예측 & 세일 캘린더 연동 (`ml_forecaster.py` & `analyzer.py`)
- **앙상블 시계열 ML 엔진**: Holt Linear Exponential Smoothing (50%) + Ridge Regression (50%) + 요일별 계절성 파동 반영.
- **전국 주요 쇼핑몰 세일 캘린더 DB 연동**: 11번가 월간/그랜드 십일절, G마켓/옥션 빅스마일데이, 블랙프라이데이 등 1년 치 세일 이벤트 감지.
- **세일 할인율 차트 파동 연동**: 14일 미래 차트 선에 세일 시작 당일 예상 할인율(-15~30%)을 직접 하향 굴곡으로 반영.
- **쇼핑몰 세일 임박 알림 전용 카드**: 세일 14일 전 바짝 다가온 세일 이벤트를 감지하여 구매 보류 알림 카드 제공 (다중 세일 중복 지원).

### 5. 💡 차별화 킬러 기능 (`analyzer.py`)
- **[체감 실구매가]:** 최저가 표기 금액에서 **카드 청구할인(5%) + 페이 적립금(1%)**을 차감한 실제 지출 체감가 칩 표시.
- **[AI 가성비 대체 상품 추천]:** 현재 상품과 핵심 스펙(CPU/RAM/SSD/화면 크기 등)이 거의 동일하지만 10%~40% 더 저렴한 대체 모델을 AI가 탐지하여 노출하며, `[이 상품 보기]` 클릭 1번으로 즉시 상세 모달 전환.

---

## 🛠️ 기술 스택 (Tech Stack)

| 구분 | 기술 스택 |
| :--- | :--- |
| **Frontend / UI** | Streamlit, Vanilla CSS (Danawa Style System), Plotly Express & Graph Objects |
| **Backend / Analytics** | Python 3.11, Pandas, NumPy, Statsmodels (Holt), Scikit-Learn (Ridge) |
| **Database & Auth** | PostgreSQL (`buyorwait_db`), SQLite (`price_tracker.db`), psycopg2, bcrypt |
| **Data Collection** | Naver Shopping Open API, Requests, BeautifulSoup4, Regex Parser |

---

## 📂 프로젝트 구조 (Directory Structure)

```text
1차프로젝트/
├── app.py               # 메인 Streamlit 웹 애플리케이션 (GNB, 탭, 모달, UI 레이아웃)
├── collector.py         # 실시간 상품 수집 및 규격/단가 파서
├── analyzer.py          # AI 가격 분석, 체감가 계산기 & AI 가성비 대체 상품 추천 엔진
├── ml_forecaster.py     # Holt + Ridge + 요일계절성 + 세일이벤트 연동 14일 예측 ML 엔진
├── db_manager.py        # PostgreSQL 데이터베이스 관리자 (회원인증, 찜목록, 세일캘린더)
├── database.py          # 로컬 일자별 가격 이력(SQLite) 데이터 관리자
├── config.py            # API 키 및 환경 변수 설정 로더
├── price_tracker.db     # 일자별 가격 이력 시계열 SQLite DB
├── requirements.txt     # 파이썬 라이브러리 의존성 목록
├── .env.example         # API 키 환경변수 템플릿 파일
└── README.md            # 프로젝트 안내 및 아키텍처 문서
```

---

## 🗄️ PostgreSQL 데이터베이스 테이블 구조

### 1. `users` (회원 정보)
```sql
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. `user_favorites` (찜 목록)
```sql
CREATE TABLE user_favorites (
    fav_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    product_id VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    lprice INT NOT NULL,
    target_price INT,
    alert_enabled BOOLEAN DEFAULT TRUE,
    favorited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, product_id)
);
```

### 3. `shopping_sales_events` (쇼핑몰 세일 캘린더)
```sql
CREATE TABLE shopping_sales_events (
    event_id SERIAL PRIMARY KEY,
    event_name VARCHAR(100) NOT NULL,
    mall_name VARCHAR(50) NOT NULL,
    event_type VARCHAR(30) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    discount_rate_avg INT DEFAULT 15,
    recommend_action VARCHAR(50) DEFAULT 'WAIT'
);
```

---

## 🚀 실행 가이드 (How to Run)

### 1. 의존성 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정 (`.env`)
`.env.example` 파일을 복사하여 프로젝트 루트에 `.env` 파일을 생성하고 네이버 API 키를 입력합니다.
```env
NAVER_CLIENT_ID=발급받은_Client_ID
NAVER_CLIENT_SECRET=발급받은_Client_Secret
DB_PASS=1111
```

### 3. Streamlit 웹 애플리케이션 실행
```bash
streamlit run app.py
```
실행 후 웹 브라우저에서 `http://localhost:8501` 주소로 접속합니다.
