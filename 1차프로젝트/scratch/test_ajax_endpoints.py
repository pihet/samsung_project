import requests
from bs4 import BeautifulSoup
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
    'Referer': 'https://www.danawa.com/'
}

# Danawa AJAX price list URL
# On Danawa, the price comparison table is fetched via:
# https://prod.danawa.com/info/ajax/getProductDesc.php?pcode=... OR
# https://prod.danawa.com/info/ajax/getPriceCompareList.php?pcode=...

pcodes = ['103451483', '96711431', '63138947']

for pcode in pcodes:
    print(f"\n================ PCODE {pcode} ================")
    
    # Try fetching price compare AJAX
    urls = [
        f'https://prod.danawa.com/info/ajax/getProductDesc.php?pcode={pcode}',
        f'https://prod.danawa.com/info/ajax/getPriceCompareList.php?pcode={pcode}&cate1Code=11&cate2Code=112758',
        f'https://prod.danawa.com/info/?pcode={pcode}'
    ]
    
    for url in urls:
        r = requests.get(url, headers=headers, timeout=5)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Search for seller names and prices
        malls = soup.select('.logo_over, .txt_logo, .img_logo, .logo, .mall, .deli_price_list li, .diff_list tr, .high_list tr, .rank_one, .sub_price_sect')
        prices = soup.select('.price, .prc_c, .txt_pr, .num_pr, strong')
        
        print(f"URL: {url} -> status: {r.status_code}, len: {len(r.text)}, malls_found: {len(malls)}")
        
        # Check if any text mentions known malls
        for m_name in ['쿠팡', '11번가', 'G마켓', '옥션', 'SSG', '스마트스토어', '티몬', '위메프', '하이마트', '전자랜드', '다나와']:
            if m_name in r.text:
                print(f"   Mentions '{m_name}' in page text!")
