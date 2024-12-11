__doc__ = '\nЗапуск графического интерфейса парсера информации\nс сайтов книжных интернет-магазинов.\n'

import logging
import time
import traceback

import web
from logger_manager import create_logger
import main_ui

logger: logging.Logger


if __name__ == '__main__':
    logger = create_logger(None, "logs.txt")
    web.logger = logger
    logger.debug("Парсер запущен. Версия 5.5")

    try:
        main_ui.start_main_ui(logger)
    except Exception as exception:
        err_text = f"Ошибка в приложении парсера - '{exception}'\n" \
                   f"{traceback.format_exc()}"
        logger.debug(err_text)
