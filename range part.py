import os
import shutil

import requests


params = { 'keypresses': '1', 'flags': '0', 'term': 'Вита'}
response = requests.get('https://api.my-shop.ru/cgi-bin/ajax/search.pl', params=params)
suggest = response.json()['suggest']
publishers = [s for s in suggest if s.get('type') == '13']
found = [p for p in publishers if p['value'] == "Вита-Нова"]

b = 2


json_data = {
    'f14_6': 'Вече',
    'f14_39': '0',
    'f14_16': '4',
    'next': '1',
    'sort': 'z',
    'page': '1',
}
params = json_data.copy()
params.update({'q': 'search'})


response = requests.post('https://api.my-shop.ru/cgi-bin/shop2.pl', params=params, json=json_data)
other = response.json()['other']
publishers = [o for o in other if o['title'] == 'В производителях'][0]
items = [p for p in publishers['items']]
href_found = [i['href'] for i in items if i['title'] == "Вече"]


# import web
#
# for i in range(10):
#     URL = f"https://static2.my-shop.ru/sitemap/{i+1:=02d}.xml"
#     name = URL.split("/")[-1]
#     # load main XML file
#     headers = {'User-Agent': "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)"}
#     req = web.get_html_page(URL, headers=headers)
#
#     with open(name, "w", encoding="utf-8") as file:
#         file.write(req.text)



# with open("studentsbook_temp.xml", "r", encoding="utf-8") as from_file:
#     with open("studentsbook.xml.xml", "w", encoding="utf-8") as to_file:
#         first_line = from_file.readline()
#         new_line = first_line.replace('encoding="windows-1251"', 'encoding="utf-8"')
#         to_file.write(new_line)
#         shutil.copyfileobj(from_file, to_file)
#
# # delete first file
# os.remove("studentsbook_temp.xml")
