import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import importlib
import collector
import analyzer
importlib.reload(collector)
importlib.reload(analyzer)
from database import init_db, save_product_and_price, get_price_history, get_all_products
from collector import search_naver_shopping, generate_mock_price_history
from analyzer import analyze_price_trend
import config

# Streamlit 페이지 설정
st.set_page_config(
    page_title="BuyOrWait - 진짜 최저가 판별 서비스",
    layout="wide"
)

# 데이터베이스 초기화
init_db()

# 커스텀 CSS 디자인 (이미지 카드 높이 고정 및 깔끔한 레이아웃)
st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; font-weight: 700; color: #1E293B; margin-bottom: 0.5rem; }
    .sub-title { font-size: 1.0rem; color: #64748B; margin-bottom: 2rem; }
    
    /* 상품 카드 이미지 컨테이너 고정 높이 */
    .img-box {
        height: 180px;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        background-color: #F8FAFC;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        border: 1px solid #E2E8F0;
    }
    .img-box img {
        max-height: 100%;
        max-width: 100%;
        object-fit: contain;
    }

    /* 상품 제목 및 판매처 고정 높이 (버튼 위치 수평 정렬) */
    .product-title {
        height: 2.8rem;
        line-height: 1.4rem;
        font-weight: 700;
        font-size: 0.95rem;
        color: #F8FAFC;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        margin-bottom: 0.4rem;
    }
    .mall-text {
        font-size: 0.8rem;
        color: #94A3B8;
        height: 1.3rem;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
        margin-bottom: 0.5rem;
    }

    /* 커스텀 메트릭 카드 디자인 */
    .metric-card {
        background: #FFFFFF;
        padding: 1.2rem;
        border-radius: 0.8rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        text-align: center;
    }
    .metric-label { font-size: 0.9rem; color: #64748B; font-weight: 600; margin-bottom: 0.3rem; }
    .metric-value-primary { font-size: 1.5rem; color: #1E40AF; font-weight: 800; }
    .metric-value-gray { font-size: 1.5rem; color: #475569; font-weight: 800; }
    .metric-value-green { font-size: 1.5rem; color: #059669; font-weight: 800; }
    .metric-score-high { background-color: #DCFCE7; color: #166534; font-size: 1.4rem; font-weight: 800; padding: 0.2rem 0.6rem; border-radius: 0.5rem; display: inline-block; }
    .metric-score-mid { background-color: #FEF3C7; color: #92400E; font-size: 1.4rem; font-weight: 800; padding: 0.2rem 0.6rem; border-radius: 0.5rem; display: inline-block; }
    .metric-score-low { background-color: #FEE2E2; color: #991B1B; font-size: 1.4rem; font-weight: 800; padding: 0.2rem 0.6rem; border-radius: 0.5rem; display: inline-block; }
    </style>
""", unsafe_allow_html=True)

# 헤더 영역
st.markdown('<div class="main-title">BuyOrWait: 진짜 최저가 판별기</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">네이버 쇼핑 시계열 가격 데이터 및 분석 엔진으로 상시 할인을 감지하고 구매 적기를 알려드립니다.</div>', unsafe_allow_html=True)

# 사이드바 설정 (API 키 설정 - 이미 설정된 경우 접어둠)
st.sidebar.header("설정")

has_default_keys = bool(config.NAVER_CLIENT_ID and config.NAVER_CLIENT_SECRET)

if has_default_keys:
    with st.sidebar.expander("네이버 API Key 설정 (설정됨)", expanded=False):
        client_id = st.text_input("Naver Client ID", value=config.NAVER_CLIENT_ID, type="password")
        client_secret = st.text_input("Naver Client Secret", value=config.NAVER_CLIENT_SECRET, type="password")
else:
    st.sidebar.subheader("네이버 API 인증 설정")
    client_id = st.sidebar.text_input("Naver Client ID", value=config.NAVER_CLIENT_ID, type="password")
    client_secret = st.sidebar.text_input("Naver Client Secret", value=config.NAVER_CLIENT_SECRET, type="password")
    if not client_id or not client_secret:
        st.sidebar.warning("네이버 API Key를 입력하거나 .env 파일에 설정해 주세요.")

# 탭 구성: 1) 상품 검색 2) 저장된 상품 분석 3) 다중 상품 가격 비교
tab1, tab2, tab3 = st.tabs(["상품 검색 & 실시간 분석", "DB 저장 상품 목록", "다중 상품 가격 비교"])

with tab1:
    with st.form("search_form"):
        col_search, col_btn = st.columns([4, 1])
        with col_search:
            query = st.text_input("검색할 상품명을 입력하세요", placeholder="예: 맥북 프로 14, 코카콜라, 닌텐도 스위치", label_visibility="collapsed")
        with col_btn:
            search_clicked = st.form_submit_button("상품 검색", use_container_width=True)

    if search_clicked:
        if not query or not query.strip():
            st.warning("검색어를 입력해 주세요.")
        elif not client_id or not client_secret:
            st.error("네이버 API Key가 설정되지 않았습니다. 사이드바에서 Client ID와 Secret을 입력해 주세요.")
        else:
            with st.spinner("네이버 쇼핑에서 최저가 데이터를 불러오는 중..."):
                items, error_msg = search_naver_shopping(query, client_id, client_secret, display=40)
                st.session_state['search_items'] = items
                st.session_state['search_error'] = error_msg
                st.session_state['current_page'] = 1  # 페이지 초기화

    # 에러 메시지 표출
    if st.session_state.get('search_error'):
        st.error(f"{st.session_state['search_error']}")

    # 검색 결과 표출 (페이지네이션 적용)
    if 'search_items' in st.session_state:
        items = st.session_state['search_items']
        if not items and not st.session_state.get('search_error'):
            st.warning("검색 결과가 없습니다. 다른 검색어로 검색해 보세요.")
        elif items:
            items_per_page = 8
            total_items = len(items)
            total_pages = (total_items + items_per_page - 1) // items_per_page
            
            if 'current_page' not in st.session_state:
                st.session_state['current_page'] = 1
                
            current_page = st.session_state['current_page']
            
            # 검색 상단 헤더 & 페이지 이동 버튼
            col_h1, col_h2 = st.columns([3, 1])
            with col_h1:
                st.subheader(f"검색 결과 (총 {total_items}건 중 {current_page}/{total_pages} 페이지)")
            with col_h2:
                p_col1, p_col2 = st.columns(2)
                with p_col1:
                    if st.button("◀ 이전", disabled=(current_page <= 1), use_container_width=True):
                        st.session_state['current_page'] -= 1
                        st.rerun()
                with p_col2:
                    if st.button("다음 ▶", disabled=(current_page >= total_pages), use_container_width=True):
                        st.session_state['current_page'] += 1
                        st.rerun()

            # 현재 페이지에 맞는 상품 슬라이싱
            start_idx = (current_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_items = items[start_idx:end_idx]

            # Grid 형태 카드 배치 (4열)
            cols = st.columns(4)
            for idx, item in enumerate(page_items):
                with cols[idx % 4]:
                    img_src = item['image_url'] if item['image_url'] else "https://via.placeholder.com/200?text=No+Image"
                    st.markdown(f'<div class="img-box"><img src="{img_src}" /></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="product-title">{item["title"]}</div>', unsafe_allow_html=True)
                    st.markdown(f"현재 최저가: **{item['lprice']:,}원**")
                    st.markdown(f'<div class="mall-text">판매처: {item["mall_name"]}</div>', unsafe_allow_html=True)
                    
                    if st.button("가격 추세 분석", key=f"btn_{item['product_id']}_{idx}", use_container_width=True):
                        # DB에 저장 & 3년 시계열 생성 (auto 패턴 적용)
                        save_product_and_price(
                            product_id=item['product_id'],
                            title=item['title'],
                            category=item['category'],
                            image_url=item['image_url'],
                            mall_name=item['mall_name'],
                            link=item['link'],
                            price=item['lprice']
                        )
                        generate_mock_price_history(item['product_id'], item['lprice'], days=1095, pattern="auto")
                        st.session_state['selected_product'] = item

    # 선택된 상품 세부 시계열 분석 대시보드
    if 'selected_product' in st.session_state:
        selected = st.session_state['selected_product']
        st.markdown("---")
        
        col_title, col_filter = st.columns([3, 2])
        with col_title:
            st.subheader(f"[{selected['title']}] 가격 변동 상세 분석")
        with col_filter:
            # 기간 선택 필터 버튼
            timeframe = st.radio(
                "분석 기간 선택",
                options=["1개월", "6개월", "1년", "3년", "전체"],
                index=0,
                horizontal=True
            )

        days_map = {
            "1개월": 30,
            "6개월": 180,
            "1년": 365,
            "3년": 1095,
            "전체": None
        }
        selected_days = days_map[timeframe]

        # DB에서 시계열 데이터 로드 및 선택 기간 분석
        df_hist = get_price_history(selected['product_id'])
        analysis = analyze_price_trend(df_hist, days=selected_days)

        # 커스텀 컬러링 메트릭 카드 4종
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">현재 판매가</div>
                    <div class="metric-value-primary">{analysis['current_price']:,}원</div>
                </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">{timeframe} 평균가</div>
                    <div class="metric-value-gray">{analysis['avg_price']:,}원</div>
                </div>
            """, unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">{timeframe} 최저가</div>
                    <div class="metric-value-green">{analysis['min_price']:,}원</div>
                </div>
            """, unsafe_allow_html=True)
        with m4:
            score = analysis['discount_score']
            badge_class = "metric-score-high" if score >= 70 else ("metric-score-mid" if score >= 40 else "metric-score-low")
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">진짜 할인 점수</div>
                    <div class="{badge_class}">{score}점 / 100점</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 구매 권장 배지 & 판정 메시지
        st.info(f"### 판정 결과: {analysis['badge']}\n\n**AI 추천 가이드**: {analysis['recommendation']}")

        # 기간 필터가 적용된 DataFrame 구하기
        if selected_days is not None and 'collected_at' in df_hist.columns:
            cutoff = pd.to_datetime(df_hist['collected_at'].max()) - pd.Timedelta(days=selected_days)
            df_plot = df_hist[df_hist['collected_at'] >= cutoff]
        else:
            df_plot = df_hist

        # Plotly 인터랙티브 라인 차트
        fig = go.Figure()

        # 가격 추이 선
        fig.add_trace(go.Scatter(
            x=df_plot['collected_at'],
            y=df_plot['price'],
            mode='lines+markers',
            name='판매가',
            line=dict(color='#2563EB', width=3),
            marker=dict(size=5)
        ))

        # 기간 평균가 점선
        fig.add_trace(go.Scatter(
            x=df_plot['collected_at'],
            y=[analysis['avg_price']] * len(df_plot),
            mode='lines',
            name=f'{timeframe} 평균가',
            line=dict(color='#EF4444', width=2, dash='dash')
        ))

        fig.update_layout(
            title=f"최근 {timeframe} 가격 변동 추이",
            xaxis_title="수집 일자",
            yaxis_title="가격 (원)",
            hovermode="x unified",
            height=420
        )

        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("DB에 수집 및 저장된 상품 목록")
    df_products = get_all_products()
    if not df_products.empty:
        st.dataframe(df_products, use_container_width=True)
    else:
        st.info("아직 DB에 저장된 상품이 없습니다. [상품 검색] 탭에서 분석을 진행해 보세요.")

with tab3:
    st.subheader("다중 상품 가격 변동 비교")
    df_products = get_all_products()
    if df_products.empty:
        st.info("비교할 상품이 없습니다. [상품 검색] 탭에서 원하는 상품들의 가격 추세 분석을 클릭하여 DB에 추가해 주세요.")
    else:
        product_options = {row['title']: row['product_id'] for _, row in df_products.iterrows()}
        selected_titles = st.multiselect("비교할 상품을 2개 이상 선택하세요", options=list(product_options.keys()), default=list(product_options.keys())[:2])
        
        if selected_titles:
            fig_compare = go.Figure()
            for title in selected_titles:
                pid = product_options[title]
                df_p = get_price_history(pid)
                if not df_p.empty:
                    fig_compare.add_trace(go.Scatter(
                        x=df_p['collected_at'],
                        y=df_p['price'],
                        mode='lines',
                        name=title[:20]
                    ))
            fig_compare.update_layout(
                title="선택된 상품 간 시계열 가격 변동 비교",
                xaxis_title="일자",
                yaxis_title="가격 (원)",
                hovermode="x unified",
                height=450
            )
            st.plotly_chart(fig_compare, use_container_width=True)
