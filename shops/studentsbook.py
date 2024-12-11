__doc__ = '\nФункции для парсинга интернет-магазина studentsbook.net.\n'

import os
import re
import threading
import time
import traceback
from urllib.parse import urlsplit

import cyrtranslit
import requests.exceptions
from PyQt6.QtCore import pyqtSignal

import exceptions
import files
import web
from shops.BooksClass import PublishersDownloadThread, BooksDownloadThread
from logger_manager import create_logger

SHOP = 'studentsbook.net'
BASE_URL = f'https://{SHOP}'
find_url = BASE_URL + "/catalog/?q={{}}&s=%D0%9F%D0%BE%D0%B8%D1%81%D0%BA"  # &s=Поиск


class StudentsbookPublishers(PublishersDownloadThread):
    __doc__ = 'Класс для потока загрузки издательств с сайта studentsbook.net.'
    soup_data_parsed = pyqtSignal(list)

    def __init__(self):
        super().__init__()

        # Superclass variables
        self.shop_name = SHOP
        self.main_func = self._run
        self.logger = create_logger(SHOP)

        # Own variables
        self.total_publishers = self.publishers = self.publishers_tag = None
        # self.soup = studentsbook_soup

    def _run(self):
        """Загружает список издательств с сайта studentsbook.net."""
        self.session = web.create_session_by_url(BASE_URL, yandex=True, verify_ssl=False)

        self.progress_update.emit(1)
        self.load_site_xml()
        self.progress_update.emit(30)
        self.parse_xml_file()
        self.progress_update.emit(60)
        self.get_total_offers()
        self.progress_update.emit(70)
        self.get_total_categories()
        self.progress_update.emit(80)
        self.get_total_publishers()
        self.progress_update.emit(90)

        if self.offers_count == 0:
            raise exceptions.WebsiteStructureError(f"На сайте {SHOP} не найдены издательства.")

        self.soup_data_parsed.emit([self.offers, self.categories_tag])

        return [self.total_publishers_info]

    def get_total_offers(self):
        self.offers = self.soup.find_all("offer")
        self.offers_count = len(self.offers)

    def get_total_categories(self):
        self.categories_tag = self.soup.find_all("category")
        self.categories = tuple([c.text for c in self.categories_tag])
        self.total_categories = set(c for c in self.categories)

    def parse_xml_file(self):
        content = files.get_correct_xml_content(SHOP)
        self.soup = web.get_soup_from_content(content, parser='xml')

    def get_total_publishers(self):
        self.publishers_tag = [o.find("publisher") for o in self.offers if o.find("publisher").text]
        self.publishers = tuple([p.text for p in self.publishers_tag])

        # self.total_publishers = set(p for p in self.publishers)
        # self.total_publishers_info = sorted([f"{p} [{self.publishers.count(p)}]" for p in self.total_publishers])
        # return 0

        pub_set = dict()
        for p in self.publishers:
            if p.lower() not in [k.lower() for k in pub_set.keys()]:
                pub_set.update({p: 1})
            else:
                for k in pub_set.keys():
                    if p.lower() == k.lower():
                        pub_set[k] += 1

        self.total_publishers = sorted(pub_set)
        self.total_publishers_info = [f"{n} [{a}]" for n, a in list(sorted(pub_set.items()))]

    def load_site_xml(self):
        # load main XML file
        # request = web.get_html_page("https://studentsbook.net/robots.txt", headers=headers)
        request = web.get_html_page(f"{BASE_URL}/bitrix/catalog_export/yandex_yml.php", session=self.session)

        files.save_xml_to_file(SHOP, request)


class StudentsbookBooks(BooksDownloadThread):
    __doc__ = 'Класс потока загрузки информации о книгах с сайта studentsbook.net.'

    def __init__(self, publisher, excel_filepath, images_dirpath, missing_images_dirpath, soup_data_parsed):
        super().__init__(publisher, excel_filepath, images_dirpath, missing_images_dirpath, verify_ssl=False)

        # Superclass variables
        self.shop_name = SHOP
        self.BASE_URL = BASE_URL
        self.main_func = self._run
        self.logger = create_logger(SHOP)

        # Own variables
        self.offers, self.categories_tag = soup_data_parsed
        # self.soup = soup_data_parsed
        # self.isbn = isbn

        self.session = None

        self.MAX_RETRY_ATTEMPTS = 50
        self.LOG_FILE_PATH = "parser.log"

    def _run(self):
        """
        Запускает поток загрузки информации о книгах по выбранному издательству
        с сайта studentsbook.net.
        """
        # progress_values = {'subcatalog_number': 0, 'book_number': 0}

        self.get_offers_by_publisher(self.publisher.lower())

        self.progress_set.emit(self.offers_by_publisher_count)

        books = self.parse_books()

        return books

    def parse_books(self):
        books = []
        # A thread for every N book
        threads_amount = min(20, self.offers_by_publisher_count)
        threads = []

        for i in range(threads_amount):
            threads.append(threading.Thread(target=self.parse_books_thread, args=(i, threads_amount, books)))
            threads[i].start()

        [t.join() for t in threads]

        return books

    def parse_books_thread(self, thread_number, threads_amount, books):
        time.sleep(thread_number / 2)  # for threads to start in order

        for i, offer in enumerate(self.offers_by_publisher):
            if i % threads_amount != thread_number:
                continue

            try:
                xml_book = self.extract_book_details_xml(offer)
                # if xml_book['isbn'] not in self.isbn:  # Only for new books
                raw_url = offer.find("url").text

                # get book details
                book_details = self.try_to_get_book_details(raw_url, xml_book)
                if not book_details:
                    # No such a book
                    self.logger.debug(f"WARNING: Книга isbn:{xml_book['isbn']} по адресу {raw_url} "
                                      f"не найдена на сайте. Хотя она указана в XML файле.")
                    continue

                books.append(book_details)
                if book_details.get("url") is None:
                    book_details["url"] = raw_url

                if not book_details.get("image_url"):
                    book_details["image_url"] = "https://studentsbook.net/bitrix/templates/aspro_mshop/images/no_photo_medium.png"
                    book_details["missing image"] = True

                self.download_book_cover(book_details)

                self.progress_update.emit(len(books))
            except Exception as e:
                # if books:
                #     files.write_books_to_excel(self.excel_filepath, books)
                err_text = f"ERROR: Ошибка при загрузке книги {xml_book['isbn']} по адресу {raw_url}. \n" \
                           f"Ошибка: {traceback.format_exc()}"
                self.logger.debug(f"RETRY Книга {xml_book['isbn']} адрес {raw_url}")
                self.logger.debug(err_text)
                # self.error.emit(e)
                # raise e

    def get_image_url(self, book_details):
        image_url = book_details['image_url']
        if 'resize_cache' in image_url:
            splited = image_url.split("/")  # [splited.pop(i) for i in [4,7]]
            splited.pop(4)
            splited.pop(6)
            image_url = "/".join(splited)
        return image_url

    def try_to_get_book_details(self, raw_url, xml_book):
        try:  # raw url
            # print(f"xml_book['description']: {xml_book['description']}")
            book_details = self.get_book_details_url(raw_url)
            # print(f"book_details['description']: {book_details.get('description')}")
        except requests.exceptions.HTTPError as e:
            authors_raw = cyrtranslit.to_latin(xml_book["authors"], "ru")
            authors = authors_raw.replace(".", "_").replace(" ", "_").lower()

            url_split = urlsplit(raw_url)
            url_path = url_split.path.split("/")
            url_path[-2] = authors + url_path[-2]
            new_path = "/".join(url_path) + "?" + url_split.query
            authors_url = BASE_URL + new_path

            try:  # with author name
                book_details = self.get_book_details_url(authors_url)
            except requests.exceptions.HTTPError as e:
                # find in site
                last_chance_url = self.find_book_url_by_xml(xml_book)
                if last_chance_url:
                    last_chance_url = last_chance_url + "?" + urlsplit(raw_url).query
                    book_details = self.get_book_details_url(last_chance_url)
                else:  # No such a book
                    return False

        return book_details

    def get_offers_by_publisher(self, publisher):
        self.offers_by_publisher = [o for o in self.offers if o.find("publisher").text.lower() == publisher]
        self.offers_by_publisher_count = len(self.offers_by_publisher)

    def get_category_recursion(self, category_id):
        """ Рекурсивно получает полное название категории """
        cat = [c for c in self.categories_tag if c['id'] == str(category_id)][0]
        try:
            parent = cat['parentId']
            return self.get_category_recursion(parent) + "-" + cat.text
        except KeyError:
            return cat.text

    def extract_book_details_xml(self, offer):
        """ Извлекает информацию о книге из тега <offer> """
        book_details = {}
        exists = [c for c in offer.contents if c.text != "\n"]

        # book_details["url"] = exists[0].text
        book_details["price"] = exists[1].text
        book_details["currency"] = exists[2].text
        book_details["category"] = self.get_category_recursion(exists[3].text)
        book_details["image_url"] = exists[4].text
        book_details["authors"] = exists[5].text
        book_details["name"] = exists[6].text
        book_details["publisher"] = exists[7].text
        # book_details["series"] = exists[8].text
        book_details["year"] = exists[9].text
        book_details["isbn"] = exists[10].text
        # book_details["barcode"] = exists[11].text
        # book_details["age_category"] = exists[12].text
        book_details["type"] = exists[11].text
        book_details["pages"] = exists[12].text
        try:
            book_details["description"] = exists[13].text
        except IndexError:
            book_details["description"] = " "

        book_details['missing image'] = False

        return book_details

    def find_book_url_by_xml(self, xml_book):
        url = find_url.replace("{{}}", xml_book['isbn'])

        req, soup = web.get_html_page(url, session=self.session, with_soup=True)

        block_search = soup.find("div", "catalog block search")
        if not block_search:
            return None

        book_links = block_search.find_all("a")
        if not book_links:
            return None

        link = BASE_URL + book_links[1]['href']
        return link

    def get_book_details_url(self, url: str) -> dict:
        """
        Получает детальную информацию о книге из содержимого
        html-страницы книги в магазине studentsbook.net.
        """
        req, soup = web.get_html_page(url, session=self.session, with_soup=True)
        info_item = soup.find("div", 'info_item')
        if not info_item:
            return {}

        book_details = {}

        book_details['isbn'] = info_item.find("span", attrs={"class": "value", "itemprop": "value"}).text
        book_details['name'] = info_item.find("div", "preview_text").text
        book_details['price'] = "".join(filter(lambda x: x.isdigit(), info_item.find("div", "price").text))

        for tr in soup.find("table", "props_list"):
            if bool(tr.text.strip()):
                tds = tr.find_all("td")
                prop, val = [t.text.strip() for t in tds]

                if prop == "Жанр":
                    book_details["category"] = val
                elif prop == "Возрастные ограничения":
                    book_details["age_category"] = val
                elif prop == "Переплет":
                    book_details["cover"] = val
                elif prop == "Язык":
                    book_details["language"] = val
                elif prop == "Количество страниц":
                    book_details["pages"] = val
                elif prop == "Страна производителя":
                    book_details["country"] = val
                elif prop == "Серия":
                    book_details["series"] = val
                elif prop == "Автор":
                    book_details["authors"] = val
                elif prop == "Год Издания":
                    book_details["year"] = val
                elif prop == "Формат":
                    book_details["type"] = val
                elif prop == "Производитель":
                    book_details["publisher"] = val

        detail_text = soup.find("div", "detail_text")
        description = detail_text.contents if detail_text else ""
        book_details["description"] = "\n".join([d.text.strip() for d in description])

        # Img data
        book_details['image_url'] = ''
        book_details['missing image'] = False

        image_url_raw = soup.find("div", "slides").find("img").get("src")
        image_url = web.extract_filename_from_url(image_url_raw)
        if "no_photo_medium.png" in image_url:
            book_details['missing image'] = True
        else:
            book_details['image_url'] = BASE_URL + image_url_raw

        return book_details

    # def get_image_filepath_OLD(self, isbn: str) -> str:
    #     """Формирует путь к файлу с картинкой обложки книги."""
    #     image_filename = f"{isbn}.jpg"
    #     return os.path.join(self.images_dirpath, image_filename)

    # def get_image_filepath(self, image_name: str, missing_image: bool) -> str:
    #     """Формирует путь к файлу с картинкой обложки книги."""
    #     images_dirpath = self.missing_images_dirpath if missing_image else self.images_dirpath
    #     image_filename = f"{image_name}.jpg"
    #     return os.path.join(images_dirpath, image_filename)
