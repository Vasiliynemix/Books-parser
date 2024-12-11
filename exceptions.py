__doc__ = 'Модуль содержит собственные исключения приложения.'


class WebsiteStructureError(Exception):
    __doc__ = 'Ошибка нарушения структуры сайта.'

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return f"Возникла ошибка:\n{self.message}\n\nСкорее всего, структура сайта изменилась. Обратитесь к программисту."
