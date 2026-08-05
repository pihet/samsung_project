import urllib.request
import urllib.parse
import json

client_id = '72zv8pmji6'
client_secret = '70xiSylythvjoa3JBpRmEcqssrFFD7cQziEZJ0mH'
query = 'test'
enc_text = urllib.parse.quote(query)

url = f"https://openapi.naver.com/v1/search/shop.json?query={enc_text}&display=10"

print("--- Testing with X-Naver-* headers ---")
request1 = urllib.request.Request(url)
request1.add_header("X-Naver-Client-Id", client_id)
request1.add_header("X-Naver-Client-Secret", client_secret)

try:
    response1 = urllib.request.urlopen(request1)
    print("SUCCESS")
    print(response1.read().decode('utf-8')[:200])
except Exception as e:
    if hasattr(e, 'read'):
        print(e, e.read().decode('utf-8'))
    else:
        print(e)

print("\n--- Testing with X-NCP-APIGW-API-KEY-* headers ---")
request2 = urllib.request.Request(url)
request2.add_header("X-NCP-APIGW-API-KEY-ID", client_id)
request2.add_header("X-NCP-APIGW-API-KEY", client_secret)

try:
    response2 = urllib.request.urlopen(request2)
    print("SUCCESS")
    print(response2.read().decode('utf-8')[:200])
except Exception as e:
    if hasattr(e, 'read'):
        print(e, e.read().decode('utf-8'))
    else:
        print(e)
