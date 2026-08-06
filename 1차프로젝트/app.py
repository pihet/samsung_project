# BuyOrWait Main Streamlit Application - 다나와(Danawa) 메인 스타일 & 파서 적용
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
    page_title="BuyOrWait - 다나와 실시간 최저가 & AI 가격 분석기",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 데이터베이스 초기화
init_db()

# 커스텀 CSS 디자인 (다나와 Danawa 메인 브랜드 디자인 시스템)
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    
    .stApp {
        background-color: #F4F6F9 !important;
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: #1E293B;
    }

    /* 상단 GNB(다나와 헤더) 스타일 */
    .dnw-header {
        background: #FFFFFF;
        border-bottom: 2px solid #115DCE;
        padding: 1.2rem 2rem;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border-radius: 0 0 8px 8px;
    }
    .dnw-logo-wrap {
        display: flex;
        align-items: baseline;
        gap: 0.8rem;
    }
    .dnw-logo {
        font-size: 2.2rem;
        font-weight: 900;
        color: #115DCE;
        letter-spacing: -0.05em;
    }
    .dnw-logo-dot {
        color: #E52528;
        display: inline-block;
    }
    .dnw-logo-sub {
        font-size: 1rem;
        font-weight: 600;
        color: #64748B;
    }

    /* 다나와 퀵 검색 키워드 칩 */
    .dnw-chips-wrap {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        margin-bottom: 0.8rem;
        flex-wrap: wrap;
    }
    .dnw-chip-label {
        font-size: 0.85rem;
        font-weight: 700;
        color: #475569;
        margin-right: 0.2rem;
    }
    .dnw-chip-btn {
        display: inline-block;
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 4px;
        color: #115DCE;
        font-size: 0.82rem;
        font-weight: 700;
        padding: 0.25rem 0.6rem;
        text-decoration: none;
        transition: all 0.15s ease;
    }
    .dnw-chip-btn:hover {
        background: #F1F5F9;
        border-color: #115DCE;
        color: #115DCE;
    }

    /* 검색창 래퍼 (다나와 시그니처 테두리) */
    .dnw-search-wrap {
        background: #FFFFFF;
        border: 3px solid #115DCE;
        border-radius: 6px;
        padding: 0;
        margin-bottom: 1rem;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(17, 93, 206, 0.12);
    }
    /* 검색 결과 헤더 및 정렬 라디오 수직 중앙 정렬 */
    div[data-testid="stHorizontalBlock"]:has(input[aria-label="정렬 기준"]) {
        align-items: center !important;
    }
    div[data-testid="stRadio"]:has(input[aria-label="정렬 기준"]) {
        margin: 0 !important;
        padding: 0 !important;
    }
    div[data-testid="stRadio"]:has(input[aria-label="정렬 기준"]) div[role="radiogroup"] {
        justify-content: flex-start !important;
        align-items: center !important;
        gap: 0.8rem !important;
        margin-left: 0 !important;
    }
    div[data-testid="stRadio"]:has(input[aria-label="정렬 기준"]) label {
        align-items: center !important;
        margin: 0 !important;
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
        color: #0F172A !important;
    }
    /* 검색 버튼 덮어쓰기 */
    div[data-testid="stForm"] .stButton > button {
        background-color: #115DCE !important;
        color: #FFFFFF !important;
        height: 100% !important;
        min-height: 54px !important;
        border-radius: 0 !important;
        border: none !important;
        font-size: 1.1rem !important;
        font-weight: 800 !important;
        width: 100% !important;
        transition: background-color 0.2s;
    }
    div[data-testid="stForm"] .stButton > button:hover {
        background-color: #0D4AA5 !important;
    }
    
    /* 일반 버튼 오버라이드 */
    .stButton > button {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        color: #334155 !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        padding: 0.4rem 1rem !important;
    }
    .stButton > button:hover {
        border-color: #115DCE !important;
        color: #115DCE !important;
    }

    /* 다나와 상품 카드 (AGENTS.md 규칙 준수) */
    .dnw-card {
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        background: #FFFFFF;
        overflow: hidden;
        margin-bottom: 0.8rem;
        transition: all 0.2s ease-in-out;
        cursor: pointer;
        min-height: 380px;
        display: flex;
        flex-direction: column;
        position: relative;
    }
    .dnw-card:hover {
        border: 1px solid #115DCE;
        box-shadow: 0 4px 16px rgba(17, 93, 206, 0.12);
    }
    
    /* AGENTS.md 선택 / 딤 상태 규칙 */
    .dnw-card.selected {
        border: 3px solid #2563EB !important;
        background-color: #FFFFFF !important;
        opacity: 1.0 !important;
        filter: none !important;
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.25) !important;
    }
    .dnw-card.unselected {
        background-color: #0F172A !important;
        opacity: 0.35 !important;
        filter: brightness(0.35) !important;
        border: 1px solid #1E293B !important;
    }

    .dnw-img-box {
        width: 100%;
        height: 180px;
        background: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        border-bottom: 1px solid #F1F5F9;
        padding: 0.8rem;
        overflow: hidden;
    }
    .dnw-img-box img {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
    }
    .dnw-info-box {
        padding: 1rem;
        flex: 1;
        display: flex;
        flex-direction: column;
    }
    .dnw-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.45;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin-bottom: 0.5rem;
        height: 2.8rem;
    }
    .dnw-specs-wrap {
        display: flex;
        flex-wrap: wrap;
        gap: 0.3rem;
        margin-bottom: 0.8rem;
        max-height: 2.4rem;
        overflow: hidden;
    }
    .dnw-spec-tag {
        background: #F1F5F9;
        color: #475569;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 0.15rem 0.4rem;
        border-radius: 4px;
    }
    .dnw-price-box {
        margin-top: auto;
        padding-top: 0.6rem;
        border-top: 1px dashed #E2E8F0;
        display: flex;
        align-items: baseline;
        justify-content: space-between;
    }
    .dnw-badge-min {
        background: #E52528;
        color: #FFFFFF;
        font-size: 0.7rem;
        font-weight: 800;
        padding: 0.15rem 0.4rem;
        border-radius: 3px;
    }
    .dnw-price-val {
        font-size: 1.3rem;
        font-weight: 800;
        color: #115DCE;
    }
    .dnw-price-val b {
        font-size: 1.45rem;
    }
    .dnw-mall-name {
        font-size: 0.78rem;
        color: #64748B;
        margin-top: 0.3rem;
    }

    /* 포인터 이벤트 전달 설정: 카드 HTML은 포인터 투과, 버튼이 클릭 수신 */
    .dnw-card,
    .dnw-card * {
        pointer-events: none !important;
    }

    /* 1. 메인 검색 폼 버튼 (stForm 내부) */
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
        background-color: #115DCE !important;
        background: #115DCE !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 4px !important;
        font-size: 1rem !important;
        font-weight: 800 !important;
        z-index: 100 !important;
        pointer-events: auto !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    }
    div[data-testid="stForm"] button p,
    div[data-testid="stForm"] button span {
        color: #FFFFFF !important;
        font-weight: 800 !important;
        font-size: 1rem !important;
        opacity: 1.0 !important;
        visibility: visible !important;
    }

    /* 2. 상품 카드 전용 오버레이 (버튼을 카드 전체 투명 버튼으로 오버레이) */
    div[data-testid="stColumn"]:has(.dnw-card) {
        position: relative !important;
    }
    div[data-testid="stColumn"]:has(.dnw-card) div[data-testid="stElementContainer"]:has(div[data-testid="stButton"]) {
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
    div[data-testid="stColumn"]:has(.dnw-card) div[data-testid="stButton"] {
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
    div[data-testid="stColumn"]:has(.dnw-card) div[data-testid="stButton"] button {
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
    /* 인기 검색어 칩 버튼 간격 콤팩트 설정 */
    div[data-testid="stHorizontalBlock"]:has(button[key^="chip_"]) {
        gap: 0.4rem !important;
        justify-content: flex-start !important;
    }
    div[data-testid="stHorizontalBlock"]:has(button[key^="chip_"]) > div[data-testid="column"] {
        flex: 0 0 auto !important;
        min-width: unset !important;
        width: auto !important;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# 팝업 모달 (Dialog) 정의
# ----------------------------------------------------
@st.dialog("상품 상세 및 분석", width="large")
def show_product_detail_dialog(selected):
    raw_title = selected['title']
    lprice = selected['lprice']
    pcode = selected.get('pcode', '')
    danawa_url = selected.get('link', f"https://prod.danawa.com/info/?pcode={pcode}" if pcode else "https://www.danawa.com")

    # 다나와 실시간 규격/옵션 및 최저가 목록
    mall_prices = selected.get('mall_prices', [
        {"mall": "다나와 실시간 최저가", "badge": "최저가", "price": lprice, "shipping": "무료배송", "link": danawa_url}
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

    # 다나와 쇼핑몰별 가격비교 테이블 HTML 생성 (들여쓰기 제거로 Markdown 코드블록 이스케이프 방지)
    mall_rows_html = ""
    for m in mall_prices:
        badge_html = f'<span style="background:#E52528; color:#FFF; font-weight:800; font-size:0.75rem; padding:0.15rem 0.4rem; border-radius:2px; margin-right:0.4rem;">{m["badge"]}</span>' if m.get("badge") else ""
        price_color = "#115DCE" if m.get("badge") else "#0F172A"
        mall_rows_html += f'<div style="display: flex; justify-content: space-between; align-items: center; padding: 0.6rem 0.4rem; font-size: 0.95rem; border-bottom: 1px solid #E2E8F0;"><div style="font-weight: 700; color: #334155; width: 140px;">{m["mall"]}</div><div style="flex: 1; text-align: right; margin-right: 1.5rem;">{badge_html}<a href="{m["link"]}" target="_blank" style="text-decoration: none; color: {price_color}; font-weight: 800; font-size: 1.1rem;">{m["price"]:,}원</a></div><div style="color: #64748B; font-size: 0.85rem; width: 80px; text-align: right;">{m["shipping"]}</div></div>'

    spec_tags_html = "".join([f'<span style="background:#F1F5F9; color:#334155; font-size:0.8rem; font-weight:600; padding:0.2rem 0.6rem; border-radius:4px; margin-right:0.3rem; margin-bottom:0.3rem; display:inline-block;">{tag}</span>' for tag in selected.get('spec_tags', [])])

    st.markdown(f"""
<div style="font-size: 1.4rem; font-weight: 800; color: #0F172A; margin-bottom: 0.3rem;">
{selected['title']} 
</div>
<div style="margin-bottom: 0.8rem;">
{spec_tags_html}
</div>
<hr style="border: none; border-top: 2px solid #115DCE; margin-bottom: 1.5rem;" />
<div style="display: flex; gap: 2rem; margin-bottom: 1.5rem; flex-wrap: wrap;">
<div style="flex: 0 0 280px; background:#FFF; padding:1rem; border-radius:8px; border:1px solid #E2E8F0; display:flex; align-items:center; justify-content:center;">
<img src="{selected['image_url']}" style="width: 100%; max-height:240px; border-radius: 4px; object-fit: contain;" />
</div>
<div style="flex: 1; min-width: 300px;">
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.2rem; background:#F8FAFC; padding:1rem; border-radius:8px; border:1px solid #E2E8F0;">
<div>
<span style="font-size: 0.9rem; font-weight: 700; color: #64748B; display:block;">실시간 최저가</span>
<span style="font-size: 2.2rem; font-weight: 900; color: #115DCE;">{lprice:,}원</span>
</div>
<a href="{danawa_url}" target="_blank" style="background: #115DCE; color: #FFFFFF; font-size: 1rem; font-weight: 800; padding: 0.8rem 1.6rem; border-radius: 6px; text-decoration: none; box-shadow: 0 4px 10px rgba(17, 93, 206, 0.25);">최저가 구매하러가기</a>
</div>
<div style="font-size: 1rem; font-weight: 800; color: #0F172A; margin-bottom: 0.6rem; border-bottom: 2px solid #E2E8F0; padding-bottom: 0.4rem;">
쇼핑몰별 실시간 최저가 비교
</div>
<div style="display: flex; flex-direction: column; gap: 0.2rem;">
{mall_rows_html}
</div>""", unsafe_allow_html=True)

    # AI 구매 추천 분석 카드
    st.markdown(f"""
<div style="background:#F0F7FF; border:1px solid #BAE6FD; border-radius:8px; padding:1.2rem; margin-bottom:1.5rem;">
<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.6rem;">
<div style="display:flex; align-items:center; gap:0.6rem;">
<span style="background:#115DCE; color:#FFF; font-weight:800; font-size:0.8rem; padding:0.2rem 0.6rem; border-radius:4px;">AI 추천 지수</span>
<span style="font-size:1.2rem; font-weight:800; color:#0F172A;">{analysis['badge']}</span>
</div>
<div style="font-size:1.5rem; font-weight:900; color:#115DCE;">{analysis['discount_score']}점 / 100점</div>
</div>
<div style="font-size:0.95rem; color:#334155; line-height:1.5;">
{analysis['recommendation']}
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='font-size:1.1rem; font-weight:800; color:#0F172A; margin-bottom:0.5rem;'>가격변동 및 AI예측 차트</div>", unsafe_allow_html=True)
    
    # 조회 기간 필터 (1개월, 3개월, 6개월, 1년, 전체 - 기본 3개월 index=1)
    timeframe = st.radio("조회 기간", ["1개월", "3개월", "6개월", "1년", "전체"], index=1, horizontal=True, label_visibility="collapsed", key=f"tf_{selected['product_id']}")
    days_map = {"1개월": 30, "3개월": 90, "6개월": 180, "1년": 365, "전체": None}
    selected_days = days_map[timeframe]

    if selected_days is not None:
        cutoff = pd.to_datetime(df_hist['collected_at'].max()) - pd.Timedelta(days=selected_days)
        df_plot = df_hist[df_hist['collected_at'] >= cutoff]
    else:
        df_plot = df_hist

    avg_p = analysis['avg_price']
    fig = go.Figure()

    x_vals = df_plot['collected_at'].tolist()
    y_vals = df_plot['price'].tolist()

    # 평균선(avg_p) 교차점 정밀 분할 알고리즘
    split_x = []
    split_y = []

    for i in range(len(x_vals) - 1):
        x1, y1 = x_vals[i], y_vals[i]
        x2, y2 = x_vals[i+1], y_vals[i+1]
        
        split_x.append(x1)
        split_y.append(y1)

        # 평균선(avg_p)을 경계로 상하 교차하는 경우 선형 보간 교차점 추가
        if (y1 < avg_p and y2 > avg_p) or (y1 > avg_p and y2 < avg_p):
            t1 = pd.to_datetime(x1).timestamp()
            t2 = pd.to_datetime(x2).timestamp()
            t_cross = t1 + (avg_p - y1) / (y2 - y1) * (t2 - t1)
            x_cross = pd.to_datetime(t_cross, unit='s')
            
            split_x.append(x_cross)
            split_y.append(avg_p)

    if x_vals:
        split_x.append(x_vals[-1])
        split_y.append(y_vals[-1])

    # 평균선 기준 상단(레드), 하단(블루) 정밀 색상 선 렌더링
    for i in range(len(split_x) - 1):
        x_seg = [split_x[i], split_x[i+1]]
        y_seg = [split_y[i], split_y[i+1]]
        mid_y = (split_y[i] + split_y[i+1]) / 2.0
        seg_color = '#EF4444' if mid_y > avg_p else '#115DCE'
        
        fig.add_trace(go.Scatter(
            x=x_seg, 
            y=y_seg, 
            mode='lines', 
            line=dict(color=seg_color, width=2.5),
            showlegend=False,
            hoverinfo='skip'
        ))

    # 최저가 흐름 통합 범례 및 데이터 포인트 마커
    fig.add_trace(go.Scatter(
        x=df_plot['collected_at'], 
        y=df_plot['price'], 
        mode='markers', 
        name='최저가 흐름',
        marker=dict(size=5, color=['#EF4444' if p > avg_p else '#115DCE' for p in df_plot['price']]),
        hovertemplate='%{x}<br>최저가: %{y:,.0f}원<extra></extra>'
    ))

    fig.add_trace(go.Scatter(x=df_plot['collected_at'], y=[avg_p] * len(df_plot), mode='lines', name='평균가', line=dict(color='#94A3B8', width=1.5, dash='dash')))
    if ml and ml.get('forecast_df') is not None and not ml['forecast_df'].empty:
        f_df = ml['forecast_df']
        last_row = pd.DataFrame([{'collected_at': df_plot['collected_at'].iloc[-1], 'price': df_plot['price'].iloc[-1], 'lower_bound': df_plot['price'].iloc[-1], 'upper_bound': df_plot['price'].iloc[-1]}])
        plot_f_df = pd.concat([last_row, f_df], ignore_index=True)
        fig.add_trace(go.Scatter(x=plot_f_df['collected_at'], y=plot_f_df['lower_bound'], mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=plot_f_df['collected_at'], y=plot_f_df['upper_bound'], mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(229, 37, 40, 0.1)', name='예측 범위', hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=plot_f_df['collected_at'], y=plot_f_df['price'], mode='lines', name='AI 14일 예측', line=dict(color='#E52528', width=2, dash='dot')))

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        hovermode="x unified",
        height=340,
        plot_bgcolor='#FFFFFF',
        paper_bgcolor='#FFFFFF',
        xaxis=dict(showgrid=True, gridcolor='#F1F5F9', zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='#F1F5F9', zeroline=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)


# GNB (BuyOrWait 헤더)
st.markdown("""
    <div class="dnw-header">
        <div class="dnw-logo-wrap">
            <a href="/" target="_self" style="text-decoration: none;">
                <div class="dnw-logo">BuyOrWait</div>
            </a>
            <div class="dnw-logo-sub">| 실시간 최저가 & AI 가격 분석기</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# 탭 Navigation
tab1, tab2, tab3 = st.tabs(["상품검색", "찜한 상품 목록", "가격 추세 비교"])

with tab1:
    # 쿼리 파라미터 처리 (인기 검색어 칩 클릭 시)
    qp_query = st.query_params.get("q", None)
    if qp_query:
        st.session_state['selected_quick_query'] = qp_query
        st.query_params.clear()

    selected_quick_query = st.session_state.pop('selected_quick_query', None)

    # 퀵 검색 추천 태그 칩 (스페이스바 1칸 간격 밀착)
    quick_queries = ["노트북", "갤럭시 S24", "아이폰 15", "OLED TV", "제로콜라", "스마트워치"]
    chips_html = "".join([f'<a href="?q={q}" target="_self" class="dnw-chip-btn">#{q}</a>' for q in quick_queries])
    st.markdown(f'<div class="dnw-chips-wrap"><span class="dnw-chip-label">인기 검색어:</span>{chips_html}</div>', unsafe_allow_html=True)

    with st.form("search_form", clear_on_submit=False):
        st.markdown('<div class="dnw-search-wrap">', unsafe_allow_html=True)
        col_search, col_btn = st.columns([5, 1], gap="small")
        with col_search:
            default_val = selected_quick_query if selected_quick_query else ""
            query = st.text_input("검색", value=default_val, placeholder="상품명 또는 키워드를 검색하세요", label_visibility="collapsed")
        with col_btn:
            search_clicked = st.form_submit_button("검색", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 퀵 검색 클릭 시 자동 검색 실행 처리
    if selected_quick_query:
        query = selected_quick_query
        search_clicked = True

    if search_clicked:
        if not query or not query.strip():
            st.warning("검색어를 입력해 주세요.")
        else:
            # AGENTS.md Rule 2: 검색 실행 시 selected_product 즉시 삭제
            if 'selected_product' in st.session_state:
                del st.session_state['selected_product']

            with st.spinner(f"{query} 상품을 검색 중입니다..."):
                items, error_msg = collector.search_shopping_products_realtime(query.strip(), display=40)
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
            col_cnt, col_sort, col_spacer = st.columns([0.10, 0.55, 0.35], gap="small")
            total_items = len(items)
            items_per_page = 8
            total_pages = (total_items + items_per_page - 1) // items_per_page
            
            if 'current_page' not in st.session_state:
                st.session_state['current_page'] = 1
            current_page = st.session_state['current_page']

            with col_cnt:
                st.markdown(f"<div style='font-size:1.02rem; color:#0F172A; font-weight:800; display:flex; align-items:center; height:100%; min-height:38px;'>검색 결과 <b>{total_items}</b>개 <span style='font-size:0.85rem; color:#64748B; font-weight:600; margin-left:0.2rem;'>({current_page} / {total_pages} 페이지)</span></div>", unsafe_allow_html=True)

            with col_sort:
                sort_option = st.radio("정렬 기준", ["인기순", "낮은가격순", "높은가격순", "정확도순"], horizontal=True, label_visibility="collapsed", key="search_sort_option")

            # 정렬 옵션별 결과 리스트 생성
            if sort_option == "낮은가격순":
                sorted_items = sorted(items, key=lambda x: x['lprice'])
            elif sort_option == "높은가격순":
                sorted_items = sorted(items, key=lambda x: x['lprice'], reverse=True)
            elif sort_option == "정확도순":
                q_terms = [w.lower() for w in query.strip().split() if w]
                sorted_items = sorted(items, key=lambda x: sum(1 for t in q_terms if t in x['title'].lower()), reverse=True)
            else: # 인기순 (다나와 실시간 수집 랭킹 원본)
                sorted_items = items

            start_idx = (current_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_items = sorted_items[start_idx:end_idx]

            selected_id = st.session_state.get('selected_product', {}).get('product_id')

            # 상품 카드 렌더링 (AGENTS.md 규칙 적용)
            grid_container = st.container()
            with grid_container:
                for row_start in range(0, len(page_items), 4):
                    row_items = page_items[row_start:row_start + 4]
                    cols = st.columns(4)
                    for i, item in enumerate(row_items):
                        with cols[i]:
                            img_src = item['image_url'] if item['image_url'] else "https://via.placeholder.com/200/115DCE/FFFFFF?text=Danawa"
                            
                            # AGENTS.md Rule 1 & Rule 3:
                            # selected_id 가 None 이면 모든 카드가 기본 백색 100% (Rule 1)
                            # selected_id 가 존재하면 선택된 카드는 .selected, 미선택 카드는 .unselected 딤 처리 (Rule 3)
                            card_class = "dnw-card"
                            if selected_id is not None:
                                card_class += " selected" if str(item['product_id']) == str(selected_id) else " unselected"
                            
                            spec_tags = item.get('spec_tags', [])
                            tags_html = "".join([f'<span class="dnw-spec-tag">{t}</span>' for t in spec_tags[:3]])
                            
                            p_id = item['product_id']
                            global_idx = row_start + i
                            btn_key = f"btn_{p_id}_{global_idx}"
                                
                            html_card = f"""
                            <div class="{card_class}">
                                <div class="dnw-img-box">
                                    <img src="{img_src}" />
                                </div>
                                <div class="dnw-info-box">
                                    <div class="dnw-title">{item['title']}</div>
                                    <div class="dnw-specs-wrap">
                                        {tags_html}
                                    </div>
                                    <div class="dnw-price-box">
                                        <span class="dnw-badge-min">최저가</span>
                                        <div class="dnw-price-val"><b>{item['lprice']:,}</b>원</div>
                                    </div>
                                    <div class="dnw-mall-name">판매처: {item.get('mall_name', '다나와 제휴몰')}</div>
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
                if st.button("< 이전", disabled=(current_page <= 1), use_container_width=True):
                    st.session_state['current_page'] -= 1
                    st.rerun()
            with pg_col3:
                if st.button("다음 >", disabled=(current_page >= total_pages), use_container_width=True):
                    st.session_state['current_page'] += 1
                    st.rerun()

    if st.session_state.get('open_dialog') and 'selected_product' in st.session_state:
        st.session_state['open_dialog'] = False
        show_product_detail_dialog(st.session_state['selected_product'])

with tab2:
    st.markdown("<h4 style='margin-bottom:1rem; color:#0F172A; font-weight:800;'>찜한 상품 및 수집 데이터 목록</h4>", unsafe_allow_html=True)
    df_products = get_all_products()
    if not df_products.empty:
        st.dataframe(df_products, use_container_width=True)
    else:
        st.info("저장된 상품이 없습니다. 검색 후 [가격 추세 분석]을 실행해 보세요.")

with tab3:
    st.markdown("<h4 style='margin-bottom:1rem; color:#0F172A; font-weight:800;'>상품 가격 추세 비교</h4>", unsafe_allow_html=True)
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
                xaxis=dict(showgrid=True, gridcolor='#F1F5F9'), yaxis=dict(showgrid=True, gridcolor='#F1F5F9')
            )
            st.plotly_chart(fig_compare, use_container_width=True)
    else:
        st.info("비교할 수집 상품 데이터가 없습니다.")
