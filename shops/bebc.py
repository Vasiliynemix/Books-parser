__doc__ = '\nФункции для парсинга интернет-магазина bebc.co.uk.\n'

import math
import re
import time
from contextlib import suppress
from threading import Thread
from urllib.parse import quote

import exceptions
import web
from shops.BooksClass import PublishersDownloadThread, BooksDownloadThread
from logger_manager import create_logger

SHOP = 'bebc.co.uk'
BASE_URL = f'https://www.{SHOP}'
MAX_BOOKS_PER_PAGE = 18


class BebcPublishers(PublishersDownloadThread):
    def __init__(self):
        super().__init__()

        # Superclass variables
        self.shop_name = SHOP
        self.main_func = self._run
        self.logger = create_logger(SHOP)

    def _run(self):
        """Загружает список издательств из магазина bebc.co.uk"""

        response, soup = web.get_html_page(BASE_URL, with_soup=True)
        self.progress_update.emit(30)

        with suppress(IndexError):
            publishers_tags = soup.find_all('select')[0]
        publishers = [tag.text.strip() for tag in publishers_tags.find_all('option')[1:]]

        if not (publishers_tags and publishers):
            raise exceptions.WebsiteStructureError(f"На web-странице {BASE_URL} не найдены издательства.")
            # return []
        self.progress_update.emit(60)

        return [publishers]


class BebcBooks(BooksDownloadThread):
    __doc__ = 'Класс потока загрузки информации о книгах с сайта bebc.co.uk.'

    def __init__(self, publisher, excel_filepath, images_dirpath, missing_images_dirpath):  # , isbn):
        super().__init__(publisher, excel_filepath, images_dirpath, missing_images_dirpath)

        # Superclass variables
        self.shop_name = SHOP
        self.BASE_URL = BASE_URL
        self.main_func = self._run
        self.logger = create_logger(SHOP)

        # # Own variables
        # self.isbn = isbn

    def _run(self):
        """
        Запускает поток загрузки информации о книгах по выбранному издательству
        с сайта bebc.co.uk.
        """

        # self.session = web.create_session_by_url(BASE_URL)
        books = []

        first_soup = self.get_soup_from_search_page(1)
        books_count = self.get_total_books_amount(first_soup)

        # IF only 1 book in a publisher, it opens this book's page
        if books_count == 1:
            self.progress_update.emit(1)
            self.parse_book(first_soup, books)
        # More than 1 book
        else:
            pages_amount = math.ceil(books_count / MAX_BOOKS_PER_PAGE)
            self.progress_set.emit(books_count)

            # Parse throw all pages
            for page in range(1, pages_amount + 1):
                # Get soup from page (first page is already parsed)
                soup = first_soup if page == 1 else self.get_soup_from_search_page(page)

                product_items = soup.find_all(class_='product-item')
                if not product_items:
                    break  # possible end or some error

                # A thread for every book on page
                threads_amount = len(product_items)
                threads = []

                for i in range(threads_amount):
                    threads.append(Thread(target=self.parse_books_thread, args=(product_items[i], books, i)))
                    threads[i].start()

                [thread.join() for thread in threads]

        return books

    def get_soup_from_search_page(self, page_number):
        base_search = f'{BASE_URL}/categories/advancedsearch'
        encoded_publisher = quote(self.publisher, safe='')
        page_url = f"{base_search}?publisher={encoded_publisher}&page={page_number}"
        response, soup = web.get_html_page(page_url, session=self.session, with_soup=True)
        return soup

    def parse_book(self, soup, books: list):
        book_details = self.extract_book_details(soup)
        if book_details:
            books.append(book_details)
            self.download_book_cover(book_details)

    def parse_books_thread(self, product_item, books, i):
        time.sleep(0.2 * i)  # for threads to start in order

        a_tag = product_item.find('a')
        if not a_tag:
            # debug to log
            self.logger.debug(f"ERROR: [{SHOP}] Не найден тег 'a' в product_item: {product_item}")
        else:
            book_url = a_tag.get('href')
            book_response, book_soup = web.get_html_page(book_url, session=self.session, with_soup=True)

            self.parse_book(book_soup, books)

        self.progress_update.emit(len(books))

    # def _run_threading(self):

    def get_total_books_amount(self, soup):
        books_count = 1
        with suppress(AttributeError, ValueError):
            tag_p = soup.find('div', class_='listing').find('p')
            text = tag_p.text
            text = text[text.find(' of ') + 4:]
            books_count = int(text[:text.find(' ')])

        if not books_count:
            raise exceptions.WebsiteStructureError(f"В магазине {SHOP} не найдено общее количество книг издательства.")

        self.progress_set.emit(books_count)
        return books_count

    def get_total_books_amount_old(self, soup, response, page_url):
        books_count = 1
        with suppress(AttributeError, ValueError):
            tag_p = soup.find('div', class_='listing').find('p')
            text = tag_p.text
            text = text[text.find(' of ') + 4:]
            books_count = int(text[:text.find(' ')])
        if not books_count:
            if response.url == page_url:
                raise exceptions.WebsiteStructureError(
                    f"На web-странице {response.url} не найдено общее количество книг издательства.")
            # books_count = 1

        self.progress_set.emit(books_count)
        return books_count

    def extract_book_details(self, soup) -> dict:
        """
        Получает детальную информацию о книге из содержимого
        html-страницы книги в магазине bebc.co.uk.
        """
        product_details = soup.find(class_='product-detail')
        if not product_details:
            return {}
        book_details = {}
        h4_tag = product_details.find('h4')
        if h4_tag:
            book_details['name'] = h4_tag.get_text()
        img_tags = product_details.find_all('img')
        book_details['image_url'] = ''
        book_details['missing image'] = False
        if img_tags:
            for img_tag in img_tags:
                image_url = img_tag.get('src')
                if image_url:
                    if image_url.startswith('https') and image_url.endswith('.jpg'):
                        book_details['image_url'] = image_url
                if web.extract_filename_from_url(image_url) == 'noimageavailablebig.jpg':
                    book_details['missing image'] = True

            em_tag = product_details.find('em')
            if em_tag:
                tag_text = em_tag.get_text().split('Published by')
                book_details['publisher'] = tag_text[1].strip()
                book_details['authors'] = tag_text[0].replace('by', '').strip()

        li_tags = product_details.find_all('li')
        for li_tag in li_tags:
            tag_text = li_tag.get_text()
            if 'ISBN:' in tag_text:
                book_details['isbn'] = tag_text.replace('ISBN:', '').strip()
            elif 'Category:' in tag_text:
                book_details['category'] = tag_text.replace('Category:', '').strip()
            # elif 'Learning Level:' in tag_text:
            #         book_details['level'] = tag_text.replace('Learning Level:', '').strip()

        p_tags = product_details.find_all('p')
        book_details['description'] = ''
        for tag_index, p_tag in enumerate(p_tags):
            tag_text = p_tag.get_text().strip()
            if tag_index == 0:
                tag_text = tag_text[1:].strip()
                space_position = tag_text.find(' ')
                if space_position == -1:
                    book_details['price'] = tag_text
                else:
                    book_details['price'] = tag_text[:space_position]
            else:
                if tag_text.startswith('Published '):
                    year = tag_text[9:14].strip()
                    match = re.search('^\\d+', year)
                    if match:
                        year = match.group(0)
                        book_details['year'] = year
                else:
                    if 'Add to Cart' not in tag_text:
                        book_details['description'] += tag_text + ' '

        return book_details
