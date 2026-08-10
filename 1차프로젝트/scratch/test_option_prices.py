import requests
from bs4 import BeautifulSoup
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
    'Referer': 'https://www.danawa.com/'
}

url = 'https://search.danawa.com/dsearch.php?query=' + requests.utils.quote('LG 2026 그램')
res = requests.get(url, headers=headers, timeout=10)
res.encoding = 'utf-8'

soup = BeautifulSoup(res.text, 'html.parser')
prod_items = soup.select('.main_prodlist .prod_item')

print(f"Total prod_item count: {len(prod_items)}")

for idx, p in enumerate(prod_items[:3]):
    name_el = p.select_one('.prod_name a')
    price_el = p.select_one('.price_sect strong')
    if not name_el or not price_el:
        continue

    title = name_el.text.strip()
    orig_link = name_el.get('href', '')
    pcode_match = re.search(r'pcode=(\d+)', orig_link)
    pcode = pcode_match.group(1) if pcode_match else ''

    price_str = price_el.text.replace(',', '').replace('원', '').strip()
    lprice = int(price_str) if price_str.isdigit() else 0

    print(f"\n--- Product #{idx+1}: {title} (pcode: {pcode}, Min Price: {lprice:,}원) ---")

    # Check .prod_pricelist li
    price_lis = p.select('.prod_pricelist li')
    sub_prices = []
    for li in price_lis:
        # Check text (e.g. SSD 512GB, SSD 1TB, etc.)
        mem_el = li.select_one('.memory_sect .text, .memory_sect, .txt_name')
        mem_txt = mem_el.text.strip() if mem_el else ''
        
        prc_el = li.select_one('.price_sect strong, .price_sect a')
        prc_str = prc_el.text.replace(',', '').replace('원', '').strip() if prc_el else ''
        
        a_el = li.select_one('a')
        a_href = a_el.get('href') if a_el else ''
        sub_pcode_match = re.search(r'pcode=(\d+)', a_href) if a_href else None
        sub_pcode = sub_pcode_match.group(1) if sub_pcode_match else pcode
        sub_link = f"https://prod.danawa.com/info/?pcode={sub_pcode}" if sub_pcode else f"https://prod.danawa.com/info/?pcode={pcode}"

        if prc_str.isdigit():
            sp = int(prc_str)
            sub_prices.append({
                'name': mem_txt if mem_txt else "다나와 최저가",
                'price': sp,
                'link': sub_link
            })

    print(f"Sub prices found ({len(sub_prices)}):")
    for sp in sub_prices:
        print(f"  Option/Price: {sp['name']} -> {sp['price']:,}원 (link: {sp['link']})")
