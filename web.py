__doc__ = '\nФункции работы с интернетом.\n'

import logging
import os
import time
from urllib.parse import unquote, urlsplit

import requests
import urllib3
from bs4 import BeautifulSoup


# Suppress only the single warning from urllib3.
urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)

logger: logging.Logger
CONNECTION_ATTEMPTS_COUNT = 10
DELAY_BETWEEN_CONNECTION_ATTEMPTS = 10
MAX_TIMEOUT = 40


def download_file(file_url: str, filepath: str, session=None) -> None:
    """Сохраняет в указанном каталоге файл из интернета."""
    # if os.path.exists(filepath):
    #     os.remove(filepath)  # OLD WAY WAS TO REMOVE IT

    # if not os.path.exists(filepath):
    url = file_url.replace('\\', '/')
    response = get_html_page(url, session=session)

    # if session:
    #     response = session.get(file_url.replace('\\', '/'))
    # else:
    #     response = requests.get(file_url.replace('\\', '/'))
    # response.raise_for_status()

    dirpath = os.path.dirname(filepath)
    os.makedirs(dirpath, exist_ok=True)
    with open(filepath, 'wb') as file:
        file.write(response.content)


def extract_filename_from_url(url: str) -> str:
    """Извлекает из url адреса файла в интернете имя файла."""
    web_filepath = unquote(urlsplit(url).path)
    filename = os.path.basename(web_filepath)
    return filename


def create_session_by_url(url, headers=None, yandex=False, verify_ssl=True):
    """Создает сессию для доступа к сайту."""
    session = requests.Session()
    session.verify = verify_ssl
    if yandex:
        session.headers = {'User-Agent': "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)"}
    if headers:
        session.headers.update(headers)

    get_html_page(url, session=session)

    return session


def exponential_backoff(attempt):
    # Экспоненциальная задержка
    delay = 2 ** (attempt + 1)  # 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048
    delay += DELAY_BETWEEN_CONNECTION_ATTEMPTS
    time.sleep(delay)


def get_html_page(url, headers=None, params=None, session=None, with_soup=False):
    """Получает web-страницу с заданным url."""
    # by default, verify_ssl is True
    response = None

    heads = headers or session.headers if session else None
    parms = params or session.params if session else None

    for attempt in range(CONNECTION_ATTEMPTS_COUNT):
        # logger.debug(f"Попытка {attempt + 1} из {CONNECTION_ATTEMPTS_COUNT}. URL: {url}"
        #              f", headers: {headers}, params: {params}, session: {session}"
        #              f", with_soup: {with_soup}")
        # if attempt >= 1:
        #     verify_ssl = False  # after first attempt, we don't need to verify SSL

        except_text = f"Попытка {attempt + 1} из {CONNECTION_ATTEMPTS_COUNT}.\n"
        try:
            if session:
                response = session.get(url, params=params, timeout=MAX_TIMEOUT)
            else:
                response = requests.get(url, headers=headers, params=params, timeout=MAX_TIMEOUT)

            if response.status_code == 404:
                logger.debug(except_text + f"Ошибка 404: Страница не найдена. URL: {url}")
                # if not ignore_404_error:
                exponential_backoff(attempt)
                # continue

            if response:
                break
        except requests.exceptions.ConnectionError:
            logger.debug(except_text + f"Ошибка соединения. URL: {url}")
            exponential_backoff(attempt)
        except requests.exceptions.Timeout:
            logger.debug(except_text + f"Превышен таймаут. URL: {url}")
            exponential_backoff(attempt)
        except requests.exceptions.ChunkedEncodingError:
            logger.debug(except_text + f"Разрыв в передаче данных. URL: {url}")
            exponential_backoff(attempt)
        except requests.exceptions.RequestException as e:
            logger.debug(except_text + f"Ошибка запроса. URL: {url}. Ошибка: {e}")
            exponential_backoff(attempt)
        except Exception as e:
            err_text = f"Неизвестная ошибка доступа к сайту. \n" \
                       f"URL: {url}, headers: {heads}, params: {parms}, session: {session}\n"
            if response:
                err_text += f"response, content, request - {response, response.content, response.request}"
            logger.debug(err_text)
            exponential_backoff(attempt)
    else:
        err_text = f"ERROR: Ошибка во время доступа к серверу. ({CONNECTION_ATTEMPTS_COUNT} раз!) \n" \
                   f"URL: {url}, headers: {heads}, params: {parms}, session: {session}\n"
        if response:
            err_text += f"response, content, request - {response, response.content, response.request}"
        logger.debug(err_text)

        if response:
            response.raise_for_status()

        raise Exception(err_text)

    if with_soup:
        return response, get_soup_from_content(response.content)
    else:
        return response


def get_soup_from_content(content, parser='html.parser'):
    """Получает объект BeautifulSoup из HTML-контента."""
    encoded_content = content.encode('utf-8') if isinstance(content, str) else content
    return BeautifulSoup(encoded_content, parser)
