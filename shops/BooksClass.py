__doc__ = '\nФункции для парсинга интернет-магазинов.\n'

import logging
import os
import shutil
import time
import traceback

# import requests.exceptions
from PyQt6.QtCore import pyqtSignal, QThread

import files
import web


# from contextlib import suppress
# import cyrtranslit
# from books_parser import logger

# import cchardet

class MainBooksThread(QThread):
    __doc__ = 'Общий класс загрузки информации с сайтов.'
    progress_set = pyqtSignal(int)
    progress_update = pyqtSignal(int)
    result = pyqtSignal(dict)
    error = pyqtSignal(Exception)

    # main_job: str
    shop_name: str
    main_func: callable
    logger: logging.Logger
    session = None

    def __init__(self):
        super().__init__()

    def create_session(self, url, verify_ssl):
        self.session = web.create_session_by_url(url, yandex=True, verify_ssl=verify_ssl)


class PublishersDownloadThread(MainBooksThread):
    __doc__ = 'Общий класс загрузки издательств с сайтов.'

    def __init__(self):
        super().__init__()

    def run(self):
        try:
            # self.logger.debug(f"Запущен сбор всех издательств для магазина '{self.shop_name}'")

            data = self.main_func()

            if len(data) == 1:
                publishers = publishers_str = data[0]
            elif len(data) == 2:
                publishers, publishers_str = data
            else:
                raise Exception(f"Неверный формат данных издательств для магазина '{self.shop_name}'")

            files.write_publishers(self.shop_name, publishers_str)
            self.progress_update.emit(100)
            self.result.emit({'publishers': publishers})

            # self.logger.debug(f"Завершен сбор всех издательств для магазина '{self.shop_name}'")

        except Exception as exception:
            err_text = f"Ошибка во время сбора всех издательств магазина '{self.shop_name}' - '{exception}'\n" \
                       f"{traceback.format_exc()}"
            self.logger.debug(err_text)
            self.error.emit(exception)


class BooksDownloadThread(MainBooksThread):
    __doc__ = 'Общий класс загрузки информации о книгах с сайтов.'
    BASE_URL = ""

    def __init__(self, *args, verify_ssl=True):
        super().__init__()
        publisher, excel_filepath, images_dirpath, missing_images_dirpath = args

        self.publisher = publisher.strip()
        self.excel_filepath = excel_filepath
        self.images_dirpath = images_dirpath
        self.missing_images_dirpath = missing_images_dirpath
        self.verify_ssl = verify_ssl

    def run(self):
        try:
            start = time.time()
            # self.logger.debug(f"Запущен сбор книг издательства '{self.publisher}' для магазина '{self.shop_name}'")
            self.create_session(self.BASE_URL, self.verify_ssl)

            books = self.main_func()
            current_books_count = len(books)

            # write to excel
            if books:
                files.write_books_to_excel(self.excel_filepath, books)
                files.adjust_column_widths(self.excel_filepath)

            self.result.emit({'books_count': current_books_count})

            time_diff = time.time() - start

            self.logger.debug(f"Сбор книг({current_books_count}) издательства '{self.publisher}' завершен за "
                              f"{time_diff:.2f} секунд")
        except Exception as exception:
            err = Exception(f"Ошибка во время парсинга книг издательства '{self.publisher}' - '{exception}'\n"
                            f"{traceback.format_exc()}")
            self.logger.debug(err)
            self.error.emit(exception)

    def get_image_url(self, book_details):
        return book_details['image_url']

    def get_book_cover_name(self, book_details):
        return book_details['isbn']

    def download_book_cover(self, book_details):
        """ Загружает картинку обложки книги, если её нет. """
        image_filepath = self.get_image_filepath(self.get_book_cover_name(book_details), book_details)

        if book_details['image_url']:
            if not os.path.exists(image_filepath):
                image_url = self.get_image_url(book_details)
                web.download_file(image_url, image_filepath, self.session)

                # Проверяем, если файл SVG, конвертируем в JPG
                # if image_filepath.endswith(".svg"):
                #     jpg_filepath = image_filepath.replace(".svg", ".jpg")
                #     self.convert_svg_to_jpg(image_filepath, jpg_filepath)
                #     os.remove(image_filepath)  # Удаляем исходный SVG, если он больше не нужен
        else:
            self.logger.debug(f"WARNING: Книга isbn:{book_details['isbn']} по адресу {book_details['url']} "
                              f"не имеет картинки обложки.")

    def get_image_filepath(self, image_name: str, book_details) -> str:
        """Формирует путь к файлу с картинкой обложки книги."""
        extension = book_details['image_url'].split(".")[-1]
        if extension == "png":
            extension = "jpg"
        missing_image = book_details['missing image']

        images_dirpath = self.missing_images_dirpath if missing_image else self.images_dirpath
        image_filename = f"{image_name}.{extension}"
        return os.path.join(images_dirpath, image_filename)

    # @staticmethod
    # def convert_svg_to_jpg(input_svg_path, output_jpg_path):
    #     png_data = cairosvg.svg2png(url=input_svg_path)
    #
    #     from PIL import Image
    #     from io import BytesIO
    #
    #     image = Image.open(BytesIO(png_data))
    #     rgb_image = image.convert('RGB')  # Убедиться, что формат RGB
    #     rgb_image.save(output_jpg_path, "JPEG")
