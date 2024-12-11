import requests
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import *

import exceptions
from shops import bebc, my_shop, studentsbook
import files


BEBC_SHOP, STUDENTSBOOK_SHOP, MY_SHOP = 'bebc.co.uk', 'studentsbook.net', 'my-shop.ru'
good_shops = [BEBC_SHOP, STUDENTSBOOK_SHOP, MY_SHOP]


class MainWindow(QMainWindow):
    __doc__ = 'Главное окно GUI.'

    def __init__(self, logger):
        super(MainWindow, self).__init__()
        self.logger = logger

        self.icon = QIcon(files.get_icon_filepath())
        self.setWindowIcon(self.icon)
        self.setWindowTitle('Парсер по магазинам и издательствам')
        self.resize(600, 300)
        self.shops_label = QLabel('Магазины')
        self.shops_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.shops_combobox = QComboBox()
        self.shops_combobox.addItems([BEBC_SHOP, STUDENTSBOOK_SHOP, MY_SHOP,
                                      'bookbridge.ru', 'deltabook.ru'])
        self.shops_combobox.currentIndexChanged.connect(self.handle_shop_selection)
        self.top_left_vbox = QVBoxLayout()
        self.top_left_vbox.addWidget(self.shops_label)
        self.top_left_vbox.addWidget(self.shops_combobox)
        self.top_left_vbox.addStretch(0)
        self.publishers_label = QLabel('Издательства')
        self.publishers_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.publishers_combobox = QComboBox()
        self.top_right_vbox = QVBoxLayout()
        self.top_right_vbox.addWidget(self.publishers_label)
        self.top_right_vbox.addWidget(self.publishers_combobox)
        self.top_right_vbox.addStretch(0)
        self.top_hbox = QHBoxLayout()
        self.top_hbox.addLayout(self.top_left_vbox)
        self.top_hbox.addLayout(self.top_right_vbox)
        self.publishers_button = QPushButton('Сбор издательств магазина')
        self.publishers_button.clicked.connect(self.handle_publishers_click)
        self.shops_button = QPushButton('Загрузка книг')
        self.shops_button.clicked.connect(self.handle_shops_click)
        self.parse_all_button = QPushButton('Сбор всех издательств')
        self.parse_all_button.clicked.connect(self.handle_parse_all_click)
        self.bottom_hbox = QHBoxLayout()
        self.parse_bottom_hbox = QHBoxLayout()
        self.tab_bottom_hbox = QHBoxLayout()
        self.bottom_hbox.addWidget(self.publishers_button)
        self.bottom_hbox.addWidget(self.shops_button)
        self.parse_bottom_hbox.addWidget(self.parse_all_button)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setStyleSheet('QProgressBar {max-height: 14px; text-align: center;}')
        self.progress_bar.setTextVisible(False)
        self.status_label = QLabel(self)
        self.status_label.setVisible(False)
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().addPermanentWidget(self.progress_bar, 1)
        self.statusBar().addPermanentWidget(self.status_label, 0)
        self.main_vbox = QVBoxLayout()
        self.main_vbox.addLayout(self.top_hbox)
        self.main_vbox.addLayout(self.bottom_hbox)

        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)
        self.line.setObjectName("line")
        self.main_vbox.addWidget(self.line)

        spacerItem = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.main_vbox.addItem(spacerItem)

        self.main_vbox.addLayout(self.parse_bottom_hbox)
        self.main_vbox.addLayout(self.tab_bottom_hbox)
        self.main_vbox.addStretch(0)
        self.main_widget = QWidget()
        self.main_widget.setLayout(self.main_vbox)
        self.setCentralWidget(self.main_widget)

        self.groupBox = QGroupBox(self.main_widget)
        self.tab_bottom_hbox.addWidget(self.groupBox)
        # self.groupBox.setGeometry(QRect(100, 250, 351, 81))
        self.groupBox.setTitle("")
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout_2 = QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setContentsMargins(5, 5, 5, 5)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.parse_some_button = QPushButton(self.groupBox)
        self.parse_some_button.setObjectName("pushButton")
        self.verticalLayout_2.addWidget(self.parse_some_button)
        self.parse_some_button.clicked.connect(self.handle_parse_some_click)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_3 = QLabel(self.groupBox)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout.addWidget(self.label_3)
        self.combobox_from = QComboBox(self.groupBox)
        self.combobox_from.setObjectName("QComboBox")
        self.horizontalLayout.addWidget(self.combobox_from)
        self.label_2 = QLabel(self.groupBox)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.combobox_to = QComboBox(self.groupBox)
        self.combobox_to.setObjectName("QComboBox_2")
        self.horizontalLayout.addWidget(self.combobox_to)
        self.verticalLayout_2.addLayout(self.horizontalLayout)

        sizePolicy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)
        self.label_2.setSizePolicy(sizePolicy)

        self.parse_some_button.setText("Сбор некоторых издательств")
        self.label_3.setText("С")
        self.label_2.setText("по")

        # self.shops_combobox = QComboBox()
        self.fill_comboboxes(shop=BEBC_SHOP)

        # Vars to remember
        self.studentsbook_soup_data_parsed = None
        self.thread_data = None

        # MainWindow.setCentralWidget(self.centralwidget)

    def handle_publishers_click(self) -> None:
        """Обрабатывает нажатие кнопки 'Сбор издательств магазина'."""
        shop = self.shops_combobox.currentText()
        if shop not in good_shops:
            message = f"Извините, сбор издательств для магазина {shop} пока не запрограммирован"
            self.show_messagebox(message, warning=True)
            return

        self.set_widgets_enabled(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat('%p%')

        files.prepare_shop_dirs(shop)

        if shop == BEBC_SHOP:
            # self.download_thread = bebc.PublishersDownloadThread()
            self.download_thread = bebc.BebcPublishers()
        elif shop == STUDENTSBOOK_SHOP:
            # content = files.get_correct_xml_content(shop)
            # self.studentsbook_soup = web.get_soup_from_content(content, parser='xml')

            self.download_thread = studentsbook.StudentsbookPublishers()
            # self.download_thread.progress_set.connect(self.set_part_progress)
            self.download_thread.soup_data_parsed.connect(self.load_students_soup_data_parsed)
        elif shop == MY_SHOP:
            self.download_thread = my_shop.MyShopPublishers()

        # self.logger.debug(f"Начат сбор всех издательств для магазина {shop}")
        # Same in all shops
        self.download_thread.progress_update.connect(self.update_progress)
        self.download_thread.error.connect(self.show_thread_error)
        self.download_thread.result.connect(self.show_thread_result)
        self.download_thread.finished.connect(self.finish_thread)
        self.download_thread.start()

    def handle_parse_some_click(self):
        """Обрабатывает нажатие кнопки 'Сбор некоторых издательств' """
        shop = self._get_picked_shop()
        if not shop:
            return

        p_from = self.combobox_from.currentIndex()
        p_to = self.combobox_to.currentIndex()

        if p_from == -1 or p_to == -1:
            message = f'Не выбраны издательства'
            self.show_messagebox(message, warning=True)
            return

        if p_from > p_to:
            message = f'Издательство "ПО" идёт ранее, чем издательство "С"'
            self.show_messagebox(message, warning=True)
        else:
            publishers = self._get_publishers(shop)
            self.thread_data = [shop, publishers, p_from, p_to]

            self._parse_next_publisher()

    def fill_comboboxes(self, publishers=None, shop=None):
        combos = [self.publishers_combobox, self.combobox_from, self.combobox_to]

        if not publishers:
            publishers = self._get_publishers(shop)

        for c in combos:
            c.clear()
            c.addItems(publishers)

    def handle_parse_all_click(self):
        """Обрабатывает нажатие кнопки 'Сбор всех издательств' """
        shop = self._get_picked_shop()
        if not shop:
            return

        publishers = self._get_publishers(shop)
        if not publishers:
            self.show_messagebox('Нет издательств для сбора', warning=True)
            return

        self.thread_data = [shop, publishers, 0, None]

        self._parse_next_publisher()

    def handle_shops_click(self) -> None:
        """Обрабатывает нажатие кнопки 'Загрузка книг'."""
        publisher = self._get_picked_publisher()
        if not publisher:
            return

        shop = self._get_picked_shop()
        if not shop:
            return

        self._parse_shop_publisher(shop, publisher)

    def _get_publishers(self, shop):
        publishers = files.read_publishers(shop)
        if shop == MY_SHOP:
            self.my_shop_publisher_id = [p.split("\tID=") for p in publishers]
            publishers = [p[0] for p in self.my_shop_publisher_id]

        return publishers

    def handle_shop_selection(self, select_index: int) -> None:
        """Обрабатывает выбор магазина в комбобоксе shops_combobox."""
        shop = self.shops_combobox.currentText()
        self.fill_comboboxes(shop=shop)

    def _parse_next_publisher(self):
        try:
            shop, publishers, index_from, index_to = self.thread_data
        except Exception as e:
            a = e
            self.logger.debug(e)
            message = f"Ошибка во время сбора издательств: {e}"
            self.show_messagebox(message, warning=True)
            return

        # if type(index_to) == type(None): #isinstance(index_to, type(None))
        if isinstance(index_to, type(None)):
            index_to = len(publishers) - 1

        if index_from <= index_to:
            publisher = publishers[index_from]
            self.publishers_combobox.setCurrentIndex(index_from)
            self._parse_shop_publisher(shop, publisher)
            self.thread_data[2] += 1
        else:
            self.thread_data = None
            message = f"Загрузка книг для магазина {shop} завершена."
            self.show_messagebox(message)

    def _get_picked_shop(self):
        shop = self.shops_combobox.currentText()
        if shop not in good_shops:
            message = f"Извините, загрузка книг для магазина {shop} пока не запрограммирована"
            self.show_messagebox(message)
            return None

        return shop

    def _get_picked_publisher(self):
        publisher = self.publishers_combobox.currentText()
        if not publisher:
            self.show_messagebox('Выберите издательство')
            return None
        return publisher

    def _parse_shop_publisher(self, shop, publisher):
        if shop == STUDENTSBOOK_SHOP:
            publisher = publisher.split(" [")[0]

        # File paths
        excel_filepath = files.get_excel_filepath(shop, publisher)
        images_dirpath = files.get_images_dirpath(shop, publisher)
        missing_images_dirpath = files.get_missing_images_dirpath(shop, publisher)

        try:
            files.prepare_output_dirs_and_files(shop, publisher)
            # if not files.is_file_exists(excel_filepath):  # Start from scratch
            #     files.prepare_output_dirs_and_files(shop, publisher)
            # isbn = []
            # else:  # Get old values
            #     isbn = files.get_books_isbn_from_excel(excel_filepath)

        except PermissionError as e:
            message = f"Нет доступа к файлу: '{e.filename}'. Пожалуйста, закройте файл."
            self.show_messagebox(message, warning=True)
            return

        self.set_widgets_enabled(False)
        if shop == BEBC_SHOP:
            # isbn = files.get_books_rows_from_excel(excel_filepath, 0)
            # self.download_thread = bebc.BooksDownloadThread(publisher, excel_filepath, images_dirpath,
            #                                                 missing_images_dirpath, isbn)
            self.download_thread = bebc.BebcBooks(publisher, excel_filepath, images_dirpath,
                                                  missing_images_dirpath)  # , isbn)
        elif shop == STUDENTSBOOK_SHOP:
            if not self.studentsbook_soup_data_parsed:
                xml_dirpath = files.get_xml_dirpath(shop)
                if files.is_file_exists(xml_dirpath):
                    sb = studentsbook.StudentsbookPublishers()
                    sb.parse_xml_file()
                    sb.get_total_offers()
                    sb.get_total_categories()

                    # content = files.get_correct_xml_content(shop)
                    self.studentsbook_soup_data_parsed = [sb.offers, sb.categories_tag]
                else:
                    message = f"Не найден файл '{xml_dirpath}'. Сначала спарсите издательства."
                    self.show_messagebox(message, warning=True)
                    self.set_widgets_enabled(True)
                    return
            # isbn = files.get_books_rows_from_excel(excel_filepath, 0)

            self.download_thread = studentsbook.StudentsbookBooks(
                publisher, excel_filepath, images_dirpath, missing_images_dirpath, self.studentsbook_soup_data_parsed)
            # self.download_thread.progress_set.connect(self.set_studentsbook_progress)
            # self.download_thread.progress_update.connect(self.update_studentsbook_progress)

        elif shop == MY_SHOP:
            publisher_name, publisher_id = self.my_shop_publisher_id[self.publishers_combobox.currentIndex()]
            ids = files.get_books_rows_from_excel(excel_filepath, 19)

            self.download_thread = my_shop.MyShopBooks(publisher, excel_filepath, images_dirpath,
                                                       missing_images_dirpath, publisher_id, publisher_name, ids)

        self.download_thread.progress_set.connect(self.set_part_progress)
        self.download_thread.progress_update.connect(self.update_progress)
        self.download_thread.error.connect(self.show_thread_error)
        self.download_thread.result.connect(self.show_thread_result)
        self.download_thread.finished.connect(self.finish_thread)
        self.download_thread.start()

    def load_students_soup_data_parsed(self, soup_data_parsed):
        """Загружает BeautifulSoup для магазина studentsbook."""
        self.studentsbook_soup_data_parsed = soup_data_parsed

    def finish_thread(self):
        """Обрабатывает окончание работы дочернего потока."""
        self.status_label.setText = ''
        self.status_label.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.reset()
        self.set_widgets_enabled(True)

        if self.thread_data:
            self._parse_next_publisher()

    def set_part_progress(self, progress_max_value: int):
        """
        Устанавливает и показавает максимальное значение прогресс-бара
        для прогресс бара с форматом строки '<закачано> / <всего>'.
        """
        self.progress_bar.setFormat('%v / %m')
        self.progress_bar.setRange(0, progress_max_value or 1)  # For not empty freeze cycle
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

    def set_studentsbook_progress(self, progress_max_value: int):
        self.progress_bar.setFormat('%v / %m подкаталогов')
        self.progress_bar.setRange(0, progress_max_value)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.status_label.setText('Загружено 0 книг...')
        self.status_label.setVisible(True)

    def set_widgets_enabled(self, enabled_value: bool):
        """Устанавливает доступность/недоступность виджетов GUI."""
        self.shops_combobox.setEnabled(enabled_value)
        self.publishers_combobox.setEnabled(enabled_value)
        self.publishers_button.setEnabled(enabled_value)
        self.shops_button.setEnabled(enabled_value)
        self.parse_some_button.setEnabled(enabled_value)
        self.parse_all_button.setEnabled(enabled_value)
        self.combobox_to.setEnabled(enabled_value)
        self.combobox_from.setEnabled(enabled_value)

    def show_connection_error(self, ex: Exception) -> None:
        """Показывает окно с сообщением об ошибке соединения с сайтом."""
        message = f"Возникла ошибка соединения с сайтом:\n{ex}\n\nПопробуйте ещё раз позже."
        self.show_messagebox(message, warning=True)

    def show_messagebox(self, message: str, warning: bool = False) -> None:
        """Показывает окно с указанным сообщением."""
        if warning:
            message_box = QMessageBox().warning(self, "Ошибка", message)
        else:
            message_box = QMessageBox()
            message_box.setWindowIcon(self.icon)
            message_box.setWindowTitle('Парсер - Сбор издательств магазина')
            message_box.setText(message)
            message_box.exec()

    def show_thread_error(self, exception: Exception):
        exception_type = type(exception)
        if exception_type is requests.exceptions.ConnectionError or exception_type is requests.exceptions.HTTPError:
            self.show_connection_error(exception)
        elif exception_type is exceptions.WebsiteStructureError:
            self.show_messagebox(f"{exception}", warning=True)
        else:
            self.show_messagebox(f"Произошла ошибка {type(exception).__name__}:\n{exception}", warning=True)

    def show_thread_result(self, result: dict):
        """Показывает окно с результатами выполнения дочернего потока."""
        if self.thread_data:  # skip if many threads
            return

        if 'books_count' in result:
            books_count = result['books_count']
            if books_count:
                self.show_messagebox(f"Загружено {books_count} книг.")
            else:
                self.show_messagebox('Отсутствуют новые книги!')

        elif 'publishers' in result:
            publishers = result['publishers']
            if publishers:
                shop = self.shops_combobox.currentText()
                if shop == MY_SHOP:
                    self._get_publishers(shop)  # To load 'self.my_shop_publisher_id'

                self.fill_comboboxes(publishers)
                self.show_messagebox('Издательства успешно загружены.')
        elif 'catalogs' in result:
            catalogs = result['catalogs']
            if catalogs:
                self.fill_comboboxes(catalogs)
                self.show_messagebox('Каталоги успешно загружены.')

    def update_progress(self, progress_value: int) -> None:
        """Обновляет текущее значение прогресс-бара."""
        self.progress_bar.setValue(progress_value)

    def update_studentsbook_progress(self, progress_values: dict) -> None:
        """
        Обновляет текущее значение прогресс-бара и текст метки статус-бара.
        """
        self.progress_bar.setValue(progress_values['subcatalog_number'])
        self.status_label.setText(f"Загружено {progress_values['book_number']} книг...")


def start_main_ui(logger):
    app = QApplication([])
    window = MainWindow(logger)
    window.show()
    app.exec()
