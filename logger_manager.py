import logging
import sys

from files import get_shop_dirpath


def create_logger(shop, filename=None):
    # global logger
    # logger = logging.getLogger('logger')
    logger = logging.getLogger(shop or 'logger')

    # skip if logger already exists
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)
    log_format = logging.Formatter(fmt='[%(asctime)s: %(threadName)s %(module)s] %(message)s')
    # log_format = logging.Formatter(fmt='[%(asctime)s: %(threadName)s | line %(lineno)d, in %(funcName)s] %(message)s')

    # To console
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(log_format)
    logger.addHandler(handler)

    # To file
    if not filename:
        filename = get_shop_dirpath(shop) + f'/logs.txt'
    file_handler = logging.FileHandler(filename, encoding="utf-8")
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)  # write logs to file

    return logger
