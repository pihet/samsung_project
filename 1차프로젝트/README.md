# 🛒 BuyOrWait : 진짜 최저가 판별 및 가격 추세 분석 웹 서비스

삼성중공업 DT 교육 1차 개인 프로젝트

---

## 📌 주요 기능
1. **네이버 쇼핑 API 연동**: 실시간 최저가, 상품 정보, 대표 이미지 수집
2. **SQLite 데이터베이스 구축**: 일자별 가격 이력(Time-Series) 자동 저장 및 관리
3. **가짜 할인(Fake Discount) 감지 알고리즘**:
   - 최근 30일 평균가 및 변동성 분석
   - 상시 할인 상품 감지 및 "진짜 할인 점수 (0~100점)" 계산
   - 구매 권장 배지(🟢 지금이 최저가 / 🟡 보통 / 🔴 상시 할인) 부여
4. **Streamlit 웹 UI & Plotly 시각화**: 인터랙티브 라인 차트 및 분석 메트릭 표출

---

## 🚀 실행 방법 (IDE 터미널)

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. 네이버 API 키 설정 (.env 파일 생성)
`.env.example` 파일을 복사하여 `.env` 파일을 생성한 후 발급받은 Key를 입력합니다.
```env
NAVER_CLIENT_ID=발급받은_Client_ID
NAVER_CLIENT_SECRET=발급받은_Client_Secret
```

### 3. Streamlit 웹 애플리케이션 실행
```bash
streamlit run app.py
```
실행 후 웹 브라우저에서 `http://localhost:8501` 주소로 자동으로 대시보드가 열립니다.
