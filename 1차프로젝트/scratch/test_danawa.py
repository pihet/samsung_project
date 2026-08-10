import requests
from bs4 import BeautifulSoup
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8'
}
url = 'https://search.danawa.com/dsearch.php?query=' + requests.utils.quote('갤럭시 s24')
res = requests.get(url, headers=headers, timeout=10)
print('Status:', res.status_code)
soup = BeautifulSoup(res.text, 'html.parser')

items = soup.select('.prod_main_info, .prod_item')
print('Found prod count:', len(items))

parsed_data = []
for i, item in enumerate(items[:5]):
    # Skip ad items or non-product items if any
    p_id = item.get('id', '')
    name_el = item.select_one('.prod_name a')
    price_el = item.select_one('.price_sect strong')
    img_el = item.select_one('.thumb_image img')
    spec_el = item.select_one('.spec_list')
    
    # Mall list parsing
    mall_items = []
    # Danawa lists mall price items inside .deli_price or .rank_one or .price_list
    m_list = item.select('.price_list li, .deli_price_list li, .rank_one')
    for m in m_list:
        m_img = m.select_one('img')
        m_txt = m.select_one('.txt_name, .logo, .txt_logo, span')
        m_name = m_img.get('alt') if (m_img and m_img.get('alt')) else (m_txt.text.strip() if m_txt else '')
        m_price_el = m.select_one('.price, .txt_price, strong, .price_sect')
        m_price = m_price_el.text.strip() if m_price_el else ''
        m_link_el = m.select_one('a')
        m_link = m_link_el.get('href') if m_link_el else ''
        if m_name or m_price:
            mall_items.append({'mall': m_name, 'price': m_price, 'link': m_link})

    if name_el:
        title = name_el.text.strip()
        link = name_el.get('href', '')
        img_url = ""
        if img_el:
            img_url = img_el.get('data-src') or img_el.get('data-original') or img_el.get('src') or ""
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
        
        parsed_data.append({
            'id': p_id,
            'title': title,
            'link': link,
            'price': price_el.text.strip() if price_el else '',
            'img': img_url,
            'spec': spec_el.text.strip() if spec_el else '',
            'malls': mall_items
        })

print(json.dumps(parsed_data, ensure_ascii=False, indent=2))
