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
prod = soup.select_one('.main_prodlist .prod_item')

if prod:
    print("--- PROD PRICELIST HTML ---")
    pricelist = prod.select_one('.prod_pricelist')
    if pricelist:
        print(pricelist.prettify())
    else:
        print("No .prod_pricelist found")

    print("\n--- ALL LIST ITEMS OR LINKS INSIDE PROD ---")
    for a in prod.select('a'):
        txt = a.text.strip().replace('\n', ' ')
        href = a.get('href', '')
        if txt or 'pcode' in href:
            print(f"a tag: text='{txt[:40]}', href='{href[:80]}'")
