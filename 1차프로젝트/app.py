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
import db_manager
importlib.reload(collector)
importlib.reload(analyzer)
importlib.reload(ml_forecaster)
importlib.reload(config)
importlib.reload(db_manager)
from database import init_db, save_product_and_price, get_price_history, get_all_products
from collector import search_naver_shopping, generate_mock_price_history
from analyzer import analyze_price_trend

def get_cached_danawa_popular_trend_products():
    return collector.get_danawa_popular_trend_products()

# Streamlit 페이지 설정
st.set_page_config(
    page_title="BuyOrWait - 실시간 최저가 & AI 가격 분석기",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 데이터베이스 초기화
init_db()

# F5 새로고침 시 회원 로그인 세션 자동 유지/복원 및 로그아웃
if st.query_params.get('logout') == '1':
    if 'user' in st.session_state:
        del st.session_state['user']
    st.query_params.clear()
    st.rerun()

db_p_init = st.session_state.get('db_pass', '1111')
if 'user' not in st.session_state and st.query_params.get('uid'):
    try:
        uid = int(st.query_params['uid'])
        restored_user = db_manager.get_user_by_id(uid, db_pass=db_p_init)
        if restored_user:
            st.session_state['user'] = restored_user
    except Exception:
        pass

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
    /* 검색창 전용 input & 버튼 스타일 (dnw-search-wrap 내부만 한정) */
    .dnw-search-wrap div[data-testid="stTextInput"] input {
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        padding: 1rem 1.2rem !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        background: transparent !important;
        color: #0F172A !important;
    }
    .dnw-search-wrap div[data-testid="stForm"] .stButton > button {
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
    .dnw-search-wrap div[data-testid="stForm"] .stButton > button:hover {
        background-color: #0D4AA5 !important;
    }

    /* 비밀번호 입력창 우측 요소(눈동자 보기 버튼 포함) 완전 숨김 처리 */
    div[data-testid="stTextInput"] div[data-baseweb="input"] > div:nth-child(2),
    div[data-baseweb="input"] input ~ *,
    div[data-testid="stTextInput"] button,
    div[data-baseweb="input"] button,
    button[aria-label*="password"],
    button[aria-label*="Password"],
    div[data-baseweb="input"] [role="button"],
    [data-testid="stInputIcon"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        width: 0 !important;
        height: 0 !important;
        max-width: 0 !important;
        max-height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
        background: transparent !important;
        pointer-events: none !important;
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

    /* CSV 다운로드 버튼 우측 상단 배치 컴팩트 스타일 */
    .stDownloadButton > button {
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        padding: 0.25rem 0.6rem !important;
        height: 32px !important;
        min-height: 32px !important;
        line-height: 1.2 !important;
        border-radius: 5px !important;
        border: 1px solid #CBD5E1 !important;
        color: #334155 !important;
        background-color: #FFFFFF !important;
        white-space: nowrap !important;
        word-break: keep-all !important;
    }
    .stDownloadButton > button:hover {
        border-color: #115DCE !important;
        color: #115DCE !important;
        background-color: #F8FAFC !important;
    }

    /* GNB 우측 회원 정보 및 로그아웃 버튼 스타일 */
    .dnw-logout-btn {
        display: inline-block !important;
        background: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        color: #334155 !important;
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        padding: 0.18rem 0.65rem !important;
        border-radius: 4px !important;
        text-decoration: none !important;
        transition: all 0.15s ease !important;
        line-height: 1.4 !important;
        cursor: pointer !important;
    }
    .dnw-logout-btn:hover {
        border-color: #115DCE !important;
        color: #115DCE !important;
        background: #F1F5F9 !important;
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
        background-color: #FFFFFF !important;
        opacity: 1.0 !important;
        filter: none !important;
        border: 1px solid #E2E8F0 !important;
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
    st.session_state['dialog_showing'] = True
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
    df_generated = generate_mock_price_history(selected['product_id'], lprice, days=1095, pattern="auto")
    
    eff_p, tot_sav, c_disc, p_point = analyzer.calculate_effective_price(lprice)

    df_hist = get_price_history(selected['product_id'])
    if df_hist.empty or 'collected_at' not in df_hist.columns or len(df_hist) < 3:
        if df_generated is not None and not df_generated.empty:
            df_hist = df_generated
        else:
            df_hist = generate_mock_price_history(selected['product_id'], lprice, days=1095, pattern="auto")
            if df_hist is None or df_hist.empty:
                df_hist = pd.DataFrame(columns=['price', 'collected_at'])

    db_p = st.session_state.get('db_pass', '1111')
    sales_events = db_manager.get_upcoming_sales_events(db_pass=db_p)
    analysis = analyze_price_trend(df_hist, days=180, upcoming_events=sales_events)
    ml = analysis.get('ml_forecast')

    # 다나와 쇼핑몰별 가격비교 테이블 HTML 생성 (들여쓰기 제거로 Markdown 코드블록 이스케이프 방지)
    mall_rows_html = ""
    for m in mall_prices:
        badge_html = f'<span style="background:#E52528; color:#FFF; font-weight:800; font-size:0.75rem; padding:0.15rem 0.4rem; border-radius:2px; margin-right:0.4rem;">{m["badge"]}</span>' if m.get("badge") else ""
        price_color = "#115DCE" if m.get("badge") else "#0F172A"
        mall_rows_html += f'<div style="display: flex; justify-content: space-between; align-items: center; padding: 0.6rem 0.4rem; font-size: 0.95rem; border-bottom: 1px solid #E2E8F0;"><div style="font-weight: 700; color: #334155; width: 140px;">{m["mall"]}</div><div style="flex: 1; text-align: right; margin-right: 1.5rem;">{badge_html}<a href="{m["link"]}" target="_blank" style="text-decoration: none; color: {price_color}; font-weight: 800; font-size: 1.1rem;">{m["price"]:,}원</a></div><div style="color: #64748B; font-size: 0.85rem; width: 80px; text-align: right;">{m["shipping"]}</div></div>'

    spec_tags_html = "".join([f'<span style="background:#F1F5F9; color:#334155; font-size:0.8rem; font-weight:600; padding:0.2rem 0.6rem; border-radius:4px; margin-right:0.3rem; margin-bottom:0.3rem; display:inline-block;">{tag}</span>' for tag in selected.get('spec_tags', [])])

    display_title = analyzer.clean_product_name(selected['title'])

    st.markdown(f"""
<div style="font-size: 1.4rem; font-weight: 800; color: #0F172A; margin-bottom: 0.3rem;">
{display_title} 
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
<div style="display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1.2rem; background:#F8FAFC; padding:1rem; border-radius:8px; border:1px solid #E2E8F0;">
<div>
<span style="font-size: 0.9rem; font-weight: 700; color: #64748B; display:block;">실시간 최저가</span>
<span style="font-size: 2.2rem; font-weight: 900; color: #115DCE;">{lprice:,}원</span>
</div>
<div style="background:#EFF6FF; border:1px solid #BFDBFE; padding:0.4rem 0.8rem; border-radius:6px; font-size:0.88rem; color:#1E40AF; font-weight:700;">
[체감 실구매가]: <b>{eff_p:,}원</b> <span style="font-size:0.8rem; color:#3B82F6;">(카드청구 5% + 페이 1% 적립 시 {tot_sav:,}원 추가 절감)</span>
</div>
</div>
<div style="font-size: 1rem; font-weight: 800; color: #0F172A; margin-bottom: 0.6rem; border-bottom: 2px solid #E2E8F0; padding-bottom: 0.4rem;">
쇼핑몰별 실시간 최저가 비교
</div>
<div style="display: flex; flex-direction: column; gap: 0.2rem;">
{mall_rows_html}
</div>""", unsafe_allow_html=True)

    current_user = st.session_state.get('user')
    p_id = selected['product_id']
    db_p = st.session_state.get('db_pass', '1111')
    is_fav = db_manager.is_favorite(current_user['user_id'], p_id, db_pass=db_p) if current_user else False

    # 목표 알림가 설정 UI (찜하기 시 원하는 목표 가격 지정)
    default_target = int(lprice * 0.95)
    c_tp1, c_tp2 = st.columns([2.5, 1.5])
    with c_tp1:
        st.markdown(f"""
            <div style="font-size:0.85rem; font-weight:700; color:#334155; margin-top:0.4rem;">
                목표 알림가 설정 (현재 최저가: <b style="color:#115DCE;">{lprice:,}원</b>)
            </div>
        """, unsafe_allow_html=True)
    with c_tp2:
        target_price_val = st.number_input("목표가 (원)", min_value=0, value=default_target, step=1000, key=f"inp_tp_{p_id}", label_visibility="collapsed")

    col_btn_fav, col_btn_cmp, col_btn_buy = st.columns([1, 1, 1])

    compare_list = st.session_state.get('compare_items', [])
    is_cmp = any(str(x['product_id']) == str(p_id) for x in compare_list)

    with col_btn_fav:
        if is_fav:
            if st.button("찜 해제", key=f"fav_btn_dlg_{p_id}", use_container_width=True):
                db_manager.remove_favorite(current_user['user_id'], p_id, db_pass=db_p)
                st.toast("찜 목록에서 삭제되었습니다.")
                st.rerun()
        else:
            if st.button("찜하기 (목표가 알림)", key=f"fav_btn_dlg_{p_id}", type="primary", use_container_width=True):
                if not current_user:
                    st.session_state['show_auth_modal'] = True
                    st.rerun()
                else:
                    db_manager.add_favorite(current_user['user_id'], selected, target_price=int(target_price_val), db_pass=db_p)
                    st.toast(f"목표가 {int(target_price_val):,}원 설정 및 찜 목록 추가 완료!")
                    st.rerun()

    with col_btn_cmp:
        if is_cmp:
            if st.button("비교함 해제", key=f"cmp_btn_dlg_{p_id}", use_container_width=True):
                st.session_state['compare_items'] = [x for x in compare_list if str(x['product_id']) != str(p_id)]
                st.toast("비교함에서 삭제되었습니다.")
                st.rerun()
        else:
            if st.button("+ 비교함 담기", key=f"cmp_btn_dlg_{p_id}", type="primary", use_container_width=True):
                if len(compare_list) >= 4:
                    st.warning("비교함에는 최대 4개 상품까지 담을 수 있습니다.")
                else:
                    if 'compare_items' not in st.session_state:
                        st.session_state['compare_items'] = []
                    st.session_state['compare_items'].append(selected)
                    st.toast("비교함에 추가되었습니다.")
                    st.rerun()

    with col_btn_buy:
        st.markdown(f'<a href="{danawa_url}" target="_blank" style="display:block; text-align:center; background: #115DCE; color: #FFFFFF; font-size: 0.95rem; font-weight: 800; padding: 0.55rem 1rem; border-radius: 6px; text-decoration: none; box-shadow: 0 4px 10px rgba(17, 93, 206, 0.25); margin-bottom: 1rem;">최저가 구매하러가기</a>', unsafe_allow_html=True)

    # AI 구매 추천 분석 카드
    st.markdown(f"""
<div style="background:#F0F7FF; border:1px solid #BAE6FD; border-radius:8px; padding:1.2rem; margin-bottom:1.2rem;">
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

    # 쇼핑몰 세일 임박 알림 전용 독립 카드 (중복/다중 세일 지원)
    sale_alerts = analysis.get('sale_alerts', [])
    if sale_alerts:
        for sa in sale_alerts:
            d_left = sa['days_left']
            d_str = "지금 진행 중!" if d_left <= 0 else f"D-{d_left}"
            st.markdown(f"""
<div style="background:#FFFBEB; border:1.5px solid #FCD34D; border-radius:8px; padding:1.1rem; margin-bottom:1rem; box-shadow: 0 2px 8px rgba(245, 158, 11, 0.1);">
<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.4rem;">
<div style="display:flex; align-items:center; gap:0.6rem;">
<span style="background:#E11D48; color:#FFF; font-weight:800; font-size:0.8rem; padding:0.2rem 0.6rem; border-radius:4px;">쇼핑몰 세일 임박</span>
<span style="font-size:1.1rem; font-weight:800; color:#9F1239;">{sa['event_name']} ({d_str})</span>
</div>
<div style="font-size:0.9rem; font-weight:800; color:#B45309;">평균 최대 {sa['discount_rate_avg']}% 할인 예상</div>
</div>
<div style="font-size:0.92rem; color:#78350F; line-height:1.4;">
약 {d_left}일 후 <b>{sa['mall_name']} {sa['event_name']}</b> 행사가 진행될 예정입니다. 급하지 않다면 <b>구매를 보류하고 세일 기간에 구매하시는 것을 강력 추천</b>합니다!
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='font-size:1.1rem; font-weight:800; color:#0F172A; margin-bottom:0.5rem;'>가격변동 및 AI예측 차트</div>", unsafe_allow_html=True)
    
    # 엑셀(CSV) 내보내기 데이터 사전 준비
    csv_rows = []
    if not df_hist.empty and 'collected_at' in df_hist.columns and 'price' in df_hist.columns:
        for _, r in df_hist.iterrows():
            c_eff_p, c_sav, _, _ = analyzer.calculate_effective_price(int(r['price']))
            csv_rows.append({
                "수집일자": pd.to_datetime(r['collected_at']).strftime("%Y-%m-%d %H:%M"),
                "상품명": selected['title'],
                "최저가(원)": int(r['price']),
                "체감가(원)": c_eff_p,
                "할인혜택(원)": c_sav,
                "구분": "실제 최저가 수집 이력"
            })

    if ml and ml.get('forecast_df') is not None and not ml['forecast_df'].empty:
        for _, r in ml['forecast_df'].iterrows():
            c_eff_p, c_sav, _, _ = analyzer.calculate_effective_price(int(r['price']))
            csv_rows.append({
                "수집일자": pd.to_datetime(r['collected_at']).strftime("%Y-%m-%d"),
                "상품명": selected['title'],
                "최저가(원)": int(r['price']),
                "체감가(원)": c_eff_p,
                "할인혜택(원)": c_sav,
                "구분": "AI 14일 미래 예측가"
            })

    df_export = pd.DataFrame(csv_rows) if csv_rows else pd.DataFrame()
    csv_bytes = df_export.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig') if not df_export.empty else b""

    # 조회 기간 필터 (좌측) + CSV 다운로드 버튼 (동일 행 우측 끝 밀착 배치)
    c_tf1, c_tf2 = st.columns([0.78, 0.22])
    with c_tf1:
        timeframe = st.radio("조회 기간", ["1개월", "3개월", "6개월", "1년", "전체"], index=1, horizontal=True, label_visibility="collapsed", key=f"tf_{selected['product_id']}")
    with c_tf2:
        if csv_bytes:
            clean_file_id = str(selected.get('product_id', 'report'))
            st.download_button(
                label="CSV 다운로드",
                data=csv_bytes,
                file_name=f"BuyOrWait_가격분석_{clean_file_id}.csv",
                mime="text/csv",
                key=f"btn_dl_csv_{selected['product_id']}",
                use_container_width=True
            )

    days_map = {"1개월": 30, "3개월": 90, "6개월": 180, "1년": 365, "전체": None}
    selected_days = days_map[timeframe]

    if selected_days is not None and not df_hist.empty and 'collected_at' in df_hist.columns and df_hist['collected_at'].notna().any():
        cutoff = pd.to_datetime(df_hist['collected_at'].max()) - pd.Timedelta(days=selected_days)
        df_plot = df_hist[df_hist['collected_at'] >= cutoff]
    else:
        df_plot = df_hist

    avg_p = analysis.get('avg_price', 0)
    fig = go.Figure()

    x_vals = df_plot['collected_at'].tolist() if (not df_plot.empty and 'collected_at' in df_plot.columns) else []
    y_vals = df_plot['price'].tolist() if (not df_plot.empty and 'price' in df_plot.columns) else []

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

    # AI 동급 스펙 가성비 대체 상품 추천 카드
    alts = analyzer.find_cheaper_spec_alternatives(selected, st.session_state.get('search_items', []))
    if alts:
        st.markdown(f"""
            <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:1rem; margin-top:1.2rem; margin-bottom:0.8rem;">
                <div style="font-size:1.05rem; font-weight:800; color:#0F172A; margin-bottom:0.2rem;">
                    [AI 가성비 대체 상품 추천] (동급 스펙 대비 최대 {alts[0]['savings']:,}원 절약 가능)
                </div>
                <div style="font-size:0.85rem; color:#64748B;">현재 상품과 핵심 스펙이 유사하지만 더 저렴한 대체 모델을 AI가 탐지했습니다.</div>
            </div>
        """, unsafe_allow_html=True)
        
        for alt_idx, alt in enumerate(alts):
            alt_item = alt['item']
            alt_p = alt_item['lprice']
            alt_sav = alt['savings']
            alt_pct = alt['savings_pct']
            alt_clean_title = analyzer.clean_product_name(alt_item['title'])
            
            c_a1, c_a2 = st.columns([4, 1])
            with c_a1:
                st.markdown(f"""
                    <div style="background:#FFF; border:1px solid #CBD5E1; border-radius:6px; padding:0.8rem; margin-bottom:0.5rem; display:flex; align-items:center; gap:1rem;">
                        <img src="{alt_item['image_url']}" style="width:55px; height:55px; object-fit:contain; border-radius:4px;" />
                        <div>
                            <div style="font-weight:700; font-size:0.9rem; color:#0F172A; margin-bottom:0.2rem;">{alt_clean_title}</div>
                            <div style="font-size:0.85rem; color:#64748B;">
                                <span style="font-size:1.05rem; font-weight:800; color:#115DCE;">{alt_p:,}원</span> 
                                <span style="background:#DCFCE7; color:#15803D; font-weight:800; padding:0.15rem 0.5rem; border-radius:4px; margin-left:0.4rem;">-{alt_sav:,}원 (-{alt_pct}%) 더 저렴!</span>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            with c_a2:
                if st.button("이 상품 보기", key=f"btn_switch_alt_{alt_item['product_id']}_{alt_idx}", use_container_width=True):
                    st.session_state['selected_product'] = alt_item
                    st.session_state['open_dialog'] = True
                    st.rerun()


# ============================================================
# 사이드바 PostgreSQL DB 접속 비밀번호 설정 (DBeaver 연동)
# ============================================================
with st.sidebar:
    st.markdown("<h4 style='color:#0F172A; font-weight:800; margin-bottom:0.2rem;'>PostgreSQL DB 설정</h4>", unsafe_allow_html=True)
    st.caption("DBeaver / PostgreSQL 접속 비밀번호를 입력해 주세요.")
    
    current_db_pass = st.session_state.get('db_pass', '1111')
    input_db_pass = st.text_input("DB 비밀번호", value=current_db_pass, type="password", key="sidebar_db_pass_input")
    st.session_state['db_pass'] = input_db_pass
    
    if st.button("DB 연결 테스트", key="btn_test_db", use_container_width=True):
        is_ok, msg = db_manager.test_db_connection(password=input_db_pass)
        if is_ok:
            st.success(msg)
        else:
            st.error(msg)

# ============================================================
# 회원 로그인 / 회원가입 인증 모달 (st.dialog)
# ============================================================
if st.session_state.get('show_auth_modal'):
    st.session_state['show_auth_modal'] = False  # 모달 오픈 시 1회성 플래그 즉시소진 (반복 팝업 방지)
    
    @st.dialog("BuyOrWait 회원 서비스")
    def render_auth_dialog():
        tab_login, tab_signup = st.tabs(["로그인", "회원가입"])
        db_p = st.session_state.get('db_pass', '1111')
        
        with tab_login:
            st.markdown("<div style='font-size:0.9rem; color:#64748B; margin-bottom:0.8rem;'>가입하신 이메일과 비밀번호를 입력해 주세요.</div>", unsafe_allow_html=True)
            with st.form("login_form", border=False):
                login_email = st.text_input("이메일", key="login_email_input", placeholder="example@email.com")
                login_pw = st.text_input("비밀번호", type="password", key="login_pw_input")
                submit_login = st.form_submit_button("로그인하기", type="primary", use_container_width=True)
                
                if submit_login:
                    if not login_email or not login_pw:
                        st.error("이메일과 비밀번호를 모두 입력해 주세요.")
                    else:
                        success, res = db_manager.login_user(login_email, login_pw, db_pass=db_p)
                        if success:
                            st.session_state['user'] = res
                            st.query_params['uid'] = res['user_id']
                            st.success(f"{res['nickname']}님 환영합니다!")
                            st.rerun()
                        else:
                            st.error(res)
                            st.info("💡 사이드바(왼쪽 화살표)에서 PostgreSQL 비밀번호를 수정하신 후 다시 시도해 주세요.")

        with tab_signup:
            st.markdown("<div style='font-size:0.9rem; color:#64748B; margin-bottom:0.8rem;'>1초 만에 간편 회원가입 후 찜 목록 및 알림을 받아보세요.</div>", unsafe_allow_html=True)
            with st.form("signup_form", border=False):
                signup_email = st.text_input("이메일 주소", key="signup_email_input", placeholder="example@email.com")
                signup_nick = st.text_input("닉네임", key="signup_nick_input", placeholder="홍길동")
                signup_pw = st.text_input("비밀번호", type="password", key="signup_pw_input")
                signup_pw_confirm = st.text_input("비밀번호 확인", type="password", key="signup_pw_confirm_input")
                submit_signup = st.form_submit_button("회원가입 완료", type="primary", use_container_width=True)
                
                if submit_signup:
                    if not signup_email or not signup_nick or not signup_pw:
                        st.error("모든 항목을 입력해 주세요.")
                    elif signup_pw != signup_pw_confirm:
                        st.error("비밀번호 확인이 일치하지 않습니다.")
                    else:
                        success, res = db_manager.register_user(signup_email, signup_pw, signup_nick, db_pass=db_p)
                        if success:
                            st.session_state['user'] = res
                            st.query_params['uid'] = res['user_id']
                            st.success(f"{res['nickname']}님 회원가입이 완료되었습니다!")
                            st.rerun()
                        else:
                            st.error(res)
                            st.info("💡 사이드바(왼쪽 화살표)에서 PostgreSQL 비밀번호를 수정하신 후 다시 시도해 주세요.")

    render_auth_dialog()

# GNB (BuyOrWait 헤더 + 우측 회원 서비스 컨트롤)
col_logo, col_auth = st.columns([3.8, 1.2])

with col_logo:
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

with col_auth:
    current_user = st.session_state.get('user')
    if current_user:
        st.markdown(f"""
            <div style="display:flex; flex-direction:column; align-items:flex-end; width:100%; padding-top:0.2rem;">
                <div style="display:flex; flex-direction:column; align-items:center; width:fit-content;">
                    <div style="font-size:0.92rem; color:#0F172A; font-weight:800; margin-bottom:0.25rem; text-align:center; white-space:nowrap;">{current_user['nickname']}님</div>
                    <a href="/?logout=1" target="_self" class="dnw-logout-btn">로그아웃</a>
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        if st.button("로그인 / 회원가입", key="btn_open_auth", use_container_width=True, type="primary"):
            st.session_state['show_auth_modal'] = True
            st.rerun()

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
    # 비교함 플로팅 안내 바
    compare_list = st.session_state.get('compare_items', [])
    if compare_list:
        st.markdown(f"""
            <div style="background:#1E293B; color:#FFFFFF; border-radius:8px; padding:0.8rem 1.2rem; margin-bottom:0.8rem; display:flex; align-items:center; justify-content:space-between; box-shadow:0 4px 12px rgba(0,0,0,0.15);">
                <div style="display:flex; align-items:center; gap:0.8rem;">
                    <span style="background:#115DCE; color:#FFF; font-weight:800; font-size:0.82rem; padding:0.25rem 0.65rem; border-radius:4px;">비교함</span>
                    <span style="font-weight:700; font-size:0.95rem;"><b>{len(compare_list)} / 4개</b> 상품이 비교함에 담겼습니다 (3번째 탭 [가격 추세 비교]에서 자동 분석)</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        c_bar1, c_bar2 = st.columns([1, 4])
        with c_bar1:
            if st.button("비교함 비우기", key="btn_clear_cmp_bar", use_container_width=True):
                st.session_state['compare_items'] = []
                st.rerun()

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
            col_cnt, col_sort, col_spacer = st.columns([0.11, 0.59, 0.30], gap="small")
            total_items = len(items)
            items_per_page = 8
            total_pages = (total_items + items_per_page - 1) // items_per_page
            
            if 'current_page' not in st.session_state:
                st.session_state['current_page'] = 1
            current_page = st.session_state['current_page']

            with col_cnt:
                st.markdown(f"<div style='font-size:1.02rem; color:#0F172A; font-weight:800; display:flex; align-items:center; height:100%; min-height:38px; white-space:nowrap;'>검색 결과 <b>{total_items}</b>개 <span style='font-size:0.85rem; color:#64748B; font-weight:600; margin-left:0.25rem; white-space:nowrap;'>({current_page} / {total_pages} 페이지)</span></div>", unsafe_allow_html=True)

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

            # 팝업 열기 상태가 아니면 selected_product 정리하여 팝업 닫힘 시 100% 백색 초기화
            if not st.session_state.get('open_dialog'):
                if 'selected_product' in st.session_state:
                    del st.session_state['selected_product']

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
                            card_style = "background-color: #FFFFFF !important; opacity: 1.0 !important; filter: none !important;"
                            if selected_id is not None and str(item['product_id']) == str(selected_id):
                                card_class += " selected"
                                card_style = "border: 3px solid #115DCE !important; background-color: #FFFFFF !important; opacity: 1.0 !important; filter: none !important;"
                            
                            spec_tags = item.get('spec_tags', [])
                            tags_html = "".join([f'<span class="dnw-spec-tag">{t}</span>' for t in spec_tags[:3]])
                            
                            p_id = item['product_id']
                            global_idx = row_start + i
                            btn_key = f"btn_{p_id}_{global_idx}"
                                
                            eff_p, tot_sav, _, _ = analyzer.calculate_effective_price(item['lprice'])
                            clean_card_title = analyzer.clean_product_name(item['title'])
                            
                            html_card = f"""
                            <div class="{card_class}" style="{card_style}">
                                <!-- state:{selected_id} -->
                                <div class="dnw-img-box">
                                    <img src="{img_src}" />
                                </div>
                                <div class="dnw-info-box">
                                    <div class="dnw-title">{clean_card_title}</div>
                                    <div class="dnw-specs-wrap">
                                        {tags_html}
                                    </div>
                                    <div class="dnw-price-box">
                                        <span class="dnw-badge-min">최저가</span>
                                        <div class="dnw-price-val"><b>{item['lprice']:,}</b>원</div>
                                    </div>
                                    <div style="font-size:0.75rem; color:#1E40AF; background:#EFF6FF; border:1px solid #BFDBFE; border-radius:4px; padding:0.15rem 0.4rem; margin-top:0.25rem; font-weight:700;">
                                        체감가 {eff_p:,}원 <span style="font-size:0.7rem; color:#3B82F6;">(-{tot_sav:,}원)</span>
                                    </div>
                                    <div class="dnw-mall-name" style="margin-top:0.2rem;">판매처: {item.get('mall_name', '다나와 제휴몰')}</div>
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
    else:
        # 랜딩 페이지: 상품 전체 카테고리 (11) + 실시간 급상승 대표 상품 Top 4
        full_danawa_categories = {
            "지금 필요한 여름템": {
                "2026년형 필수가전": ["LG 퓨리케어 에어컨 2026", "창문형 에어컨 Pro 2026", "삼성 비스포크 제습기 2026", "BLDC 저소음 써큘레이터", "LG 퓨리케어 제습기 20L", "파나소닉 저소음 선풍기", "신일 타워형 선풍기 2026", "삼성 비스포크 무풍 에어컨"],
                "2026년형 올인원 가전세트": ["LG 올인원 세탁건조기 Pro", "삼성 비스포크 AI 세탁건조기", "로보락 S8 MaxV Ultra", "다이슨 V15 무선청소기", "삼성 비스포크 식기세척기", "LG 디오스 오브제 김치냉장고", "쿠쿠 IH 압력밥솥 6인용", "SK매직 식기세척기 12인용"],
                "2026년형 트렌드 음료": ["코카콜라 제로 500ml", "스프라이트 500ml", "빅토리아 탄산수 500ml", "삼다수 2L 6병 세트", "칠성사이다 제로 355ml", "몬스터 에너지 355ml", "웰치스 제로 포도 355ml", "닥터페퍼 제로 355ml"]
            },
            "가전 · TV": {
                "2026년형 TV/영상": ["LG 올레드 evo G4 77인치", "삼성 Neo QLED 8K 85인치", "LG Mini RGB TV 65인치", "4K UHD 빔프로젝터", "삼성 스마트 모니터 M8 32인치", "LG 시네빔 라제닉스 4K", "삼성 더 프레임 TV 65인치", "소니 브라비아 XR 4K TV"],
                "2026년형 생활/세탁가전": ["LG 올인원 세탁건조기 Pro", "삼성 비스포크 AI 드럼세탁기", "로보락 S8 MaxV Ultra", "다이슨 V15 무선청소기", "LG 코드제로 A9S 무선청소기", "삼성 비스포크 제트 청소기", "샤오미 자동먼지비움 청소기", "에코백스 디봇 X2 옴니"],
                "2026년형 주방/냉장고": ["LG 디오스 오브제 냉장고 870L", "삼성 비스포크 AI 김치냉장고", "빌트인 식기세척기 14인용", "비스포크 AI 인덕션 2026", "쿠쿠 6인용 IH 압력밥솥", "발뮤다 더 토스터 3세대", "필립스 에어프라이어 XXL", "휴롬 즙마스터 착즙기"]
            },
            "컴퓨터 · 노트북 · 조립PC": {
                "2026년 최신형 프리미엄 노트북": ["삼성 갤럭시북5 Pro 360", "LG 그램 Pro 17 (2026)", "맥북프로 M4 Max 16형", "ASUS ROG 제피러스 G16", "레노버 리전 Pro 7i", "애플 맥북에어 M4 15형", "HP 오멘 16 게이밍 2026", "델 엑스피에스 16 (2026)"],
                "2026년 차세대 PC부품": ["인텔 Core 울트라 9 285K", "AMD 라이젠 9 9950X3D", "NVIDIA RTX 5090 32GB", "NVIDIA RTX 5080 16GB", "DDR5 64GB 7200MHz", "PCIe 5.0 4TB NVMe SSD", "ASUS ROG MAXIMUS 메인보드", "시소닉 1200W 파워서플라이"],
                "2026년 하이엔드 디스플레이": ["LG 울트라기어 OLED 4K", "삼성 오디세이 OLED G9", "32인치 4K 144Hz IPS 모니터", "알파스캔 AOC 27인치 QHD", "BENQ 조위 240Hz 모니터", "ASUS ROG SWIFT 360Hz", "한성 34인치 커브드 WQHD", "크로스오버 4K HDR 모니터"]
            },
            "태블릿 · 모바일 · 디카": {
                "2026년 최신 플래그십 스마트폰": ["갤럭시 S26 울트라 512G", "삼성 갤럭시 Z 폴드8 / Z 플립8", "아이폰 17 프로 맥스 512G", "애플 아이폰 17 프로", "자급제 5G 스마트폰 2026", "삼성 갤럭시 S26+ 256GB", "애플 아이폰 17 256GB", "샤오미 14 Pro 5G"],
                "2026년 최신 태블릿": ["갤럭시탭 S11 울트라 5G", "아이패드 프로 M4 13형", "애플 아이패드 에어 7세대", "삼성 갤럭시탭 S9 FE", "레노버 Y700 게이밍 태블릿", "애플 아이패드 11세대", "삼성 갤럭시탭 A9+", "샤오미 패드 6 Pro"],
                "2026년 스마트워치/디카": ["갤럭시워치9 울트라 LTE", "애플워치 울트라 3 49mm", "소니 A7M5 미러리스 카메라", "고프로 히어로13 4K", "캐논 EOS R6 Mark II", "애플워치 시리즈 10", "삼성 갤럭시워치7 44mm", "DJI 포켓 3 핸드헬드"]
            },
            "스포츠 · 골프": {
                "2026년 최신 골프용품": ["테일러메이드 2026 드라이버", "보이스캐디 2026 거리측정기", "타이틀리스트 Pro V1 2026", "캘러웨이 2026 아이언세트", "핑 G430 MAX 드라이버", "풋조이 2026 골프화", "골프버디 레이저 거리측정기", "오디세이 퍼터 2026"],
                "2026년 캠핑/아웃도어": ["스노우피크 2026 랜드락 텐트", "헬리녹스 체어 원 Pro", "대용량 파워뱅크 2000W", "크레모아 LED 캠핑 렌턴", "코베아 3웨이 올인원 버너", "파세코 캠핑 난로 2026", "스탠리 쿨러 아이스박스", "네이처하이크 에어텐트"]
            },
            "자동차 · 용품 · 공구": {
                "2026년 최신 블랙박스/차량": ["아이나비 QXD1 4K 블랙박스", "파인뷰 2채널 4K 블랙박스", "순성 카시트 (2026)", "불스원샷 70000 엔진세정제", "메이튼 차량용 거치대", "훠링 세차용품 풀세트", "카템 차량용 공기청정기", "아이나비 에어비타 워셔액"],
                "2026년 프리미엄 전동공구": ["디월트 20V MAX 전동드릴", "보쉬 18V 프로 콤보세트", "마키타 충전 공구세트", "아임삭 18V 임팩 드라이버", "밀워키 M18 충전 공구", "계양 18V 충전 드라이버", "스탠레이 레이저 수평기", "밀워키 툴박스 캐리어"]
            },
            "가구 · 조명": {
                "2026년 스마트 가구": ["시디즈 T50 헤드레스트 의자", "데스커 모션데스크 Pro", "템퍼 모션베드 퀸 (2026)", "듀오백 2026 에어체어", "한샘 샘책장 5단", "일룸 모션베드 싱글", "에이스침대 퀸사이즈", "퍼시스 리클라이너 소파"],
                "2026년 인테리어/조명": ["필립스 휴 스마트 조명 세트", "LED 거실등 150W (2026)", "이케아 장스탠드 조명", "아르떼미데 네시노 조명", "스피드랙 앵글 선반", "마켓비 서랍장 6단", "모던하우스 커튼 세트", "라인프렌즈 캐릭터 무드등"]
            },
            "식품 · 유아 · 완구": {
                "2026년 인기 탄산/음료": ["코카콜라 제로 500ml", "스프라이트 500ml", "칠성사이다 제로 355ml", "몬스터 에너지 355ml", "빅토리아 탄산수 500ml", "삼다수 2L 6병 세트", "나랑드사이다 제로 355ml", "환타 제로 오렌지 355ml"],
                "2026년 가공/자취식품": ["햇반 210g 24개 세트", "신라면 20봉 세트", "단백질 쉐이크 프로틴 2026", "동원참치 135g 12캔", "비비고 왕교자 만두 1kg", "스팸 클래식 200g 10캔", "오뚜기 3분 카레 10개", "너구리 라면 20봉 세트"]
            },
            "생활 · 주방 · 건강": {
                "2026년 건강/위생가전": ["바디프랜드 파라오 안마의자", "체중계 인바디 Dial H20", "세라젬 V7 메디컬 (2026)", "오므론 자동혈압계 2026", "브라운 체온계 6520", "코웨이 얼음정수기 2026", "청호나이스 정수기", "쿠쿠 얼음정수기"]
            },
            "패션 · 잡화 · 뷰티": {
                "2026년 뷰티/의류": ["다이슨 에어랩 멀티 스토어", "나이키 에어맥스 2026 신상", "샘소나이트 28인치 캐리어", "아디다스 러닝화 2026", "뉴발란스 993 운동화", "설화수 자음 2종 세트", "에스티로더 갈색병 에센스", "샤넬 샹스 향수 50ml"]
            },
            "반려동물 · 취미 · 사무": {
                "2026년 반려동물 인기품": ["로얄캐닌 사료 10kg", "벤토나이트 고양이 모래 12kg", "반려동물 자동급식기 Pro", "강아지 펫드라이룸 2026", "페스룸 펫 샴푸 500ml", "두부모래 7L 4개", "고양이 캣타워 대형", "강아지 배변패드 100매"]
            }
        }

        st.markdown("""
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:1.2rem 1.4rem; margin-bottom:1.5rem; box-shadow:0 2px 8px rgba(0,0,0,0.03);">
        """, unsafe_allow_html=True)

        c_m1, c_m2 = st.columns([0.75, 3.25], gap="small")
        with c_m1:
            st.markdown("<div style='font-size:0.92rem; font-weight:900; color:#115DCE; margin-bottom:0.5rem; border-bottom:2px solid #115DCE; padding-bottom:0.4rem;'>상품 전체 카테고리 (11)</div>", unsafe_allow_html=True)
            sel_main_cat = st.radio("전체 카테고리 대분류", list(full_danawa_categories.keys()), label_visibility="collapsed", key="mega_full_cat_radio")

        with c_m2:
            st.markdown(f"""
                <div style="background:#115DCE; color:#FFFFFF; font-weight:900; font-size:0.98rem; padding:0.6rem 1rem; border-radius:6px; margin-bottom:0.8rem; display:flex; align-items:center; justify-content:space-between;">
                    <span>{sel_main_cat} > 세부 카테고리 목록</span>
                    <span style="font-size:0.8rem; font-weight:600; background:rgba(255,255,255,0.2); padding:0.2rem 0.5rem; border-radius:4px;">원클릭 바로 분석</span>
                </div>
            """, unsafe_allow_html=True)

            sub_dict = full_danawa_categories[sel_main_cat]
            for grp_name, item_list in sub_dict.items():
                st.markdown(f"<div class='dnw-mega-group-title'>{grp_name}</div>", unsafe_allow_html=True)
                item_cols = st.columns(4)
                for i_idx, item_name in enumerate(item_list):
                    with item_cols[i_idx % 4]:
                        if st.button(f"▪ {item_name}", key=f"btn_full_m_{sel_main_cat}_{grp_name}_{item_name}", use_container_width=True):
                            st.session_state['selected_quick_query'] = item_name
                            st.rerun()
                st.markdown("<div style='margin-bottom:0.8rem;'></div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # 2단: 실시간 급상승 대표 상품 4종 카드
        st.markdown("""
            <div style="font-size:1.05rem; font-weight:800; color:#0F172A; margin-bottom:1rem; display:flex; align-items:center;">
                <span>실시간 급상승 대표 상품 Top 4</span>
            </div>
        """, unsafe_allow_html=True)

        pop_items = get_cached_danawa_popular_trend_products()
        if pop_items:
            pop_cols = st.columns(4)
            for p_idx, p_item in enumerate(pop_items[:4]):
                with pop_cols[p_idx]:
                    img_src = p_item['image_url'] if p_item['image_url'] else "https://via.placeholder.com/200/115DCE/FFFFFF?text=Danawa"
                    clean_title = analyzer.clean_product_name(p_item['title'])
                    eff_p, tot_sav, _, _ = analyzer.calculate_effective_price(p_item['lprice'])
                    
                    st.markdown(f"""
                        <div class="dnw-card" style="background-color: #FFFFFF !important; opacity: 1.0 !important; filter: none !important;">
                            <div class="dnw-img-box">
                                <img src="{img_src}" />
                            </div>
                            <div class="dnw-info-box">
                                <div class="dnw-title">{clean_title}</div>
                                <div class="dnw-price-box">
                                    <span class="dnw-badge-min">최저가</span>
                                    <div class="dnw-price-val"><b>{p_item['lprice']:,}</b>원</div>
                                </div>
                                <div style="font-size:0.75rem; color:#1E40AF; background:#EFF6FF; border:1px solid #BFDBFE; border-radius:4px; padding:0.15rem 0.4rem; margin-top:0.25rem; font-weight:700;">
                                    체감가 {eff_p:,}원 <span style="font-size:0.7rem; color:#3B82F6;">(-{tot_sav:,}원)</span>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button("가격 추세 분석", key=f"btn_pop_trend_{p_item['product_id']}_{p_idx}", use_container_width=True):
                        st.session_state['selected_product'] = p_item
                        st.session_state['open_dialog'] = True
                        st.rerun()

    if st.session_state.get('open_dialog') and 'selected_product' in st.session_state:
        st.session_state['open_dialog'] = False
        show_product_detail_dialog(st.session_state['selected_product'])

with tab2:
    st.markdown("<h4 style='margin-bottom:1rem; color:#0F172A; font-weight:800;'>찜한 상품 목록</h4>", unsafe_allow_html=True)
    
    current_user = st.session_state.get('user')
    if not current_user:
        st.markdown("""
            <div style="background:#F0F7FF; border:1px solid #BAE6FD; border-radius:10px; padding:2.2rem 1.5rem; text-align:center; margin:1rem 0;">
                <h3 style="color:#0F172A; font-size:1.2rem; font-weight:800; margin-bottom:0.5rem;">회원 전용 기능</h3>
                <p style="color:#64748B; font-size:0.92rem; margin-bottom:1.4rem; line-height:1.5;">
                    로그인하시면 관심 있는 상품을 나만의 찜 목록에 저장하고<br>
                    <b>목표 가격 하락 시 실시간 알림 서비스</b>를 이용하실 수 있습니다.
                </p>
            </div>
        """, unsafe_allow_html=True)
        col_m1, col_m2, col_m3 = st.columns([1, 1.2, 1])
        with col_m2:
            if st.button("로그인 / 회원가입", type="primary", key="tab2_login_btn", use_container_width=True):
                st.session_state['show_auth_modal'] = True
                st.rerun()
    else:
        db_p = st.session_state.get('db_pass', '1111')
        # 목표가 달성 상품 탐지 및 자동 이메일 알림 처리
        sent_cnt, alert_msg = db_manager.check_and_send_target_price_alerts(current_user['user_id'], db_pass=db_p)
        if sent_cnt > 0:
            st.toast(f"🎉 {sent_cnt}개 상품이 목표 알림가에 도달하여 {current_user['email']}로 알림 메일이 발송되었습니다!")

        fav_items = db_manager.get_user_favorites(current_user['user_id'], db_pass=db_p)
        if fav_items:
            for fav_idx, fav in enumerate(fav_items):
                clean_title = analyzer.clean_product_name(fav['title'])
                img_url = fav['image_url'] if fav.get('image_url') else "https://via.placeholder.com/80/115DCE/FFFFFF?text=Danawa"
                fav_p = fav['lprice']
                target_p = fav.get('target_price')
                fav_date = str(fav['favorited_at'])[:10] if fav.get('favorited_at') else ""
                
                # 목표가 달성 여부 뱃지 판별
                if target_p and target_p > 0:
                    if fav_p <= target_p:
                        status_badge = f'<span style="background:#DCFCE7; color:#15803D; font-weight:800; font-size:0.78rem; padding:0.2rem 0.5rem; border-radius:4px; margin-left:0.5rem;">🟢 목표가 달성! ({target_p:,}원 이하)</span>'
                    else:
                        diff = fav_p - target_p
                        status_badge = f'<span style="background:#FEF3C7; color:#B45309; font-weight:700; font-size:0.78rem; padding:0.2rem 0.5rem; border-radius:4px; margin-left:0.5rem;">🟡 목표가까지 {diff:,}원 남음 (목표: {target_p:,}원)</span>'
                else:
                    status_badge = '<span style="background:#F1F5F9; color:#64748B; font-weight:600; font-size:0.78rem; padding:0.2rem 0.5rem; border-radius:4px; margin-left:0.5rem;">목표가 미설정</span>'

                c_f1, c_f2 = st.columns([3.6, 1.4])
                with c_f1:
                    st.markdown(f"""
                        <div style="background:#FFF; border:1px solid #CBD5E1; border-radius:8px; padding:0.9rem 1.2rem; margin-bottom:0.4rem; display:flex; align-items:center; gap:1.2rem;">
                            <img src="{img_url}" style="width:65px; height:65px; object-fit:contain; border-radius:6px;" />
                            <div style="flex:1;">
                                <div style="font-weight:800; font-size:1.02rem; color:#0F172A; margin-bottom:0.25rem;">
                                    {clean_title} {status_badge}
                                </div>
                                <div style="font-size:0.88rem; color:#64748B;">
                                    현재 최저가: <span style="font-size:1.1rem; font-weight:800; color:#115DCE;">{fav_p:,}원</span>
                                    <span style="margin-left:1.2rem; font-size:0.8rem; color:#94A3B8;">등록일: {fav_date}</span>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                with c_f2:
                    c_m1, c_m2 = st.columns([1, 1])
                    with c_m1:
                        with st.popover("목표가 수정", use_container_width=True):
                            st.markdown("<div style='font-size:0.85rem; font-weight:700; color:#0F172A; margin-bottom:0.4rem;'>목표 알림가 변경</div>", unsafe_allow_html=True)
                            cur_tp_val = int(target_p) if (target_p and target_p > 0) else int(fav_p * 0.95)
                            new_tp = st.number_input("목표가 (원)", min_value=0, value=cur_tp_val, step=1000, key=f"inp_mod_tp_{fav['product_id']}_{fav_idx}")
                            if st.button("저장하기", key=f"btn_save_tp_{fav['product_id']}_{fav_idx}", type="primary", use_container_width=True):
                                db_manager.update_favorite_target_price(current_user['user_id'], fav['product_id'], int(new_tp), db_pass=db_p)
                                st.toast(f"목표가가 {int(new_tp):,}원으로 변경되었습니다!")
                                st.rerun()
                    with c_m2:
                        if st.button("찜 해제", key=f"btn_rem_fav_{fav['product_id']}_{fav_idx}", use_container_width=True):
                            db_manager.remove_favorite(current_user['user_id'], fav['product_id'], db_pass=db_p)
                            st.success("찜한 상품에서 삭제되었습니다.")
                            st.rerun()
        else:
            st.info(f"{current_user['nickname']}님의 찜한 상품이 아직 없습니다. 상품 검색 후 관심 상품을 추가해 보세요!")

import re

def calculate_unit_price(title, price):
    """제목에서 수량/용량(개, 캔, kg, ml 등)을 감지하여 1개당/단가 계산"""
    try:
        match = re.search(r'(\d+)\s*(개|캔|팩|병|봉|세트|입)', title)
        if match:
            count = int(match.group(1))
            if count > 1:
                unit_p = int(price / count)
                return f"1{match.group(2)}당 {unit_p:,}원 (총 {count}{match.group(2)})"
        
        match_cap = re.search(r'(\d+(?:\.\d+)?)\s*(kg|g|ml|l)', title, re.IGNORECASE)
        if match_cap:
            val = float(match_cap.group(1))
            unit = match_cap.group(2).lower()
            if unit == 'g' and val > 0:
                p_100g = int((price / val) * 100)
                return f"100g당 {p_100g:,}원"
            elif unit == 'kg' and val > 0:
                p_1kg = int(price / val)
                return f"1kg당 {p_1kg:,}원"
            elif unit == 'ml' and val > 0:
                p_100ml = int((price / val) * 100)
                return f"100ml당 {p_100ml:,}원"
            elif unit == 'l' and val > 0:
                p_1l = int(price / val)
                return f"1L당 {p_1l:,}원"
    except Exception:
        pass
    return "-"

with tab3:
    st.markdown("<h4 style='margin-bottom:1rem; color:#0F172A; font-weight:800;'>상품 가격 추세 비교</h4>", unsafe_allow_html=True)
    
    # 4대 고대비 브랜드 라인 테마 컬러
    CMP_COLORS = ["#115DCE", "#10B981", "#F59E0B", "#8B5CF6"]
    
    compare_list = st.session_state.get('compare_items', [])
    df_products = get_all_products()

    # 비교함 항목과 수집 DB 항목 통합
    title_to_item = {}
    for item in compare_list:
        title_to_item[item['title']] = item

    if not df_products.empty:
        for _, row in df_products.iterrows():
            if row['title'] not in title_to_item:
                p_hist = get_price_history(row['product_id'])
                latest_p = int(p_hist['price'].iloc[-1]) if not p_hist.empty else 0
                title_to_item[row['title']] = {
                    'product_id': row['product_id'],
                    'title': row['title'],
                    'lprice': row['current_price'] if 'current_price' in row else latest_p,
                    'spec_tags': []
                }

    if title_to_item:
        all_titles = list(title_to_item.keys())
        default_selected = [x['title'] for x in compare_list[:4]] if compare_list else []
        
        selected_titles = st.multiselect("비교할 상품 선택 (최대 4개)", options=all_titles, default=default_selected, max_selections=4)
        
        if selected_titles:
            # 조회 기간 필터 (1개월, 3개월, 6개월, 1년, 전체 - 기본 3개월 index=1)
            timeframe_cmp = st.radio("조회 기간", ["1개월", "3개월", "6개월", "1년", "전체"], index=1, horizontal=True, key="cmp_timeframe_radio")
            days_map_cmp = {"1개월": 30, "3개월": 90, "6개월": 180, "1년": 365, "전체": None}
            selected_days_cmp = days_map_cmp[timeframe_cmp]

            fig_compare = go.Figure()
            table_rows = []

            for idx, title in enumerate(selected_titles):
                item = title_to_item[title]
                pid = item['product_id']
                color = CMP_COLORS[idx % len(CMP_COLORS)]
                
                df_p = get_price_history(pid)
                if df_p.empty or 'collected_at' not in df_p.columns or len(df_p) < 3:
                    df_p = collector.generate_mock_price_history(pid, item['lprice'])
                    if df_p is None or df_p.empty:
                        df_p = pd.DataFrame(columns=['price', 'collected_at'])
                
                # 기간 필터링
                if selected_days_cmp is not None and not df_p.empty and 'collected_at' in df_p.columns and df_p['collected_at'].notna().any():
                    max_date = df_p['collected_at'].max()
                    cutoff_date = max_date - pd.Timedelta(days=selected_days_cmp)
                    df_p_plot = df_p[df_p['collected_at'] >= cutoff_date]
                else:
                    df_p_plot = df_p
                
                fig_compare.add_trace(go.Scatter(
                    x=df_p_plot['collected_at'], 
                    y=df_p_plot['price'], 
                    mode='lines+markers', 
                    name=title[:25],
                    line=dict(color=color, width=3),
                    marker=dict(size=5, color=color),
                    hovertemplate='%{x}<br>최저가: %{y:,.0f}원<extra></extra>'
                ))

                # 핵심 스펙 또는 단가 계산
                unit_str = calculate_unit_price(title, item['lprice'])
                spec_tags = item.get('spec_tags', [])
                if unit_str != "-":
                    spec_info = f"<span style='color:#115DCE; font-weight:700;'>{unit_str}</span>"
                elif spec_tags:
                    spec_info = f"<span style='color:#334155;'>{' / '.join(spec_tags[:3])}</span>"
                else:
                    spec_info = "<span style='color:#94A3B8;'>기본 모델</span>"

                # AI 가격 분석 평가 배지
                avg_p = df_p['price'].mean() if not df_p.empty else item['lprice']
                min_p = df_p['price'].min() if not df_p.empty else item['lprice']
                cur_p = item['lprice']
                
                if cur_p <= min_p * 1.02:
                    eval_badge = '<span style="background:#DCFCE7; color:#15803D; padding:0.2rem 0.6rem; border-radius:4px; font-weight:800; font-size:0.85rem;">역대 최저가</span>'
                elif cur_p < avg_p:
                    eval_badge = '<span style="background:#E0F2FE; color:#0369A1; padding:0.2rem 0.6rem; border-radius:4px; font-weight:800; font-size:0.85rem;">평균 이하 (구매 추천)</span>'
                else:
                    eval_badge = '<span style="background:#FEF2F2; color:#B91C1C; padding:0.2rem 0.6rem; border-radius:4px; font-weight:800; font-size:0.85rem;">평균 이상 (보류 권장)</span>'

                table_rows.append({
                    "구분": f'<span style="color:{color}; font-weight:800;">● 상품 {idx+1}</span>',
                    "상품명": title,
                    "현재 최저가": f"<b>{item['lprice']:,}원</b>",
                    "핵심 스펙 / 단가": spec_info,
                    "AI 가격 평가": eval_badge
                })

            fig_compare.update_layout(
                margin=dict(l=0, r=0, t=20, b=0),
                hovermode="x unified", height=420,
                plot_bgcolor='#FFFFFF', paper_bgcolor='#FFFFFF',
                xaxis=dict(showgrid=True, gridcolor='#F1F5F9'), yaxis=dict(showgrid=True, gridcolor='#F1F5F9'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_compare, use_container_width=True)

            # 핵심 스펙 및 가격 평가 요약 비교표
            st.markdown("<h5 style='margin:1.5rem 0 0.8rem 0; color:#0F172A; font-weight:800;'>상품별 스펙 및 AI 가격 평가 비교표</h5>", unsafe_allow_html=True)
            df_table = pd.DataFrame(table_rows)
            st.markdown(df_table.to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.info("비교할 상품이 선택되지 않았습니다. [상품검색] 탭에서 원하는 상품의 [+ 비교함 담기] 버튼을 누르시거나, 위 드롭다운에서 비교할 상품을 검색/선택해 보세요!")
    else:
        st.info("비교함에 담긴 상품 또는 수집된 상품 데이터가 없습니다. 상품 검색 결과에서 [+ 비교함 담기] 버튼을 클릭해 보세요!")
