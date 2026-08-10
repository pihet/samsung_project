import requests
from bs4 import BeautifulSoup
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
    'Referer': 'https://prod.danawa.com/'
}

pcode = '103451483'
url = f'https://prod.danawa.com/info/?pcode={pcode}'
res = requests.get(url, headers=headers, timeout=10)
res.encoding = 'utf-8'

soup = BeautifulSoup(res.text, 'html.parser')

# Find all script tags containing ajax or price or getProduct
scripts = soup.select('script')
for s in scripts:
    txt = s.text
    if 'ajax' in txt.lower() or 'price' in txt.lower() or 'pcode' in txt.lower():
        matches = re.findall(r'https?://[^\s\'"]+|\/[a-zA-Z0-9_\-\/]+\.php[^\s\'"]*', txt)
        if matches:
            print("Found AJAX/API matches in script:")
            for m in matches[:10]:
                print("  ", m)

# Also check form actions or data attributes
elements = soup.select('[data-url], [action], [data-ajax]')
for el in elements:
    print("Found data-url / action:", el.name, el.get('data-url'), el.get('action'))
