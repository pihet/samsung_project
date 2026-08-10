import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
    'Referer': 'https://www.danawa.com/'
}
url = 'https://search.danawa.com/dsearch.php?query=' + requests.utils.quote('노트북')
res = requests.get(url, headers=headers, timeout=10)
res.encoding = 'utf-8'

soup = BeautifulSoup(res.text, 'html.parser')
prod_items = soup.select('.main_prodlist .prod_item, .prod_main_info')
print("Found prod_items:", len(prod_items))

for idx, p in enumerate(prod_items[:3]):
    p_id = p.get('id', '')
    title_el = p.select_one('.prod_name a')
    price_el = p.select_one('.price_sect strong')
    spec_el = p.select_one('.spec_list')
    img_el = p.select_one('.thumb_image img')
    
    title = title_el.text.strip() if title_el else "N/A"
    link = title_el.get('href') if title_el else ""
    price = price_el.text.strip() if price_el else "N/A"
    spec = spec_el.text.strip() if spec_el else ""
    img = img_el.get('data-src') or img_el.get('data-original') or img_el.get('src') if img_el else ""

    # Mall list parsing inside each product
    malls = []
    mall_lis = p.select('.deli_price_list li, .price_list li')
    for m in mall_lis:
        m_name_el = m.select_one('.txt_logo img, .img_logo img, img')
        m_name = m_name_el.get('alt') if (m_name_el and m_name_el.get('alt')) else (m.select_one('.txt_name').text.strip() if m.select_one('.txt_name') else '')
        m_price_el = m.select_one('.price, .txt_price, strong')
        m_price = m_price_el.text.strip() if m_price_el else ''
        m_link_el = m.select_one('a')
        m_link = m_link_el.get('href') if m_link_el else ''
        if m_name or m_price:
            malls.append({'name': m_name, 'price': m_price, 'link': m_link})

    print(f"\n--- Item #{idx+1} (ID: {p_id}) ---")
    print("Title:", title)
    print("Link:", link)
    print("Price:", price)
    print("Img:", img)
    print("Spec:", spec[:100].replace('\n', ' '))
    print("Malls count:", len(malls))
    for m in malls[:5]:
        print("  Mall:", m)
