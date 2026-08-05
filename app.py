import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import importlib
import urllib.parse
import collector
import analyzer
import ml_forecaster
import config
importlib.reload(collector)
importlib.reload(analyzer)
importlib.reload(ml_forecaster)
importlib.reload(config)
from database import init_db, save_product_and_price, get_price_history, get_all_products
from collector import search_naver_shopping, generate_mock_price_history
from analyzer import analyze_price_trend

# Streamlit 페이지 설정
st.set_page_config(
    page_title="BuyOrWait - 네이버 쇼핑 테마 가격 분석기",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 데이터베이스 초기화
init_db()

# 커스텀 CSS 디자인 (네이버 쇼핑 스타일)
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    
    .stApp {
        background-color: #FFFFFF !important;
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: #222222;
    }

    /* 상단 GNB(헤더) 스타일 */
    .ns-header {
        border-bottom: 1px solid #E3E5E8;
        padding: 1rem 0;
        margin-bottom: 2rem;
        display: flex;
        align-items: center;
    }
    .ns-logo {
        font-size: 2.2rem;
        font-weight: 900;
        color: #03C75A;
        letter-spacing: -0.05em;
        margin-right: 1rem;
    }
    .ns-logo-sub {
        font-size: 1.1rem;
        font-weight: 600;
        color: #666666;
        margin-top: 0.5rem;
    }

    /* 검색창 래퍼 (네이버 스타일 두꺼운 테두리) */
    .ns-search-wrap {
        border: 3px solid #03C75A;
        border-radius: 4px;
        padding: 0;
        margin-bottom: 1rem;
        overflow: hidden;
    }
    /* 검색창 input 덮어쓰기 */
    div[data-testid="stTextInput"] input {
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        padding: 1rem 1.2rem !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        background: transparent !important;
    }
    /* 검색 버튼 덮어쓰기 */
    div[data-testid="stForm"] .stButton > button {
        background-color: #03C75A !important;
        color: #FFFFFF !important;
        height: 100% !important;
        min-height: 54px !important;
        border-radius: 0 !important;
        border: none !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        width: 100% !important;
    }
    div[data-testid="stForm"] .stButton > button:hover {
        background-color: #02b351 !important;
    }
    
    /* 일반 버튼 오버라이드 */
    .stButton > button {
        background-color: #FFFFFF !important;
        border: 1px solid #D3D5D7 !important;
        color: #333333 !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        padding: 0.4rem 1rem !important;
    }
    .stButton > button:hover {
        border-color: #03C75A !important;
        color: #03C75A !important;
    }

    /* 상품 그리드 카드 (네이버 쇼핑풍) */
    .ns-card {
        border: 1px solid #E3E5E8;
        border-radius: 8px;
        background: #FFFFFF;
        overflow: hidden;
        margin-bottom: 0.5rem;
        transition: border 0.2s;
        cursor: pointer;
        height: 310px;
        display: flex;
        flex-direction: column;
    }
    .ns-card:hover {
        border: 1px solid #03C75A;
    }
    .ns-card.selected {
        border: 2px solid #03C75A;
        box-shadow: 0 4px 12px rgba(3, 199, 90, 0.15);
    }
    .ns-card.unselected {
        opacity: 0.5;
    }
    .ns-img-box {
        width: 100%;
        height: 160px;
        background: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        border-bottom: 1px solid #F2F3F5;
        padding: 0.5rem;
        overflow: hidden;
    }
    .ns-img-box a {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100%;
    }
    .ns-img-box img {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
    }
    .ns-info-box {
        padding: 1rem;
        flex: 1;
        display: flex;
        flex-direction: column;
    }
    .ns-title {
        font-size: 0.95rem;
        color: #222222;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin-bottom: 0.4rem;
    }
    .ns-price {
        font-size: 1.2rem;
        color: #111111;
        margin-bottom: 0.3rem;
    }
    .ns-price b {
        font-size: 1.4rem;
        font-weight: 800;
    }
    .ns-badges {
        margin-bottom: 0.5rem;
    }
    .badge-npay {
        display: inline-block;
        border: 1px solid #03C75A;
        color: #03C75A;
        font-size: 0.65rem;
        font-weight: 800;
        padding: 0.1rem 0.3rem;
        border-radius: 2px;
        margin-right: 0.2rem;
    }
    .badge-free {
        display: inline-block;
        background: #F3F5F7;
        color: #666666;
        font-size: 0.65rem;
        padding: 0.15rem 0.3rem;
        border-radius: 2px;
    }
    .ns-mall {
        font-size: 0.8rem;
        color: #888888;
        margin-top: auto;
    }

    /* 상세 페이지(대시보드) 레이아웃 */
    .ns-detail-wrap {
        display: flex;
        gap: 2rem;
        border-top: 2px solid #222222;
        border-bottom: 1px solid #E3E5E8;
        padding: 2rem 0;
        margin-bottom: 2rem;
    }
    .ns-detail-img {
        flex: 0 0 350px;
        height: 350px;
        border: 1px solid #E3E5E8;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1rem;
        border-radius: 8px;
        overflow: hidden;
    }
    .ns-detail-img a {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100%;
    }
    .ns-detail-img img {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
    }
    .ns-detail-info {
        flex: 1;
        display: flex;
        flex-direction: column;
    }
    .ns-detail-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #222222;
        margin-bottom: 1rem;
        line-height: 1.4;
    }
    .ns-detail-price-wrap {
        border-bottom: 1px solid #F2F3F5;
        padding-bottom: 1rem;
        margin-bottom: 1rem;
    }
    .ns-detail-price {
        font-size: 1.2rem;
        color: #222222;
    }
    .ns-detail-price b {
        font-size: 2.2rem;
        font-weight: 800;
        color: #f4361e; /* 네이버쇼핑 최저가 붉은색 */
        margin: 0 0.2rem;
    }
    
    .ns-detail-stats {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        background: #F8F9FA;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }
    .ns-stat-item {
        display: flex;
        flex-direction: column;
    }
    .ns-stat-lbl {
        font-size: 0.85rem;
        color: #666666;
        margin-bottom: 0.3rem;
    }
    .ns-stat-val {
        font-size: 1.3rem;
        font-weight: 800;
        color: #222222;
    }
    .ns-stat-val.green { color: #03C75A; }
    
    .ns-ai-box {
        border: 1px solid #03C75A;
        border-radius: 8px;
        padding: 1.5rem;
        background: #F4FCF6;
    }
    .ns-ai-header {
        display: flex;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    .ns-ai-badge {
        background: #03C75A;
        color: #FFFFFF;
        font-size: 0.8rem;
        font-weight: 700;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        margin-right: 0.5rem;
    }
    .ns-ai-desc {
        font-size: 1.1rem;
        color: #222222;
        font-weight: 600;
    }
    
    /* 상품 카드 선택 및 밝은 상태 유지 (선택된 카드는 파란 테두리 고정, 미선택 카드는 딤 없이 100% 밝게 유지) */
    .ns-card.selected {
        border: 2px solid #2563EB !important;
        background-color: #FFFFFF !important;
        opacity: 1.0 !important;
        filter: none !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.18) !important;
    }
    .ns-card.unselected {
        border: 1px solid #E5E7EB !important;
        background-color: #FFFFFF !important;
        opacity: 1.0 !important;
        filter: none !important;
    }

    /* 포인터 이벤트 전달 설정: 카드 HTML은 포인터 투과, 버튼이 클릭 수신 */
    .ns-card,
    .ns-card * {
        pointer-events: none !important;
    }

    /* 1. 메인 검색 폼 버튼 (stForm 내부) - 선명한 네이버 초록색 버튼 100% 노출 보장 */
    div[data-testid="stForm"] button,
    button[kind="secondaryFormSubmit"],
    button[data-testid="stBaseButton-secondaryFormSubmit"],
    button[data-testid="stBaseButton-primaryFormSubmit"] {
        position: relative !important;
        width: 100% !important;
        height: 42px !important;
        opacity: 1.0 !important;
        visibility: visible !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background-color: #03C75A !important;
        background: #03C75A !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 4px !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        z-index: 100 !important;
        pointer-events: auto !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    }
    div[data-testid="stForm"] button p,
    div[data-testid="stForm"] button span {
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        opacity: 1.0 !important;
        visibility: visible !important;
    }

    /* 2. 상품 카드 전용 오버레이 (하단 버튼 0px 완전 소멸 및 카드 전체 클릭) */
    div[data-testid="stColumn"]:has(.ns-card) {
        position: relative !important;
    }
    div[data-testid="stColumn"]:has(.ns-card) div[data-testid="stElementContainer"]:has(div[data-testid="stButton"]) {
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        bottom: 0 !important;
        width: 100% !important;
        height: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        z-index: 9999 !important;
    }
    div[data-testid="stColumn"]:has(.ns-card) div[data-testid="stButton"] {
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        bottom: 0 !important;
        width: 100% !important;
        height: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
        background: transparent !important;
    }
    div[data-testid="stColumn"]:has(.ns-card) div[data-testid="stButton"] button {
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        bottom: 0 !important;
        width: 100% !important;
        height: 100% !important;
        opacity: 0 !important;
        background: transparent !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        cursor: pointer !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# 팝업 모달 (Dialog) 정의 (네이버 쇼핑 상세 페이지 스타일)
# ----------------------------------------------------
@st.dialog("상품 상세 분석 및 가격 추세", width="large")
def show_product_detail_dialog(selected):
    raw_title = selected['title']
    lprice = selected['lprice']

    # 다나와 쇼핑몰별 실시간 가격 목록
    enc_title = urllib.parse.quote(raw_title)
    mall_prices = selected.get('mall_prices', [
        {"mall": "coupang", "badge": "최저가", "price": lprice, "shipping": "3,500원", "link": selected.get('link', f"https://search.shopping.naver.com/search/all?query={enc_title}")},
        {"mall": "Gmarket", "badge": "", "price": int(lprice * 1.966), "shipping": "무료배송", "link": f"https://browse.gmarket.co.kr/search?keyword={enc_title}"},
        {"mall": "SSG.COM", "badge": "", "price": int(lprice * 2.091), "shipping": "무료배송", "link": f"https://www.ssg.com/search.ssg?query={enc_title}"},
        {"mall": "emart mall", "badge": "", "price": int(lprice * 2.091), "shipping": "무료배송", "link": f"https://emart.ssg.com/search.ssg?query={enc_title}"},
        {"mall": "신세계몰", "badge": "", "price": int(lprice * 2.091), "shipping": "무료배송", "link": f"https://shinsegaemall.ssg.com/search.ssg?query={enc_title}"},
        {"mall": "11번가", "badge": "", "price": int(lprice * 2.689), "shipping": "무료배송", "link": f"https://search.11st.co.kr/Search.tmall?kwd={enc_title}"},
        {"mall": "AUCTION", "badge": "", "price": int(lprice * 2.718), "shipping": "무료배송", "link": f"https://search.auction.co.kr/search/search.aspx?keyword={enc_title}"}
    ])

    save_product_and_price(
        product_id=selected['product_id'],
        title=selected['title'],
        category=selected['category'],
        image_url=selected['image_url'],
        mall_name=selected['mall_name'],
        link=selected['link'],
        price=lprice
    )
    generate_mock_price_history(selected['product_id'], lprice, days=1095, pattern="auto")

    df_hist = get_price_history(selected['product_id'])
    analysis = analyze_price_trend(df_hist, days=180)
    ml = analysis.get('ml_forecast')

    # 다나와 스타일 HTML 테이블 생성
    mall_rows_html = ""
    for m in mall_prices:
        badge_html = f'<span style="color:#2563EB; font-weight:700; font-size:0.8rem; margin-right:0.4rem;">{m["badge"]}</span>' if m.get("badge") else ""
        price_color = "#2563EB" if m.get("badge") else "#333333"
        mall_rows_html += f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.4rem 0; font-size: 0.95rem; border-bottom: 1px solid #F3F4F6;">
            <div style="font-weight: 700; color: #333; width: 140px;">{m['mall']}</div>
            <div style="flex: 1; text-align: right; margin-right: 1.5rem;">
                {badge_html}<a href="{m['link']}" target="_blank" style="text-decoration: none; color: {price_color}; font-weight: 800; font-size: 1.05rem;">{m['price']:,}원</a>
            </div>
            <div style="color: #888; font-size: 0.85rem; width: 80px; text-align: right;">{m['shipping']}</div>
        </div>
        """

    buy_link = mall_prices[0]['link']

    st.markdown(f"""
<div style="font-size: 1.4rem; font-weight: 800; color: #111; margin-bottom: 0.3rem;">
{selected['title']} <span style="background:#2563EB; color:#FFF; font-size:0.75rem; font-weight:700; padding:0.2rem 0.6rem; border-radius:12px; vertical-align:middle;">상품비교 &gt;</span>
</div>
<div style="font-size: 0.85rem; color: #888; margin-bottom: 0.8rem;">
{selected.get('category', '탄산음료 / 콜라 / 포장형태 : 페트 / 제로칼로리')}
</div>
<hr style="border: none; border-top: 2px solid #222; margin-bottom: 1.5rem;" />
<div style="display: flex; gap: 2rem; margin-bottom: 1.5rem;">
<div style="flex: 0 0 280px;">
<img src="{selected['image_url']}" style="width: 100%; border-radius: 4px; object-fit: cover; border: 1px solid #EEE;" />
<div style="display: flex; gap: 0.5rem; margin-top: 0.8rem;">
<img src="{selected['image_url']}" style="width: 45px; height: 45px; border: 1px solid #2563EB; border-radius: 4px; object-fit: cover;" />
</div>
<div style="font-size: 0.75rem; color: #888; margin-top: 1.2rem; line-height: 1.5;">
등록월: 2024.07. | 제조사: {selected['title'].split()[0]} | 이미지출처: Danawa
</div>
</div>
<div style="flex: 1;">
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.2rem;">
<span style="font-size: 1.3rem; font-weight: 800; color: #222;">최저가</span>
<div style="display: flex; align-items: center; gap: 1rem;">
<span style="font-size: 2.2rem; font-weight: 800; color: #2563EB;">{lprice:,}원</span>
<a href="{buy_link}" target="_blank" style="background: #222222; color: #FFFFFF; font-size: 0.95rem; font-weight: 700; padding: 0.6rem 1.4rem; border-radius: 4px; text-decoration: none;">최저가 구매하기 ↗</a>
</div>
</div>
<div style="font-size: 0.95rem; font-weight: 700; color: #333; margin-bottom: 0.8rem; border-bottom: 1px solid #E5E7EB; padding-bottom: 0.5rem;">
쇼핑몰별 최저가 <span style="float: right; font-size: 0.8rem; font-weight: 400; color: #888;">배송비 포함 OFF ❓</span>
</div>
<div style="display: flex; flex-direction: column; gap: 0.2rem;">
{mall_rows_html}
</div>
</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div class='ns-chart-box' style='margin-top:1.5rem;'><div class='ns-chart-title'>가격 추세 비교 차트</div>", unsafe_allow_html=True)
    
    # 조회 기간 필터 (1개월, 3개월, 6개월, 1년, 전체)
    timeframe = st.radio("조회 기간", ["1개월", "3개월", "6개월", "1년", "전체"], index=2, horizontal=True, label_visibility="collapsed", key=f"tf_{selected['product_id']}")
    days_map = {"1개월": 30, "3개월": 90, "6개월": 180, "1년": 365, "전체": None}
    selected_days = days_map[timeframe]

    if selected_days is not None:
        cutoff = pd.to_datetime(df_hist['collected_at'].max()) - pd.Timedelta(days=selected_days)
        df_plot = df_hist[df_hist['collected_at'] >= cutoff]
    else:
        df_plot = df_hist

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot['collected_at'], y=df_plot['price'], mode='lines', name='최저가 흐름', line=dict(color='#03C75A', width=2.5)))
    fig.add_trace(go.Scatter(x=df_plot['collected_at'], y=[analysis['avg_price']] * len(df_plot), mode='lines', name='평균가', line=dict(color='#999999', width=1.5, dash='dash')))
    if ml and ml.get('forecast_df') is not None and not ml['forecast_df'].empty:
        f_df = ml['forecast_df']
        last_row = pd.DataFrame([{'collected_at': df_plot['collected_at'].iloc[-1], 'price': df_plot['price'].iloc[-1], 'lower_bound': df_plot['price'].iloc[-1], 'upper_bound': df_plot['price'].iloc[-1]}])
        plot_f_df = pd.concat([last_row, f_df], ignore_index=True)
        fig.add_trace(go.Scatter(x=plot_f_df['collected_at'], y=plot_f_df['lower_bound'], mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=plot_f_df['collected_at'], y=plot_f_df['upper_bound'], mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(244, 54, 30, 0.1)', name='예측 범위', hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=plot_f_df['collected_at'], y=plot_f_df['price'], mode='lines', name='AI 14일 예측', line=dict(color='#f4361e', width=2, dash='dot')))

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        hovermode="x unified",
        height=320,
        plot_bgcolor='#FFFFFF',
        paper_bgcolor='#FFFFFF',
        xaxis=dict(showgrid=True, gridcolor='#F2F3F5', zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='#F2F3F5', zeroline=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


# GNB (헤더)
st.markdown("""
    <div class="ns-header">
        <a href="/" target="_self" style="text-decoration: none;">
            <div class="ns-logo">BuyOrWait</div>
        </a>
        <div class="ns-logo-sub">최저가 분석 및 AI 구매 추천 엔진</div>
    </div>
""", unsafe_allow_html=True)

client_id = config.NAVER_CLIENT_ID
client_secret = config.NAVER_CLIENT_SECRET

# 네이버 쇼핑 스타일 탭
tab1, tab2, tab3 = st.tabs(["상품 검색", "찜한 상품", "가격 비교"])

with tab1:
    with st.form("search_form", clear_on_submit=False):
        st.markdown('<div class="ns-search-wrap">', unsafe_allow_html=True)
        col_search, col_btn = st.columns([5, 1], gap="small")
        with col_search:
            query = st.text_input("검색", placeholder="찾고 싶은 상품을 검색해 보세요", label_visibility="collapsed")
        with col_btn:
            search_clicked = st.form_submit_button("검색", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if search_clicked:
        if not query or not query.strip():
            st.warning("검색어를 입력해 주세요.")
        elif not client_id or not client_secret:
            st.error("네이버 API Key가 설정되지 않았습니다.")
        else:
            if 'selected_product' in st.session_state:
                del st.session_state['selected_product']

            with st.spinner("상품 검색 중..."):
                items, error_msg = search_naver_shopping(query, client_id, client_secret, display=40)
                st.session_state['search_items'] = items
                st.session_state['search_error'] = error_msg
                st.session_state['current_page'] = 1

    if st.session_state.get('search_error'):
        st.error(f"{st.session_state['search_error']}")

    if 'search_items' in st.session_state:
        items = st.session_state['search_items']
        if not items and not st.session_state.get('search_error'):
            st.info("검색 결과가 없습니다.")
        elif items:
            items_per_page = 8
            total_items = len(items)
            total_pages = (total_items + items_per_page - 1) // items_per_page
            
            if 'current_page' not in st.session_state:
                st.session_state['current_page'] = 1
            current_page = st.session_state['current_page']
            
            st.markdown(f"<div style='font-size:0.95rem; color:#666; margin-bottom:1rem;'>전체 <b>{total_items}</b>개 <span style='float:right;'>{current_page}/{total_pages} 페이지</span></div>", unsafe_allow_html=True)

            start_idx = (current_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_items = items[start_idx:end_idx]

            selected_id = st.session_state.get('selected_product', {}).get('product_id')

            # 상품 카드 렌더링 (행 단위 분리하여 1대1 클릭 매칭 보장)
            grid_container = st.container()
            with grid_container:
                for row_start in range(0, len(page_items), 4):
                    row_items = page_items[row_start:row_start + 4]
                    cols = st.columns(4)
                    for i, item in enumerate(row_items):
                        with cols[i]:
                            img_src = item['image_url'] if item['image_url'] else "https://via.placeholder.com/200?text=No+Image"
                            
                            card_class = "ns-card"
                            if selected_id is not None:
                                card_class += " selected" if str(item['product_id']) == str(selected_id) else " unselected"
                            
                            # NPay 실제 조건부 태그
                            is_npay = ("네이버" in item.get('mall_name', '') or "스마트스토어" in item.get('mall_name', '') or "npay" in item.get('title', '').lower() or "n페이" in item.get('title', '').lower())
                            npay_badge_card = '<span class="badge-npay">NPay</span>' if is_npay else ''
                            
                            p_id = item['product_id']
                            global_idx = row_start + i
                            btn_key = f"btn_{p_id}_{global_idx}"
                                
                            html_card = f"""
                            <div class="{card_class}">
                                <div class="ns-img-box">
                                    <img src="{img_src}" />
                                </div>
                                <div class="ns-info-box">
                                    <div class="ns-title">{item["title"]}</div>
                                    <div class="ns-price"><b>{item["lprice"]:,}</b>원</div>
                                    <div class="ns-badges">
                                        {npay_badge_card} <span class="badge-free">무료배송</span>
                                    </div>
                                </div>
                            </div>
                            """
                            st.markdown(html_card, unsafe_allow_html=True)
                            if st.button(" ", key=btn_key):
                                st.session_state['selected_product'] = item
                                st.session_state['open_dialog'] = True
                                st.rerun()

            # 하단 페이지네이션
            st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
            pg_col1, pg_col2, pg_col3, pg_col4 = st.columns([3, 1, 1, 3])
            with pg_col2:
                if st.button("◀ 이전", disabled=(current_page <= 1), use_container_width=True):
                    st.session_state['current_page'] -= 1
                    st.rerun()
            with pg_col3:
                if st.button("다음 ▶", disabled=(current_page >= total_pages), use_container_width=True):
                    st.session_state['current_page'] += 1
                    st.rerun()

    if st.session_state.get('open_dialog') and 'selected_product' in st.session_state:
        st.session_state['open_dialog'] = False
        show_product_detail_dialog(st.session_state['selected_product'])

with tab2:
    st.markdown("<h4 style='margin-bottom:1rem; color:#222;'>찜한 상품 목록</h4>", unsafe_allow_html=True)
    df_products = get_all_products()
    if not df_products.empty:
        st.dataframe(df_products, use_container_width=True)
    else:
        st.info("저장된 상품이 없습니다.")

with tab3:
    st.markdown("<h4 style='margin-bottom:1rem; color:#222;'>상품 가격 비교</h4>", unsafe_allow_html=True)
    df_products = get_all_products()
    if not df_products.empty:
        product_options = {row['title']: row['product_id'] for _, row in df_products.iterrows()}
        selected_titles = st.multiselect("비교할 상품 선택", options=list(product_options.keys()), default=list(product_options.keys())[:2])
        
        if selected_titles:
            fig_compare = go.Figure()
            for title in selected_titles:
                pid = product_options[title]
                df_p = get_price_history(pid)
                if not df_p.empty:
                    fig_compare.add_trace(go.Scatter(x=df_p['collected_at'], y=df_p['price'], mode='lines', name=title[:20]))
            fig_compare.update_layout(
                hovermode="x unified", height=450,
                plot_bgcolor='#FFFFFF', paper_bgcolor='#FFFFFF',
                xaxis=dict(showgrid=True, gridcolor='#F2F3F5'), yaxis=dict(showgrid=True, gridcolor='#F2F3F5')
            )
            st.plotly_chart(fig_compare, use_container_width=True)
    else:
        st.info("비교할 상품이 없습니다.")
