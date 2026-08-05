# Project UI/UX Behavior Rules

## Product Card Selection & State Management Rules
1. **Initial Search State (초기 검색 상태)**:
   - When a new search is initiated or when no product has been selected, ALL product cards MUST be rendered with 100% bright white background and clean clear image (`background-color: #FFFFFF`, `opacity: 1.0`, `filter: none`).
2. **Search Reset Trigger (검색 실행 시 상태 초기화)**:
   - Whenever `search_clicked` (new query search) is executed, `st.session_state['selected_product']` MUST be deleted/cleared immediately so the new search results always start in the 100% bright default state.
3. **Single Item Selection Focus (단일 상품 선택 포커스)**:
   - ONLY when the user explicitly clicks `[가격 추세 분석]` on a product card, that specific product gets highlighted (`border: 3px solid #2563EB`, bright white), while other non-selected product cards get dimmed (`background-color: #0F172A`, `opacity: 0.35`, `filter: brightness(0.35)`).
