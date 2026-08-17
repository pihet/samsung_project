import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

output_dir = os.path.dirname(os.path.abspath(__file__))
preview_path = os.path.join(output_dir, "eda_slide_preview.png")

fig, ax = plt.subplots(figsize=(16, 9), dpi=180)
ax.set_xlim(0, 16)
ax.set_ylim(0, 9)
ax.axis('off')

# 전체 배경
bg = patches.Rectangle((0, 0), 16, 9, color='#F8FAFC')
ax.add_patch(bg)

# 상단 타이틀 뱃지
badge = patches.Rectangle((0.8, 7.8), 0.7, 0.6, color='#115DCE')
ax.add_patch(badge)
ax.text(1.15, 8.1, '11', color='white', fontsize=18, fontweight='bold', ha='center', va='center', fontfamily='Malgun Gothic')

# 상단 타이틀 텍스트
ax.text(1.7, 8.1, '탐색적 데이터 분석 (EDA) — 시계열 특성 및 모델링 근거 도출', color='#0F172A', fontsize=20, fontweight='bold', va='center', fontfamily='Malgun Gothic')

# 상단 구분선
ax.plot([0.8, 15.2], [7.5, 7.5], color='#CBD5E1', lw=1.5)

# 3개 카드 영역
cards = [
    {
        'x': 0.8, 'w': 4.4, 'num': '01', 'title': '주간 계절성 & 자기상관',
        'badge': 'Lag 7 자기상관 r = 0.9057', 'b_color': '#E11D48',
        'img': os.path.join(output_dir, 'eda_chart1_seasonal.png'),
        'bullets': [
            '• Lag 7에서 0.9057의 강한 자기상관 관측',
            '• 요일별 분석 결과 주말(금~일) 2~4% 특가 집중',
            '• [모델 반영]: 7일 주기 계절성 가중치 적용'
        ]
    },
    {
        'x': 5.6, 'w': 4.4, 'num': '02', 'title': '7일 이동 변동성 탐색',
        'badge': 'Rolling Volatility 분석', 'b_color': '#8B5CF6',
        'is_table': True,
        'bullets': [
            '• 7일 Rolling Std로 단발성 튐 vs 지속 추세 분리',
            '• 정상 변동폭(±1.5%) 초과 급변동 스파이크 감지',
            '• [전처리 반영]: 2.5×IQR 완화 기준 수립 근거'
        ]
    },
    {
        'x': 10.4, 'w': 4.4, 'num': '03', 'title': 'ADF + KPSS 정상성 검정',
        'badge': '1차 차분 후 100% 정상성 확보', 'b_color': '#10B981',
        'img': os.path.join(output_dir, 'eda_chart2_stationarity.png'),
        'bullets': [
            '• 원시 시계열: ADF p=0.8978 (비정상)',
            '• 1차 차분 시계열: ADF p=0.0000 (정상)',
            '• [모델 반영]: Auto-ARIMA d=1 차분 채택'
        ]
    }
]

for c in cards:
    x = c['x']
    w = c['w']
    # 카드 외곽
    c_box = patches.FancyBboxPatch((x, 0.6), w, 6.5, boxstyle="round,pad=0.02,rounding_size=0.15", facecolor='white', edgecolor='#E2E8F0', lw=1.5)
    ax.add_patch(c_box)
    
    # 카드 상단 헤더
    h_box = patches.Rectangle((x, 6.45), w, 0.65, color='#1E293B')
    ax.add_patch(h_box)
    ax.text(x + 0.2, 6.77, f"{c['num']}  {c['title']}", color='white', fontsize=12.5, fontweight='bold', va='center', fontfamily='Malgun Gothic')
    
    # 뱃지
    b_tag = patches.FancyBboxPatch((x + 0.2, 5.85), w - 0.4, 0.45, boxstyle="round,pad=0.02,rounding_size=0.08", facecolor='#F1F5F9', edgecolor=c['b_color'], lw=1.2)
    ax.add_patch(b_tag)
    ax.text(x + w/2, 6.07, f"★ {c['badge']}", color=c['b_color'], fontsize=10.5, fontweight='bold', ha='center', va='center', fontfamily='Malgun Gothic')
    
    # 중간 비주얼 (이미지 또는 표)
    if 'img' in c and os.path.exists(c['img']):
        img_arr = plt.imread(c['img'])
        ax.imshow(img_arr, extent=[x + 0.2, x + w - 0.2, 3.7, 5.7], aspect='auto', zorder=5)
    elif c.get('is_table'):
        t_box = patches.Rectangle((x + 0.2, 3.8), w - 0.4, 1.8, facecolor='#F8FAFC', edgecolor='#CBD5E1', lw=1)
        ax.add_patch(t_box)
        ax.text(x + 0.4, 5.2, '구분', fontsize=10, fontweight='bold', color='#475569', fontfamily='Malgun Gothic')
        ax.text(x + w - 0.4, 5.2, '수치 / 진단 결과', fontsize=10, fontweight='bold', color='#475569', ha='right', fontfamily='Malgun Gothic')
        ax.plot([x + 0.3, x + w - 0.3], [4.9, 4.9], color='#CBD5E1', lw=0.8)
        
        ax.text(x + 0.4, 4.5, '평균 수집 간격', fontsize=9.5, color='#334155', fontfamily='Malgun Gothic')
        ax.text(x + w - 0.4, 4.5, '1.9일 (불규칙)', fontsize=9.5, fontweight='bold', color='#115DCE', ha='right', fontfamily='Malgun Gothic')
        
        ax.text(x + 0.4, 4.05, '최대 수집 공백', fontsize=9.5, color='#334155', fontfamily='Malgun Gothic')
        ax.text(x + w - 0.4, 4.05, '3.9일 (3일 보간 필요)', fontsize=9.5, fontweight='bold', color='#E11D48', ha='right', fontfamily='Malgun Gothic')

    # 하단 텍스트
    y_text = 3.2
    for b in c['bullets']:
        is_highlight = '[모델 반영]' in b or '[전처리 반영]' in b
        b_color = '#115DCE' if is_highlight else '#475569'
        weight = 'bold' if is_highlight else 'normal'
        ax.text(x + 0.2, y_text, b, color=b_color, fontsize=10, fontweight=weight, fontfamily='Malgun Gothic')
        y_text -= 0.65

plt.savefig(preview_path, dpi=180, bbox_inches='tight')
plt.close()
print("Preview generated at:", preview_path)
