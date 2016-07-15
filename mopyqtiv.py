#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################################
# Copyright [2016] [Евгений]
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##########################################################################

import os  # операции с файлами
import sys  # аргументы командной строки
import time  # для меток удаляемых файлов
import shutil  # для удаления файлов
import atexit  # для удаления временных файлов при выходе
import hashlib  # для рандомных имён времнных папок

from PIL import Image
from multiprocessing import Pool, Pipe

from PyQt5.QtGui import (QIcon, QPalette, QColor,
                         QFont, QPixmap, QCursor, QTransform
                         )

from PyQt5.QtWidgets import (QWidget, QMenu, QLabel, QScrollArea,
                             QApplication, QFileDialog,QAction,
                             QVBoxLayout, QLayout, qApp
                             )

from PyQt5.QtCore import Qt, QThread, QFileInfo, QTimer

###################################################
############### EDIT VARIABLES HERE ###############

WITHOUT_BORDER = True  # главное окно без рамки, рекомендуется
HINT_TIME = 2.5  # время показа сообщений в секундах
SCALE_STEP = 0.8  # шаг изменения масштаба
ROTATE_STEP = 15  # шаг вращения изображения в градусах
SCALE_MAGNIFIER = 1.7  # масштаб для лупы
MAGNIFIER_MOVE_BOOST = 1.3  # ускорение перемещния в режиме лупы
MINIATURE_WIDTH = 250  # ширина миниатюры по умолчанию
BACKGROUND_COLOR = '#000000'  # цвет фона главного окна
COPY_ON_SORTING = False  # перемещение (False) или копирование (True) при сортировке

########### DO NOT EDIT AFTER THIS LINE ###########
###################################################


class Filer:
    """
    Этот класс создаёт и обновляет список файлов
    """

    def __init__(self):
        self.files = []
        self.current_folder = os.getcwd()  # запись текущей папки
        self.dialog = QFileDialog()  # диалог выбора файлов
        self.can_choose_file = True
        self.available_extensions = ('.bmp', '.pbm', '.pgm', '.ppm', '.xbm',
                                     '.xpm', '.jpg', '.jpeg', '.png', '.gif'
                                     )

    def list_folder(self, path):
        """
        создаёт список изобр. папки -> self.files
        """
        self.files = []  # очистка списка изображений
        for name in os.listdir(path):
            if os.path.splitext(name)[1].lower() in self.available_extensions:  # фильтр по расширению
                self.files.append(os.path.join(path, name))
        self.files = list(set(self.files))  # не допускает дубликатов
        self.files.sort()

    def choose_file(self):
        """
        Диалог выбора картинки: возвращает путь для выбранного файла
        """
        if self.can_choose_file is True:
            file_path = self.dialog.getOpenFileName(
                    parent=None,
                    caption='Выбор файла',
                    directory=self.current_folder,
                    filter='Изображения('
                           '*.bmp *.pbm *.pgm *.ppm *.xbm '
                           '*.xpm *.jpg *.jpeg *.png *.gif)'
            )[0]

            # обновление текущей папки
            self.current_folder = os.path.split(file_path)[0]

            return file_path

        else:
            return ''

    def choose_folder(self, folder):
        """
        Диалог выбора папки: возвращает полный путь
        """
        folder_path = self.dialog.getExistingDirectory(
                parent=None,
                caption='Выбор файла',
                directory=folder
        )

        return folder_path


class Bind:
    """
    Объект временной связи клавиша -> папка
    Используется для сортировки изображений
    """

    def __init__(self):
        self.key = ''
        self.path = ''

    def move(self, image_path):
        """
        Отправляет изображение image_path по адресу destination
        """
        destination = os.path.join(self.path, os.path.split(image_path)[1])

        # перемещение или копирование при сортировке
        if COPY_ON_SORTING is False:
            shutil.move(image_path, destination)
        else:
            shutil.copy(image_path, destination)


class PopupMenu(QMenu):
    """
    Всплывающее меню
    """

    def __init__(self, main):
        super().__init__()

        self.main = main
        self.file = ''

        # описание действий
        info_action = QAction(
                QIcon.fromTheme('exifinfo'),
                'Информация',
                self
        )

        trash_action = QAction(
                QIcon.fromTheme('trash-empty'),
                'Отправить в корзину',
                self
        )

        exit_action = QAction(
                QIcon.fromTheme('application-exit'),
                'Выход',
                self
        )

        info_action.triggered.connect(self.show_info)
        trash_action.triggered.connect(lambda: self.main.trash(self.file))
        exit_action.triggered.connect(sys.exit)

        # сборка выпадающего меню
        self.addAction(info_action)
        self.addAction(trash_action)
        self.addSeparator()
        self.addAction(exit_action)

    def show_info(self):
        """
        Показывает краткую информацию по файлу
        """
        file_name = os.path.split(self.file)[1]
        pixmap = QPixmap(self.file)
        width = pixmap.width()
        height = pixmap.height()
        size = self.file_size()

        self.main.info.show_hint(
                '«{0}»: разрешение <font color="red"><b>{1}x{2}</b></font>, '
                'размер <font color="red"><b>{3}</b></font> {4}'.format(
                        file_name,
                        width,
                        height,
                        size[0],
                        size[1]
                )
        )

    def file_size(self):
        """
        Возвращает удобочитаемый размер файла
        """
        file = QFileInfo(self.file)
        size = file.size()

        if size < 1024:
            return str(size), 'байт'

        elif 1024 <= size < 1048576:
            return str(round(size / 1024, 1)), 'Кб'

        else:
            return str(round(size / 1048576, 1)), 'Мб'


class InfoLabel(QLabel):
    """
    Используется для показа сообщений в левом нижнем углу экрана
    """

    def __init__(self, main):
        super().__init__()

        self.main = main
        self.setMargin(5)
        self.resize(50, 30)
        self.move(40, self.main.frame_resolution_height - 60)
        self.setWindowFlags(Qt.WindowStaysOnTopHint |
                            Qt.FramelessWindowHint |
                            Qt.X11BypassWindowManagerHint)
        self.setMaximumWidth(self.main.frame_resolution_width - 80)

        self.font = QFont()
        self.font.setFamily("Liberation Serif")
        self.font.setPointSize(14)
        self.font.setItalic(True)
        self.setFont(self.font)

    def show_hint(self, text):
        """
        Показывает сообщение text
        """
        self.timer = QTimer()
        self.timer.setInterval(HINT_TIME * 1000)
        self.timer.timeout.connect(self.close_hint)
        self.setText(text)
        self.adjustSize()
        self.show()
        self.timer.start()

    def close_hint(self):
        """
        Выполняется при завершении работы таймера self.timer
        """
        self.hide()
        self.timer.deleteLater()
        self.close()


class Miniature(QLabel):
    """
    Отдельно взятая миниатюра с переписанными событиями щелчка мышью
    """

    def __init__(self, main):
        super().__init__()

        self.main = main
        self.path = ''
        self.original_file = ''
        self.miniature_width = main.miniature_width
        self.miniature_height = main.miniature_width

        # настройка выпадающего меню
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

    def mousePressEvent(self, event):
        """
        Установка картинки по щелчку на миниатюре
        """
        if event.button() == 1:
            self.main.current_image = self.original_file
            self.main.imageviewer.set_image(self.main.current_image,
                                            self.main.imageviewer.scale_default
                                            )

    def context_menu(self, point):
        """
        Вызвает выпадающее меню
        """
        self.main.popup.file = self.original_file
        self.main.popup.exec_(self.mapToGlobal(point))


class MiniaturesFolderHandler:
    """
    Создаёт/обновляет/удаляет временную папку для миниатюр
    """

    def __init__(self):
        self.folder = '/tmp/mopyqtiv.' + hashlib.sha1(os.urandom(8)).hexdigest()[:8]
        self.create_folder()

    def create_folder(self):
        """
        Удаляет старую и создаёт новую папку для миниатюр
        """
        self.remove_miniatures_folder()
        os.mkdir(self.folder)

    def remove_miniatures_folder(self):
        """
        Удаляет все относящиеся к программе временные папки в /tmp
        """
        for name in os.listdir('/tmp'):
            if 'mopyqtiv' in name:
                shutil.rmtree(os.path.join('/tmp', name))


class MiniaturesMaker:
    """
    Создаёт миниатюры для всех файлов в папке
    """

    def __init__(self, main):
        self.conn = first
        self.files = []
        self.folder = ''
        self.miniature_width = MINIATURE_WIDTH

    def make_one_miniature(self, file):
        """
        Создаёт одну миниатюру во временной папке
        """
        save_path = os.path.join(
                self.folder,
                os.path.split(file)[1]
        )

        try:
            with Image.open(file) as miniature:
                width = self.miniature_width
                ratio = width / miniature.size[0]
                height = miniature.size[1] * ratio
                miniature.thumbnail((width, height), Image.ANTIALIAS)
                miniature.save(save_path)

                # отправка сообщения о готовности миниатюры
                self.conn.send(['DONE', file, save_path])

        except EnvironmentError or OSError:
            return

    def create_miniatures(self):
        """
        Запуск создания миниатюр
        """
        pool = Pool()
        pool.map(self.make_one_miniature, self.files)
        # нормальное завершение
        pool.close()
        pool.join()

        # отправка сообщения о том, что все миниатюры сделаны
        self.conn.send('STOP')


class MiniaturesMakerThread(QThread):
    """
    Управляет созданием миниатюр в отдельном потоке
    """

    def __init__(self, main):
        super().__init__()
        self.main = main

    def run(self):
        self.main.miniatures_handler.miniatures_maker.files = self.main.filer.files
        self.main.miniatures_handler.miniatures_maker.folder = \
            self.main.miniatures_handler.miniatures_folder_handler.folder
        self.main.miniatures_handler.miniatures_maker.create_miniatures()


class MiniaturesToQueue(QThread):
    """
    Слушает сообщения о готовых миниатюрах
    и добавляет их в очередь на установку
    """

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.conn = second

    def run(self):
        while True:
            message = self.conn.recv()
            # когда все миниатюры в папке созданы
            if message == 'STOP':
                break

            # добавляет миниатюру в очередь
            if message[0] == 'DONE':
                done = (message[1], message[2])
                self.main.miniatures_handler.queue.append(done)
        self.main.miniatures_handler.miniatures_setter.complete = True


class MiniaturesSetter(QThread):
    """
    Устанавливает подготовленное изображение миниатюры
    на виджеты миниатюры в отдельном потоке
    Запускать после MiniaturesToQueue
    """

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.complete = False

    def run(self):
        # сброс переменной готовности
        self.complete = False

        while True:
            # если создание миниатюр окончено -> break
            if self.complete is True and len(self.main.miniatures_handler.queue) == 0:
                break
            try:
                # получаем пару (оригинальный_файл, миниатюра)
                new = self.main.miniatures_handler.queue.pop()

                # миниатюра готова -> установка на виджет
                for miniature in self.main.miniatures_handler.list_miniatures_widgets():
                    if miniature.original_file == new[0]:
                        # запись пути миниатюры
                        miniature.path = new[1]
                        # загрузка миниатюры на соответствующий виджет миниатюры
                        miniature.image.load(miniature.path)
                        # установка миниатюры
                        self.set_miniature_pixmap(miniature)

            # если в очереди пусто - ждёт дальше
            except IndexError:
                pass

    def set_miniature_pixmap(self, miniature):
        """
        Устанавливает pixmap на миниатюру miniature из переменной miniature.image
        """
        miniature.miniature_width = self.main.miniature_width
        miniature.miniature_height = miniature.miniature_width / miniature.image.width() * \
                                     miniature.image.height()

        miniature.setPixmap(
                miniature.image.scaled(
                        miniature.miniature_width,
                        miniature.miniature_height,
                        Qt.KeepAspectRatio,
                        Qt.FastTransformation
                )
        )


class MiniaturesArea(QWidget):
    """
    На этом виджете будут располагаться виджеты миниматюр
    """

    def __init__(self, main):
        super().__init__()

        self.main = main

        # настройка раскладки
        self.miniatures_layout = QVBoxLayout(self)
        self.miniatures_layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(self.miniatures_layout)


class MiniaturesScroller(QScrollArea):
    """
    Этот класс добавляет область прокрутки на панель миниатюр
    """

    def __init__(self, main):
        super().__init__(main)

        # наложение прокрутки
        self.miniatures_area = main.miniatures_area
        self.setWidget(self.miniatures_area)

        # настройка внешнего вида
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)


class MiniaturesHandler:
    """
    Управляет подготовкой, созданием, изменением размера, удалением миниатюр
    """

    def __init__(self, main):
        self.main = main
        self.miniatures_layout = self.main.miniatures_area.miniatures_layout

        # очередь готовых на установку миниатюр
        self.queue = []

        # создание объектов обработки миниатюр
        self.miniatures_maker = MiniaturesMaker(main)
        self.miniatures_maker_thread = MiniaturesMakerThread(main)
        self.miniatures_setter = MiniaturesSetter(main)
        self.miniatures_to_queue = MiniaturesToQueue(main)
        self.miniatures_folder_handler = MiniaturesFolderHandler()

        # после создания миниатюр -> проверка и чистка
        self.miniatures_setter.finished.connect(self.clean_miniatures_and_file_list)

    def prepare_miniatures(self):
        """
        Создаёт пустые виджеты миниатюр по кол-ву файлов изображений в папке
        """
        # очистка очереди миниатюр на установку
        self.queue = []

        for file in self.main.filer.files:
            miniature = Miniature(self.main)
            miniature.original_file = file
            miniature.image = QPixmap()
            self.main.miniatures_area.miniatures_layout.addWidget(miniature)

    def set_miniatures(self):
        """
        Управляет циклом создания миниатюр для текущей папки
        """
        # подготовка виджетов миниатюр в основном потоке
        self.prepare_miniatures()

        # обработка миниатюр в параллельных потоках
        self.miniatures_maker_thread.start()
        self.miniatures_to_queue.start()
        self.miniatures_setter.start()

    def clean_miniatures_and_file_list(self):
        """
        Удаляет виджеты миниатюр без картинок
        и очищает от них список файлов
        """
        for miniature in self.list_miniatures_widgets():
            # если для виджета миниатюра не была создана
            try:
                if miniature.path == '':
                    # удаляет из списка файлов
                    self.main.filer.files.remove(miniature.original_file)
                    # удаляет этот виджет
                    self.purge_miniature(miniature.original_file)

            # если это проблемная миниатюра
            except AttributeError:
                miniature.deleteLater()

        # теперь можно выбирать изображения
        self.main.filer.can_choose_file = True

    def resize_miniatures(self, coefficient):
        """
        Изменяет размер всех виджетов миниатюр с сохранением пропорций
        в зависимости от полученного коэффициента
        """
        for miniature in self.list_miniatures_widgets():

            # на запуске миниатюры ещё не созданы, поэтому отбой
            if miniature.image.isNull():
                return

            else:
                image = miniature.image
                miniature_width = miniature.miniature_width * coefficient
                miniature_height = miniature.miniature_height * coefficient
                miniature.resize(miniature_width,
                                 miniature_height
                                 )

                miniature.setPixmap(
                        image.scaled(miniature_width,
                                     miniature_height,
                                     Qt.KeepAspectRatio,
                                     Qt.FastTransformation
                                     )
                )

    def list_miniatures_widgets(self):
        """
        Возвращает список виджетов миниатюр
        """
        miniatures_widgets = (
            self.miniatures_layout.itemAt(i).widget()
            for i in range(self.miniatures_layout.count())
        )

        return miniatures_widgets

    def purge_miniature(self, file_for_delete):
        """
        Удаляет виджет миниатюры переданного файла
        """
        for miniature in self.list_miniatures_widgets():
            if miniature.original_file == file_for_delete:
                # попытка удаления миниатюры
                try:
                    os.remove(miniature.path)
                # если файла миниатюры нет
                except FileNotFoundError:
                    pass

                # удаление виджета миниатюры
                miniature.deleteLater()

        # если удаляется последнее в папке изображение
        if self.miniatures_layout.count() == 1:
            print('mopyqtiv: изображений в папке больше нет')
            sys.exit(0)

    def purge_all_miniatures(self):
        """
        Удаление всех виджетов миниатюр
        """
        for miniature in self.list_miniatures_widgets():
            miniature.deleteLater()
        self.main.miniatures_handler.miniatures_folder_handler.create_folder()

    def turn_miniature(self, image_path, degree):
        """
        Вращает и обновляет миниатюру переданного файла вправо,
        в зависимости от параметра degree
        """
        for miniature in self.list_miniatures_widgets():
            if miniature.original_file == image_path:
                self.main.turn_image(miniature.path, degree)
                miniature.image.load(miniature.path)
                self.miniatures_setter.set_miniature_pixmap(miniature)


class ImageViewer(QLabel):
    """
    Центральный виджет просмотрщика изображений
    """

    def __init__(self, main):
        super().__init__(main)

        self.main = main  # для обращений к классу главного окна
        self.ratio = 0  # отношения сторон картинки
        self.diagonal = 0  # диагональ текущего изображения
        self.rotation = 0  # запись текущего угла повората картинки
        self.is_scaled = False
        self.is_rotated = False
        self.is_magnified = False
        self.scale_default = 1.0
        self.current_scale = self.scale_default  # текущий коэффициент масштаба
        self.scale_step = SCALE_STEP
        self.scale_magnifier = SCALE_MAGNIFIER
        self.current_pixmap = QPixmap()  # pixmap текущего изображения
        self.current_pixmap.path = ''  # для запись пути текущей картинки
        self.position_img_x_new = 0
        self.position_img_y_new = 0
        self.position_img_x_max = 0
        self.position_img_y_max = 0
        self.current_img_width = 0
        self.current_img_height = 0
        self.position_img_x = 0
        self.position_img_y = 0

        # центровка изображения
        self.setAlignment(Qt.AlignCenter)

        # для отслеживания положения мыши
        self.setMouseTracking(True)

        # настройка выпадающего меню
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

    def set_image(self, image_path, scale):
        """
        Используется для установки/обновления изображения на центральном виджете
        """
        # для избежания повторной подгрузки изображения
        if self.current_pixmap.path != image_path \
                or self.main.is_image_altered is True:
            self.current_pixmap = QPixmap(image_path)
            self.main.is_image_altered = False

            # запись пути файла к текущему pixmap
            self.current_pixmap.path = image_path

        # проверка читаемости картинки
        if self.check_pixmap(self.current_pixmap) is False:
            return

        # запись размера текущей картинки в полную величину
        self.current_img_width = self.current_pixmap.width()
        self.current_img_height = self.current_pixmap.height()

        # сброс коэффициента масштабирования
        self.ratio = 1.0

        # подгонка размеров изображения под габариты окна,
        # если хотя бы одна из сторон больше соотвертствующей стороны окна
        # нужно, чтобы при первом показе картинка поместилась в окно
        if self.is_current_scale_bigger_than_frame() is True:
            # если картинка растянута по ширине более, чем окно
            if self.current_img_width / self.current_img_height > self.main.frame_ratio():
                self.ratio = self.main.frame_resolution_width / self.current_img_width
                self.current_img_width = self.main.frame_resolution_width
                self.current_img_height = self.current_img_height * self.ratio

            # если картинка растянута по высоте более, чем окно
            else:
                self.ratio = self.main.frame_resolution_height / self.current_img_height
                self.current_img_height = self.main.frame_resolution_height
                self.current_img_width = self.current_img_width * self.ratio

        # вычисление позиции для изображения
        self.position_img_x = self.main.frame_center_x - self.current_img_width / 2
        self.position_img_y = self.main.frame_center_y - self.current_img_height / 2

        if scale != 1.0:  # если применяется масштаб
            self.position_img_x = self.main.frame_center_x - self.current_img_width * scale / 2
            self.position_img_y = self.main.frame_center_y - self.current_img_height * scale / 2
            self.current_img_width *= scale
            self.current_img_height *= scale
            self.current_scale = scale
            self.ratio *= scale
            if self.is_magnified is False:
                self.is_scaled = True

        if scale == self.scale_default:  # если масштаб не применяется
            self.rotation = 0
            self.is_scaled = False
            self.is_rotated = False
            self.is_magnified = False
            self.current_scale = self.scale_default

        self.move(self.position_img_x, self.position_img_y)
        self.resize(self.current_img_width, self.current_img_height)
        self.setPixmap(
                self.current_pixmap.scaled(self.current_img_width,
                                           self.current_img_height,
                                           Qt.KeepAspectRatio,
                                           Qt.SmoothTransformation
                                           )
        )

        # ограничение на выход картинки за периметр окна
        self.limit_image_position()

        # изменятет заголовок окна под имя файла картинки
        self.main.change_title(os.path.split(self.main.current_image)[1])

    def rotate_widget(self, degree):
        """
        Поворачивает центральное изображение на degree градусов
        """
        self.rotation += degree
        # сброс счётчика при полном повороте
        if self.rotation >= 360 or self.rotation <= -360:
            self.rotation = 0
            return

        # подготовка объекта-трансформатора
        transform = QTransform()
        transform.rotate(self.rotation)
        rotated_pixmap = self.current_pixmap.transformed(transform,
                                                         Qt.SmoothTransformation
                                                         )

        # расчёт диагонали по текущему масштабу
        self.diagonal = (self.current_img_width ** 2 +
                         self.current_img_height ** 2
                         ) ** 0.5

        # расчёт положения центрального виджета
        self.position_img_x = self.main.frame_center_x - self.diagonal / 2
        self.position_img_y = self.main.frame_center_y - self.diagonal / 2

        # подготовка центрального виджета
        self.move(self.position_img_x, self.position_img_y)
        self.resize(self.diagonal,
                    self.diagonal
                    )

        # запись временного размера повёрнутой картинки в текущем положении
        img_width = rotated_pixmap.width() * self.ratio
        img_height = rotated_pixmap.height() * self.ratio

        self.setPixmap(
                rotated_pixmap.scaled(
                        img_width,
                        img_height,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                )
        )

        # вращение выполнено
        self.is_rotated = True

        # расчитать ограничение на перемещение
        self.limit_image_position()

    def check_pixmap(self, pixmap):
        """
        Проверка возможности открытия картинки
        Возвращает True, если картинку открыть можно
        Возвращает False, если открыть картинку не получится
        """
        if pixmap.isNull() == True:
            print('mopyqtiv: ошибка открытия изображения {0}'.format(pixmap.path),
                  '\nmopyqtiv: попытка открыть следующее изображение'
                  )
            # если открыть не удаётся, тут же пробует открыть следующее изображение
            self.main.next_image()
            # если битое изображение не поменялось, значит картинок больше нет
            if pixmap.path == self.main.current_image:
                print('mopyqtiv: не удаётся найти изображения в папке')
                sys.exit(0)

            # удаление файла нечитаемой картинки из списка изображений текущей папки
            try:
                self.main.filer.files.remove(pixmap.path)
            except ValueError:
                pass

            return False
        else:
            return True

    def limit_image_position(self):
        """
        Установка границ на перемещение увеличенного изображения
        """
        if self.is_rotated is False:
            self.position_img_x_max = self.main.frame_resolution_width - self.current_img_width
            self.position_img_y_max = self.main.frame_resolution_height - self.current_img_height

        # в случае вращения
        elif self.is_rotated is True:
            self.position_img_x_max = self.main.frame_resolution_width - self.diagonal
            self.position_img_y_max = self.main.frame_resolution_height - self.diagonal

    def check_position_img_max(self):
        """
        Блокировка выхода картинки за габариты окна
        """
        if self.position_img_x_new < self.position_img_x_max:
            self.position_img_x_new = self.position_img_x_max
        if self.position_img_y_new < self.position_img_y_max:
            self.position_img_y_new = self.position_img_y_max

        # ограничение при перемещении изображения мышью
        if self.current_img_width > self.main.frame_resolution_width:
            if self.position_img_x_new > 0:
                self.position_img_x_new = 0
        else:
            self.position_img_x_new = self.position_img_x

        if self.current_img_height > self.main.frame_resolution_height:
            if self.position_img_y_new > 0:
                self.position_img_y_new = 0
        else:
            self.position_img_y_new = self.position_img_y

    def full_size_image_scale(self):
        """
        Возвращает значение масштаба изображения для текущего размера окна,
        при котором картинка полностью поместится в окне с сохранением попорций
        """
        coefficient_x = 0
        coefficient_y = 0

        if self.current_pixmap.width() > self.main.frame_resolution_width:
            coefficient_x = self.current_pixmap.width() / self.main.frame_resolution_width
        if self.current_pixmap.height() > self.main.frame_resolution_height:
            coefficient_y = self.current_pixmap.height() / self.main.frame_resolution_height

        return max(coefficient_x, coefficient_y)

    def is_current_scale_bigger_than_frame(self):
        """
        Возвращает True, если хотя бы одна из сторон изображения
        больше, чем текущий размер окна
        Возвращает False, если размер изображения полностью помещается
        в текущие габариты окна
        """
        if self.current_img_width > self.main.frame_resolution_width \
                or self.current_img_height > self.main.frame_resolution_height:
            return True
        else:
            return False

    def set_image_full_size(self):
        """
        Устанавливает размер текущего изображения 1:1
        """
        scale = self.full_size_image_scale()
        self.set_image(self.main.current_image, scale)

    def increase_in_size(self):
        """
        Увеличивает размер текущего изображения
        на один шаг, равный SCALE_STEP
        """
        if self.current_scale < 10:
            self.current_scale += self.scale_step
            self.set_image(self.main.current_image, self.current_scale)

        # сброс счётчика поворота
        self.rotation = 0

    def scale_back(self):
        """
        Уменьшает размер текущего изображения
        на один шаг, равный SCALE_STEP
        """
        if self.current_scale > 0.5:
            self.current_scale -= self.scale_step
            self.set_image(self.main.current_image, self.current_scale)

        # сброс счётчика поворота
        self.rotation = 0

    def magnifier(self):
        """
        Режим «Лупа»
        Масштаб зависит от глобальной переменной SCALE_MAGNIFIER
        """
        self.is_scaled = False
        self.is_magnified = True
        self.set_image(self.main.current_image, self.scale_magnifier)

    def context_menu(self, point):
        """
        Вызвает выпадающее меню
        """
        self.main.popup.file = self.main.current_image
        self.main.popup.exec_(self.mapToGlobal(point))


class MainWindow(QWidget):
    """
    Виджет главного окна
    Связующий класс
    """

    def __init__(self, start_image):
        super().__init__()

        self.binds = []
        self.is_image_altered = False
        self.current_image = os.path.abspath(start_image)
        self.program_icon = QIcon.fromTheme('pixelart-trace')
        self.trash_path = os.path.expanduser('~') + '/.local/share/Trash'
        self.miniature_width = MINIATURE_WIDTH
        self.miniature_current_width = self.miniature_width
        self.screen_resolution = QApplication.desktop().screenGeometry()
        # координаты центра окна
        self.frame_center_x = self.screen_resolution.width() / 2
        self.frame_center_y = self.screen_resolution.height() / 2
        self.frame_resolution_width = self.screen_resolution.width()
        self.frame_resolution_height = self.screen_resolution.height()

        # доступные клавиши для привязывания сортировочных папок
        self.keys_for_bindings = (Qt.Key_Z, Qt.Key_X, Qt.Key_C, Qt.Key_V, Qt.Key_B,
                                  Qt.Key_N, Qt.Key_M, Qt.Key_A, Qt.Key_S, Qt.Key_D,
                                  Qt.Key_F, Qt.Key_G, Qt.Key_H, Qt.Key_J, Qt.Key_K,
                                  Qt.Key_L, Qt.Key_W, Qt.Key_E, Qt.Key_R, Qt.Key_T,
                                  Qt.Key_Y, Qt.Key_U, Qt.Key_I, Qt.Key_O, Qt.Key_P)

        # текущее положение курсора
        self.current_cursor_position_x = 0
        self.current_cursor_position_y = 0

        # включает режим отслеживания положения мыши
        self.setMouseTracking(True)

        # настройка главного окна
        self.main_palette = QPalette()  # палитра главного окна
        self.setAutoFillBackground(True)  # позволяет установить фон QWidget
        self.background_color = QColor()
        self.background_color.setNamedColor(BACKGROUND_COLOR)
        self.set_background(self.background_color)
        self.change_title(os.path.split(start_image)[1])

        # раскрывает главное окно на весь экран
        self.move(0, 0)
        self.resize(self.frame_resolution_width, self.frame_resolution_height)

        # установка иконки приложения
        self.setWindowIcon(self.program_icon)

        # главное окно без рамки
        if WITHOUT_BORDER is True:
            self.setWindowFlags(Qt.FramelessWindowHint)

        # создание экземпляров классов
        self.filer = Filer()
        self.info = InfoLabel(self)
        self.popup = PopupMenu(self)
        self.imageviewer = ImageViewer(self)
        self.miniatures_area = MiniaturesArea(self)
        self.miniatures_handler = MiniaturesHandler(self)
        self.miniatures_scroller = MiniaturesScroller(self)

        # настройка области прокрутки панели миниатюр
        self.miniatures_scroller.focusNextPrevChild(True)
        self.miniatures_scroller.hide()

        # создаёт список картинок в текущей папке
        self.filer.list_folder(self.filer.current_folder)

        # создание и установка миниатюр
        self.miniatures_handler.set_miniatures()

        # регистрация функции удаления временных файлов при выходе
        atexit.register(self.at_close)

    def frame_ratio(self):
        """
        Возвращает коэффициент отношения сторон текущего окна
        """
        return self.frame_resolution_width / self.frame_resolution_height

    def set_background(self, color):
        """
        Установка фона главного окна
        """
        self.main_palette.setColor(QPalette.Background, color)
        self.setPalette(self.main_palette)

    def change_title(self, name):
        """
        Изменяет заголовок окна
        """
        self.setWindowTitle('Mouse oriented PyQt5 image viewer: {0}'.format(name))

    def trash(self, file_path):
        """
        Отправляет указанную картинку в корзину
        """
        # TODO: удаление для оффтопика
        if os.path.isdir(self.trash_path):

            # при переносе в корзину текущего изображения
            if file_path == self.current_image \
                    and file_path != self.filer.files[-1]:
                self.next_image()

            for_delete_full_path = file_path
            for_delete_file_name = os.path.split(for_delete_full_path)[1]

            # перемещение файла в корзину
            destination = self.trash_path + '/files/' + for_delete_file_name
            shutil.move(for_delete_full_path, destination)

            # создание файла описания удалённого файла
            date = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time()))
            info_file = self.trash_path + '/info/' + for_delete_file_name + '.trashinfo'
            info = '[Trash Info]\nPath={0}\nDeletionDate={1}\n'.format(for_delete_full_path, date)
            with open(info_file, 'w') as info_file:
                info_file.write(info)

            # удаление файла картинки из списка изображений текущей папки
            try:
                self.filer.files.remove(for_delete_full_path)
            except ValueError:
                pass

            # удаление его миниатюры
            self.miniatures_handler.purge_miniature(for_delete_full_path)

            self.info.show_hint('Файл «{0}» перемещен в корзину'.format(for_delete_file_name))

            if for_delete_full_path == self.current_image:
                self.next_image()

    def next_image(self):
        """
        Установка следующего в списке изображения
        """
        try:
            current_index = self.filer.files.index(self.current_image)
        # если файл отсутствует в списке изображений, пробует открыть первое
        except ValueError:
            current_index = 0

        # если изображение в папке нет -> выход
        if len(self.filer.files) == 0:
            print('mopyqtiv: не удаётся найти изображения в папке')
            sys.exit(0)

        # если всё нормально -> следующее изображение
        if current_index < len(self.filer.files) - 1:
            self.current_image = self.filer.files[current_index + 1]
            self.imageviewer.set_image(self.current_image,
                                       self.imageviewer.scale_default
                                       )

    def previous_image(self):
        """
        Установка предыдующего в списке изображения
        """
        try:
            current_index = self.filer.files.index(self.current_image)
        # если файл отсутствует в списке изображений -> выход
        except ValueError:
            print('mopyqtiv: не удаётся найти изображения в папке')
            sys.exit(0)

        # если всё нормально -> предыдующее изображение
        if current_index > 0:
            self.current_image = self.filer.files[current_index - 1]
            self.imageviewer.set_image(self.current_image, self.imageviewer.scale_default)

    def turn_image(self, image_path, degree):
        """
        Поворачивает изображение image_path
        в зависимости от параметра degree
        """
        with Image.open(image_path) as image:
            image = image.rotate(degree, resample=Image.BICUBIC, expand=True)
            image.save(image_path)

    def turn_right(self, image_path):
        """
        Вращает изобажение image_path и его миниатюру вправо
        """
        self.turn_image(image_path, -90)
        self.is_image_altered = True
        self.imageviewer.set_image(image_path, self.imageviewer.scale_default)
        self.miniatures_handler.turn_miniature(image_path, -90)

    def turn_left(self, image_path):
        """
        Вращает изобажение image_path и его миниатюру влево
        """
        self.turn_image(image_path, 90)
        self.is_image_altered = True
        self.imageviewer.set_image(image_path, self.imageviewer.scale_default)
        self.miniatures_handler.turn_miniature(image_path, 90)

    def choose_file(self):
        """
        Запускает диалог выбора изображения
        """
        if self.filer.can_choose_file is False:
            print('mopyqtiv: Вы не можете выбирать изображения,\n',
                  '\tпока создаются миниатюры для текущей папки'
                  )

            return

        file_path = self.filer.choose_file()

        if file_path == '':
            return

        self.filer.current_folder = os.path.split(file_path)[0]
        self.current_image = file_path
        self.filer.list_folder(self.filer.current_folder)
        self.imageviewer.set_image(file_path, self.imageviewer.scale_default)
        self.miniatures_handler.purge_all_miniatures()
        self.miniatures_handler.set_miniatures()
        self.filer.can_choose_file = False

    def bind_key(self, key):
        """
        Привязывает на клавишу путь до папки (выбирается через диалог)
        """
        bind = Bind()
        bind.key = key()
        bind.path = self.filer.choose_folder(os.getcwd())

        if bind.path == '':
            return
        else:
            self.binds.append(bind)
            self.info.show_hint('Клавиша привязана к «{0}»'.format(bind.path))

    def unbind_key(self, key):
        """
        Отвязывает папку от клавиши
        """
        for bind in self.binds:
            if bind.key == key():
                self.binds.remove(bind)
                self.info.show_hint('Клавиша освобождена')

    def work_bind(self, event):
        """
        Обрабатывает привязку/отвязку папок от клавиш,
        а также перемещение изображений
        """
        for bind in self.binds:
            if event.key() == bind.key \
                    and event.modifiers() == Qt.NoModifier:
                bind.move(self.current_image)

                # уведомление о перемещении
                file_name = os.path.split(self.current_image)[1]
                self.info.show_hint('Файл «{0}» перемещен в «{1}»'.format(
                        file_name, bind.path)
                )

                self.miniatures_handler.purge_miniature(self.current_image)
                self.next_image()
                return

        if event.modifiers() == Qt.NoModifier:
            self.bind_key(event.key)

        elif event.modifiers() == Qt.ControlModifier:
            self.unbind_key(event.key)

    def try_hand_cursor(self, event):
        """
        Меняет указатель мыши стрелку на руку,
        если картинка больше габаритов окна, и наоборот
        """
        # в режиме перетаскивания
        if self.imageviewer.is_current_scale_bigger_than_frame() is True \
                and event.buttons() == Qt.LeftButton:
            self.setCursor(Qt.ClosedHandCursor)

        # в режиме готовности к перетаскиванию
        elif self.imageviewer.is_current_scale_bigger_than_frame() is True:
            self.setCursor(Qt.OpenHandCursor)

        # во всех остальных случаях
        else:
            self.setCursor(Qt.ArrowCursor)

    def keyPressEvent(self, event):
        """
        Обработка нажатий клавиш клавиатуры
        """
        # с модификатором control
        if event.modifiers() == Qt.ControlModifier:

            if event.key() == Qt.Key_R:
                self.turn_right(self.current_image)

            elif event.key() == Qt.Key_L:
                self.turn_left(self.current_image)

        elif event.key() == Qt.Key_Right or event.key() == Qt.Key_Down:
            self.next_image()

        elif event.key() == Qt.Key_Left or event.key() == Qt.Key_Up:
            self.previous_image()

        elif event.key() == Qt.Key_Delete:
            self.trash(self.current_image)

        elif event.key() == Qt.Key_Backspace:
            self.choose_file()

        elif event.key() == Qt.Key_Escape or event.key() == Qt.Key_Q:
            sys.exit(0)

        # обработчик сортировки по горячим клавишам
        elif event.key() in self.keys_for_bindings:
            self.work_bind(event)

        event.accept()

    def mousePressEvent(self, event):
        """
        Обработка нажатий кнопок мыши
        """
        # обработка щелчка левой кнопки мыши
        if event.buttons() == Qt.LeftButton:
            # запуск режима лупы
            if self.imageviewer.is_scaled is not True \
                    or self.imageviewer.is_current_scale_bigger_than_frame() is False:
                self.imageviewer.magnifier()
                self.setCursor(Qt.BlankCursor)

            # обработка перемещения увеличенного изображения
            if self.imageviewer.is_scaled is True:
                self.current_cursor_position_x = QCursor.pos().x()
                self.current_cursor_position_y = QCursor.pos().y()
                self.try_hand_cursor(event)

        # установка изображения в полный размер при нажатии на колёсико
        if event.buttons() == Qt.MiddleButton:
            # если изображение способно к увеличению в полный размер
            if self.imageviewer.is_scaled is False \
                    and self.imageviewer.full_size_image_scale() > 1.0:
                self.imageviewer.set_image_full_size()
                self.try_hand_cursor(event)

            # обработка выхода из режима увеличения
            elif self.imageviewer.is_scaled is True:
                self.imageviewer.is_scaled = False
                self.imageviewer.current_scale = self.imageviewer.scale_default
                self.imageviewer.set_image(self.current_image, self.imageviewer.scale_default)
                self.try_hand_cursor(event)

            # если изображение не способно к полному размеру - ничего не делать
            else:
                event.ignore()
                return

        event.accept()

    def mouseMoveEvent(self, event):
        """
        Обработка событий, связанных с положением или перемещением курсора мыши
        """
        # перемещает картинку в зависимости от положения курсора
        # и параметров scale_magnifier и MAGNIFIER_MOVE_BOOST
        if self.imageviewer.is_magnified is True:
            self.imageviewer.position_img_x_new = self.imageviewer.position_img_x - \
                                                  (QCursor.pos().x() - self.frame_center_x) * \
                                                  self.imageviewer.scale_magnifier * \
                                                  MAGNIFIER_MOVE_BOOST

            self.imageviewer.position_img_y_new = self.imageviewer.position_img_y - \
                                                  (QCursor.pos().y() - self.frame_center_y) * \
                                                  self.imageviewer.scale_magnifier * \
                                                  MAGNIFIER_MOVE_BOOST

            # ограничение выхода за габариты окна
            self.imageviewer.check_position_img_max()

            # перемещение увеличенного изображения
            self.imageviewer.move(self.imageviewer.position_img_x_new,
                                  self.imageviewer.position_img_y_new
                                  )

        # перемещение изображения при масштабировании
        if self.imageviewer.is_scaled is True and event.buttons() == Qt.LeftButton:
            # вычисление разницы старого и нового положения курсора
            differens_x = QCursor.pos().x() - self.current_cursor_position_x
            differens_y = QCursor.pos().y() - self.current_cursor_position_y

            # расчёт нового положения картинки
            self.imageviewer.position_img_x_new = self.imageviewer.position_img_x + differens_x
            self.imageviewer.position_img_y_new = self.imageviewer.position_img_y + differens_y

            # проверка выхода изображения за границы
            self.imageviewer.check_position_img_max()

            # сохранение текущей позиции изображения
            self.imageviewer.position_img_x = self.imageviewer.position_img_x_new
            self.imageviewer.position_img_y = self.imageviewer.position_img_y_new

            # установка увеличенного изображения в расчётное положение
            self.imageviewer.move(self.imageviewer.position_img_x_new,
                                  self.imageviewer.position_img_y_new
                                  )

            # сохранение текущего положения курсора
            self.current_cursor_position_x = QCursor.pos().x()
            self.current_cursor_position_y = QCursor.pos().y()

        # появление панели миниатюр в зависимости от положения мыши
        if qApp.mouseButtons() != Qt.LeftButton:
            # 50 - кол-во пикселей от правого края,
            # заходя за которые курсором мыши, появится панель миниатюр
            if QCursor.pos().x() > self.pos().x() + self.frame_resolution_width - 50:
                self.miniatures_scroller.show()
            if QCursor.pos().x() < self.pos().x() + self.frame_resolution_width - \
                    self.miniature_current_width:
                self.miniatures_scroller.hide()

        event.accept()

    def mouseReleaseEvent(self, event):
        """
        Обработка снятия нажатия левой кнопки мыши
        """
        if event.button() == Qt.LeftButton:
            # снятие лупы
            if self.imageviewer.is_scaled is not True:
                # возвращает изображение на место
                self.imageviewer.set_image(self.current_image,
                                           self.imageviewer.scale_default
                                           )

                self.try_hand_cursor(event)

            # при прекращении перетаскивания
            else:
                self.try_hand_cursor(event)

            event.accept()

        else:
            event.ignore()

    def wheelEvent(self, event):
        """
        Смена изображения по колёсику мыши
        """
        step = event.angleDelta().y()  # -120 колёсико на себя, 120 - от себя
        if self.miniatures_scroller.isVisible() is True:
            event.ignore()
            return

        # увеличение масштаба колёсиком мыши + ConrolModifier
        elif step > 0 and event.modifiers() == Qt.ControlModifier:
            self.imageviewer.increase_in_size()
            self.try_hand_cursor(event)

        # уменьшение масштаба колёсиком мыши + ConrolModifier
        elif step < 0 and event.modifiers() == Qt.ControlModifier:
            self.imageviewer.scale_back()
            self.try_hand_cursor(event)

        # вращение изображения + ShiftModifier
        elif step > 0 and event.modifiers() == Qt.ShiftModifier:
            self.imageviewer.rotate_widget(-ROTATE_STEP)
            self.try_hand_cursor(event)

        # вращение изображения + ShiftModifier
        elif step < 0 and event.modifiers() == Qt.ShiftModifier:
            self.imageviewer.rotate_widget(ROTATE_STEP)
            self.try_hand_cursor(event)

        # если модификаторов не зажато
        else:
            if step > 0:
                self.previous_image()

            elif step < 0:
                self.next_image()

            # восстановление курсора
            self.setCursor(Qt.ArrowCursor)

        event.accept()

    def resizeEvent(self, event):
        """
        Срабатывает при изменении размера окна
        """
        # настройка основной картинки
        self.frame_center_x = self.frameSize().width() / 2
        self.frame_center_y = self.frameSize().height() / 2
        self.frame_resolution_width = self.frameSize().width()
        self.frame_resolution_height = self.frameSize().height()
        self.imageviewer.set_image(self.current_image, self.imageviewer.scale_default)

        # настройка размера и положения миниатюр
        coefficient = self.frameSize().width() / self.screen_resolution.width()
        self.miniature_current_width = coefficient * self.miniature_width
        self.miniatures_handler.resize_miniatures(coefficient)
        self.miniatures_scroller.move(self.frame_resolution_width - (self.miniature_current_width + 36), 0)
        self.miniatures_scroller.resize(self.miniature_current_width + 36, self.frame_resolution_height)

        event.accept()

    def at_close(self):
        """
        Очистка временной папки с миниатюрами при выходе
        """
        self.miniatures_handler.miniatures_folder_handler.remove_miniatures_folder()


def mopyqtiv_help():
    print('\nmopyqtiv - программа для просмотра изображений, написанная на python,'
          '\nс использованием библиотек PyQt пятой серии и PIL.'
          '\n\nИспользование:'
          '\n\tmopyqtiv [-h] [файл]'
          '\n\t-h\tключ для показа этого сообщения'
          '\n\tфайл\tпрограмма может открыть изображения следующих форматов:'
          '\n\t\t*.bmp *.pbm *.pgm *.ppm *.xbm *.xpm *.jpg *.jpeg *.png *.gif')


if __name__ == '__main__':
    if '-h' in sys.argv:
        mopyqtiv_help()
        sys.exit(0)

    elif len(sys.argv) > 2 or len(sys.argv) < 2:
        print('Для запуска приложения mopyqtiv укажите открываемое изображение.',
              '\nДля справки запустите с параметром -h')
        sys.exit(0)

    else:
        first, second = Pipe()
        app = QApplication(sys.argv)
        mainwindow = MainWindow(sys.argv[1])
        mainwindow.show()
        sys.exit(app.exec_())
