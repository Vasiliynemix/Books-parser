__doc__ = '\nФункции для парсинга интернет-магазина my-shop.ru.\n'

import math
import time
import traceback
from threading import Thread

import lxml.html
import lxml.html.clean

import web
from shops.BooksClass import BooksDownloadThread, PublishersDownloadThread
from logger_manager import create_logger

# BASE_URL = 'https://my-shop.ru'
SHOP = 'my-shop.ru'
BASE_URL = f"https://api.{SHOP}/cgi-bin/shop2.pl"
MAX_BOOKS_PER_PAGE = 40


class MyShopPublishers(PublishersDownloadThread):
    __doc__ = 'Класс для потока загрузки издательств с сайта my-shop.ru.'

    def __init__(self):
        super().__init__()

        # Superclass variables
        self.shop_name = SHOP
        self.main_func = self._run
        self.logger = create_logger(SHOP)

        # Own variables
        self.total_publishers = self.publishers = self.publishers_tag = None
        self.progress = 0

    def _run(self):
        """Загружает список издательств с сайта my-shop.ru"""
        # try:
        self.add_to_progress(1)
        self.create_session(BASE_URL, verify_ssl=True)
        self.add_to_progress(4)

        self.cat_params = {'q': 'catalogue', 'id': '1', 'sort': 'a', 'page': '1'}
        # Книги - "https://my-shop.ru/shop/catalogue/3/sort/a/page/1.html",
        # Учебники, учебная литература - "https://my-shop.ru/shop/catalogue/2665/sort/a/page/1.html",
        # Литература на иностранных языках- "https://my-shop.ru/shop/catalogue/3227/sort/a/page/1.html"
        categories = [3, 2665, 3227]

        all_brands = []
        for cat in categories:
            self.cat_params['id'] = cat
            response = web.get_html_page(BASE_URL, params=self.cat_params, session=self.session)
            all_brands += self.find_brands_recursion(all_brands, response.json())

        # Save to file and exit
        all_brands_list = [[a['title'], str(a['id'])] for a in all_brands]
        # all_brands_list.
        all_brands_str = sorted(list(set(["\tID=".join(a) for a in all_brands_list])))
        all_brands_list = [a.split("\tID=") for a in all_brands_str]

        self.progress_update.emit(95)

        names = [a[0] for a in all_brands_list]

        return names, all_brands_str

        # files.write_publishers(SHOP, all_brands_str)
        # self.progress_update.emit(100)
        # self.result.emit({'publishers': names})

        # except Exception as exception:
        #     self.error.emit(exception)

    def add_to_progress(self, value=1.0):
        self.progress += value
        self.progress_update.emit(self.progress)

    def find_brands_recursion(self, all_brands, response_json):
        # sub_links = [a['href'] for a in response.json()['subcategories']]
        if not response_json.get('filter'):
            a = 2
        filters = response_json['filter']
        prods = [f['values'] for f in filters if f.get('title') == 'производитель']
        if prods:
            prods = prods[0]
            # bomb = [a for a in prods[0] if "Бомбор" in a['title']]
            bomb = [a for a in prods if "[old" in a['title']]
            if bomb:
                for b in bomb:
                    prods.remove(b)
            return prods
        else:
            if response_json['subcategories']:
                sub_ids = [a['id'] for a in response_json['subcategories']]
                for sub_id in sub_ids:
                    self.cat_params['id'] = sub_id
                    if sub_id == 26812 or sub_id == '26812':
                        b = 2
                    sub_response = web.get_html_page(BASE_URL, params=self.cat_params, session=self.session)
                    if sub_response.status_code == 301:
                        red_url = sub_response.json()['redirect']
                        if "/shop/catalogue" in red_url:
                            red_id = red_url.split("/")[3]
                            self.cat_params['id'] = red_id
                            sub_response = web.get_html_page(BASE_URL, params=self.cat_params, session=self.session)
                        else:
                            TEST = 3

                    down_brands = self.find_brands_recursion(all_brands, sub_response.json())
                    all_brands += [d for d in down_brands if d not in all_brands]
                    # print("exit", sub_id, "from", sub_ids)
                    self.add_to_progress(1)

        return []


class MyShopBooks(BooksDownloadThread):
    __doc__ = 'Класс потока загрузки информации о книгах с сайта my-shop.ru.'

    def __init__(self, publisher, excel_filepath, images_dirpath, missing_images_dirpath,
                 publisher_id, publisher_name, ids):
        super().__init__(publisher, excel_filepath, images_dirpath, missing_images_dirpath)

        # Superclass variables
        self.shop_name = SHOP
        self.BASE_URL = BASE_URL
        self.main_func = self._run
        self.logger = create_logger(SHOP)

        # Own variables
        self.publisher_id = publisher_id
        self.publisher = publisher_name
        self.ids = ids

        self.session = None
        self.cleaner = lxml.html.clean.Cleaner(style=True)

    def _run(self):
        """Запускает поток загрузки информации о книгах по выбранному издательству с сайта."""
        # try:

        # Parse books
        params = {'q': 'producer', 'id': self.publisher_id, 'sort': 'a', 'page': '1'}
        response = web.get_html_page(BASE_URL, params=params, session=self.session)
        total_books_amount = response.json()['meta']['total']
        total_pages = math.ceil(total_books_amount / MAX_BOOKS_PER_PAGE)
        # print(f"Collected total books: {total_books_amount}, total pages: {total_pages}")

        self.progress_set.emit(total_books_amount)

        books_on_page = response.json()['products']
        books = []
        self.parse_books(books_on_page, books)

        for page in range(2, total_pages + 1):
            params['page'] = page
            response = web.get_html_page(BASE_URL, params=params, session=self.session)
            books_on_page = response.json()['products']
            self.parse_books(books_on_page, books)

        return books

    # def parse_books_old(self, books_on_page, page):
    #     books = []
    #     try:
    #         params = {'q': 'product', 'id': '1'}
    #
    #         # cd_exceptions = ['CD-ROM', 'DVD', 'Audio CD']
    #         # analyze book or not
    #         for i, book_link in enumerate(books_on_page):
    #             # emit book
    #             self.progress_update.emit(i + page * MAX_BOOKS_PER_PAGE)
    #
    #             product_id = book_link['product_id']
    #             # if not any([ex in str(book_link['ga_item']) for ex in cd_exceptions]) and product_id not in self.ids:
    #             if product_id not in self.ids:
    #                 # if book_details['isbn'] not in self.ids:  # Only for new books
    #                 params['id'] = product_id
    #                 response = web.get_html_page(BASE_URL, params=params, session=self.session)
    #                 product_info = response.json()['product']
    #
    #                 # parse book json
    #                 book_details = self.get_book_details(product_info)
    #                 books.append(book_details)
    #                 img_path = book_details['isbn'].strip() or product_id
    #                 self.get_book_cover_name = lambda _: img_path
    #                 self.download_book_cover(book_details)
    #     except Exception as e:
    #         # if books:
    #         #     files.write_books_to_excel(self.excel_filepath, books)
    #         err_text = Exception(f"ERROR: Ошибка во время парсинга книг издательства '{self.publisher}' - '{e}'\n"
    #                              f"{traceback.format_exc()}")
    #         self.logger.debug(err_text)
    #         self.error.emit(err_text)
    #         # raise e
    #
    #     # if books:
    #     #     files.write_books_to_excel(self.excel_filepath, books)
    #
    #     return books

    def parse_books(self, books_on_page, books):
        # A thread for every book on page
        threads_amount = len(books_on_page)
        threads = []

        for i in range(threads_amount):
            threads.append(Thread(target=self.parse_books_thread, args=(books, books_on_page[i], i)))
            threads[i].start()

        [thread.join() for thread in threads]

        return books

    def parse_books_thread(self, books, book_link, i):
        time.sleep(0.2 * i)  # for threads to start in order

        try:
            product_id = book_link['product_id']

            params = {'q': 'product', 'id': product_id}
            response = web.get_html_page(BASE_URL, params=params, session=self.session)
            product_info = response.json()['product']

            # parse book json
            book_details = self.get_book_details(product_info)
            books.append(book_details)
            # remaking get_book_cover_name for return needed img_path
            self.get_book_cover_name = lambda _: book_details['isbn'].strip() or product_id
            self.download_book_cover(book_details)

            # emit book
            self.progress_update.emit(len(books))

        except Exception as e:
            err_text = Exception(f"ERROR: Ошибка во время парсинга книг издательства '{self.publisher}' - '{e}'\n"
                                 f"{traceback.format_exc()}")
            self.logger.debug(err_text)
            # self.error.emit(err_text)
            # raise e

    def get_book_details(self, product_info: dict) -> dict:
        """Получает детальную информацию о книге из содержимого книги в магазине."""

        a = product_info
        book_details = {}

        # ISBN
        book_details['isbn'] = a['isbn'].replace("-", "") if a['isbn'] else " "
        # Название
        book_details['name'] = a.get('title', " ")
        # Серия
        book_details["series"] = self._find_val_in_json(a, 'about', ['серия'])
        # Производитель
        book_details["publisher"] = self._find_val_in_json(a, 'about', ['издательство', 'производитель'])
        # Авторы
        book_details["authors"] = self._find_val_in_json(a, 'about', ['автор', 'составител'])
        # Цена
        book_details['price'] = a.get('cost', " ")
        # # Жанр
        # book_details["category"] = val
        # Возрастные ограничения
        # Не брать в учет скобки и все то, что в них "18+ (нет данных)"
        book_details["age_category"] = self._find_val_in_json(a, 'characteristics', ['возрастная категория'])
        book_details["age_category"] = book_details["age_category"].split("(")[0].strip()
        # Обложка
        book_details["cover"] = self._find_val_in_json(a, 'characteristics', ['переплет'])
        # Язык
        # book_details["language"] = self._find_val_in_json(a, 'lang', [1], subkey='id')
        # book_details["language"] = a['lang'][0]['value'] if a['lang'] else " "
        book_details["language"] = ', '.join([str(la['value']) for la in a['lang']]) if a['lang'] else " "
        # "Количество страниц":
        book_details["pages"] = self._find_val_in_json(a, 'characteristics', ['количество страниц'])

        dimensions = self._find_val_in_json(a, 'characteristics', ['размеры'])
        # Размеры
        book_details["dimensions"] = dimensions
        # Длина
        book_details["length"] = dimensions.split("x")[0].replace("мм", "").strip() if dimensions else " "
        # Ширина
        book_details["width"] = dimensions.split("x")[1].replace("мм", "").strip() if dimensions else " "
        # Высота
        book_details["height"] = dimensions.split("x")[2].replace("мм", "").strip() if dimensions else " "
        # Вес
        book_details["weight"] = self._find_val_in_json(a, 'characteristics', ['вес'])
        # Класс
        book_details["grade"] = self._find_val_in_json(a, 'characteristics', ['класс'])
        # Тип бумаги
        # Не брать в учет скобки и все то, что в них "офсетная (60-220 г/м2)"
        book_details["paper"] = self._find_val_in_json(a, 'characteristics', ['тип бумаги'])
        book_details["paper"] = book_details["paper"].split("(")[0].strip()
        # Цвет
        book_details["color"] = self._find_val_in_json(a, 'characteristics', ['цвет'])
        # Описание
        raw_description = a.get('description', "")
        clean_description = self.clear_web_text(raw_description) if raw_description else " "
        book_details["description"] = clean_description
        # ID
        book_details["ID"] = a['product_id']
        # Страна изготовления
        book_details["country"] = self._find_val_in_json(a, 'characteristics', ['страна изготовления'])
        # Год
        book_details["year"] = a['manufacture_date'].replace("&nbsp;г.", "") if a['manufacture_date'] else " "
        # Вид товара (Формат)
        book_details["type"] = self._find_val_in_json(a, 'characteristics', ['тип материала'])
        # Img data
        img_exists = a['img'] and a['img'][0]
        if img_exists:
            book_details['image_url'] = "https://static2.my-shop.ru" + a['img'][0]
            book_details['missing image'] = False
        else:
            book_details['image_url'] = "https://studentsbook.net/bitrix/templates/aspro_mshop/images/no_photo_medium.png"
            book_details['missing image'] = True

        # image_url_raw = soup.find("div", "slides").find("img").get("src")
        # image_url = web.extract_filename_from_url(image_url_raw)
        # if "no_photo_medium.png" in image_url:
        #     book_details['missing image'] = True
        # else:
        #     book_details['image_url'] = BASE_URL + image_url_raw

        return book_details

    def clear_web_text(self, text):
        if not text:
            return text

        html = text
        doc = lxml.html.fromstring(html)
        doc = self.cleaner.clean_html(doc)
        return doc.text_content()

    def _find_val_in_json(self, json, submenu, search_objs):
        # found = [char for char in json[submenu] for so in search_objs if so == char[subkey] or so in char[subkey]]
        found = [char for char in json[submenu] for so in search_objs if so in char['name']]
        # removing duplicates if any
        non_dupes = []
        for f in found:
            if f not in non_dupes:
                non_dupes.append(f)
        # found = [dict(t) for t in {tuple(d.items()) for d in found}]
        if non_dupes:
            return ', '.join([str(v['value']) for v in non_dupes])
        else:
            return " "
