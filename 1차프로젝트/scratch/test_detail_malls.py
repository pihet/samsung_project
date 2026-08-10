import requests
from bs4 import BeautifulSoup
import json
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
    'Referer': 'https://www.danawa.com/'
}

# Test Danawa product detail page HTML
pcode = '103451483'
url = f'https://prod.danawa.com/info/?pcode={pcode}'
res = requests.get(url, headers=headers, timeout=10)
res.encoding = 'utf-8'

soup = BeautifulSoup(res.text, 'html.parser')
print(f"Product detail page status: {res.status_code}")

# Danawa product detail page has mall list inside #blog_content or .high_list or .diff_list or .low_price or .price_cmp
mall_rows = soup.select('.high_list tr, .diff_list tr, .price_cmp tr, .list_price tbody tr, .tbl_price tbody tr, .deli_price_list li, .mall_list li')
print(f"Found mall_rows count: {len(mall_rows)}")

# Let's inspect all price elements on product detail page
prices = soup.select('.prc_c, .txt_pr, .price, .num_pr, .tx_c, .low_price .num, .prc_t')
print(f"Found price elements: {len(prices)}")
for p in prices[:10]:
    print(" Price element:", p.text.strip(), "Parent class:", p.parent.get('class', []))

# Let's also check Danawa AJAX price comparison API endpoint!
# Danawa uses an internal AJAX endpoint for product price list:
# https://prod.danawa.com/info/ajax/getProductDesc.php?pcode=... or blog_content
ajax_url = f'https://prod.danawa.com/info/ajax/getProductDesc.php?pcode={pcode}'
ajax_res = requests.get(ajax_url, headers=headers, timeout=10)
print(f"Ajax res status: {ajax_res.status_code}, len: {len(ajax_res.text)}")
