import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
    'Referer': 'https://www.danawa.com/'
}

url = 'https://search.danawa.com/dsearch.php?query=' + requests.utils.quote('LG 2026 그램')
res = requests.get(url, headers=headers, timeout=10)
res.encoding = 'utf-8'

soup = BeautifulSoup(res.text, 'html.parser')
prod_items = soup.select('.main_prodlist .prod_item, .prod_main_info')

print(f"Total prod items: {len(prod_items)}")

if prod_items:
    item = prod_items[0]
    print("--- FIRST ITEM HTML ---")
    # Print elements inside price_sect and all list elements inside item
    print("Item ID:", item.get('id'))
    price_sect = item.select_one('.price_sect')
    print("Price sect HTML:")
    print(price_sect.prettify() if price_sect else "No price_sect")
    
    print("\nAll ul / li / div classes inside item:")
    for el in item.find_all(['ul', 'div', 'dl', 'table'], recursive=True):
        classes = el.get('class', [])
        if classes:
            print(f"  Tag: {el.name}, Class: {classes}")

    # Look for any shop links or prices
    shop_links = item.select('a')
    print(f"\nTotal links count: {len(shop_links)}")
    for a in shop_links:
        href = a.get('href', '')
        txt = a.text.strip()
        img = a.select_one('img')
        img_alt = img.get('alt') if img else ''
        if 'pcode' in href or 'link.danawa' in href or 'click' in href or img_alt or any(c in txt for c in ['원', '쿠팡', '11번가', 'G마켓', '옥션', 'SSG', '스마트스토어']):
            print(f"  Link: txt='{txt[:30]}', alt='{img_alt}', href='{href[:80]}'")
