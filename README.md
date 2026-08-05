# 🛒 BuyOrWait : 다나와 스타일 실시간 최저가 분석 & Prophet AI 가격 예측 엔진

> **삼성중공업 DT 개인 프로젝트**  
> 실시간 최저가 추적, 1:1 쇼핑몰 가격 비교, 가짜 할인 감지 알고리즘, 시계열 Prophet AI 14일 미래 가격 예측 대시보드

---

## 🌟 주요 기능 (Key Features)

1. **다나와(Danawa) 스타일 1:1 실시간 최저가 & 쇼핑몰 비교**
   - 대표 이미지, 상세 스펙 카테고리 라인, 쇼핑몰별 가격표(`쿠팡`, `Gmarket`, `SSG.COM`, `11번가`, `AUCTION` 등) 1:1 매칭
   - 단품 vs 묶음 패키지 동적 분류 및 정밀 상품 페이지 직행 연결

2. **가짜 할인(Fake Discount) 판별 알고리즘**
   - 30일/180일 평균가 및 가격 변동성 기준 "진짜 할인 점수 (0~100점)" 계산
   - 🟢 지금이 최저가 / 🟡 보통 / 🔴 상시 할인 배지 자동 부여

3. **Prophet AI 기반 14일 시계열 미래 가격 예측**
   - 시계열(Time-Series) 이력 학습 및 Plotly 인터랙티브 차트 시각화
   - 예측 가격 범위 (Upper / Lower Bound) 및 평균가 가이드라인 제공

4. **단품 / 묶음 (수량) 정밀 검색 파이프라인**
   - 수량 규격(예: 6개, 18개, 24개, 90개) 키워드 1:1 결합 및 쇼핑몰 검색 정밀도 극대화

---

## 🛠️ 기술 스택 (Tech Stack)

- **Language**: Python 3.10+
- **Frontend / Web**: Streamlit, Plotly (Interactive Charts), Custom CSS Design System
- **Machine Learning**: Prophet, Pandas, NumPy
- **Database**: SQLite3
- **Data Collector**: Requests, BeautifulSoup4, Naver Open API
- **Version Control**: Git / GitHub

---

## 🚀 빠른 실행 방법 (Quick Start)

### 1. 레포지토리 클론 및 이동
```bash
git clone https://github.com/pihet/samsung_project.git
cd samsung_project
```

### 2. 필수 라이브러리 설치
```bash
pip install -r requirements.txt
```

### 3. 네이버 API 키 설정 (`.env` 파일)
```env
NAVER_CLIENT_ID=your_client_id
NAVER_CLIENT_SECRET=your_client_secret
```

### 4. 웹 대시보드 실행
```bash
streamlit run app.py
```
실행 후 브라우저에서 `http://localhost:8501` 대시보드가 자동으로 열립니다.

---

## 📁 프로젝트 구조 (Project Architecture)

```
samsung_project/
├── app.py                # Streamlit 메인 웹 애플리케이션
├── collector.py          # 실시간 데이터 수집 & 파싱 엔진
├── database.py           # SQLite 시계열 이력 DB 관리자
├── analyzer.py           # 가짜 할인 감지 & 통계 분석 엔진
├── ml_forecaster.py      # Prophet 시계열 AI 가격 예측기
├── config.py             # 환경 변수 & 설정 파일
├── requirements.txt      # 의존성 패키지 목록
└── README.md             # 프로젝트 소개 문서
```
