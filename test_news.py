import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

query = '삼성전자 특징주'
url = f'https://search.naver.com/search.naver?where=news&query={quote(query)}'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
res = requests.get(url, headers=headers, timeout=5)
soup = BeautifulSoup(res.text, 'html.parser')

for a in soup.find_all('a'):
    text = a.text.strip()
    href = a.get('href', '')
    if len(text) > 10 and 'fender' in str(a.get('class', '')):
        print(f'텍스트: {text[:60]}')
        print(f'URL: {href}')
        print()
