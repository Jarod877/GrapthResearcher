import sys
import os
import pickle
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QWidget, QVBoxLayout,
    QTableWidget, QTableWidgetItem, QMenuBar, QPushButton, QHBoxLayout,
    QHeaderView, QFileDialog, QCheckBox, QDialog, QLabel, QLineEdit,
    QSizePolicy, QAbstractItemView, QMessageBox, QComboBox
)
from PySide6.QtGui import QAction, QIcon, QDoubleValidator
from PySide6.QtCore import Qt, QSize
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
import numpy as np

IS_SAVE = True  # Флаг, показывающий, сохранен ли проект
UNITS = ['y', 'ln(y)', 'lg(y)']

class GraphData:
    """Класс для хранения данных о каждом графике"""
    def __init__(self, data: pd.DataFrame, file_path: str, show: bool = True, scalable: bool = True):
        self.data = data  # Данные из файла
        self.file_path = file_path  # Путь к файлу
        self.file_name = file_path.split("/")[-1].split(".")[0]  # Название файла без расширения
        self.show = show  # Показывать ли график
        self.scalable = scalable  # Возможность масштабирования
        self.graph_window = None  # Окно для отображения графика
        self.graph_table = None  # Объект таблицы-списка графиков
        self.graph_field = None  # Объект поля графика
        self.graphics_visible = []  # Какие из графиков будут показываться
        self.scale_x_min = 273
        self.scale_x_max = 2000
        self.scale_y_min = 0
        self.scale_y_max = 0
        self.units_list = UNITS
        self.unit_initial = 0
        self.unit_final = 0
        self.unit_to = [self.u_1_1, self.u_2_1, self.u_3_1]
        self.unit_from = [self.u_1_1, self.u_1_2, self.u_1_3]

    def __setattr__(self, name, value):
        global IS_SAVE
        IS_SAVE = False
        super().__setattr__(name, value)

    def __getstate__(self):
        """Определяет, какие данные будут сериализованы."""
        state = self.__dict__.copy()
        state['graph_window'] = None  # Устанавливаем None вместо ссылки на окно
        state['graph_table'] = None
        state['graph_field'] = None
        return state

    def __setstate__(self, state):
        """Определяет, как объект восстанавливается из сериализованных данных."""
        self.__dict__.update(state)
        self.graph_window = None  # После восстановления, окно не существует
        self.graph_table = None  # Объект таблицы-списка графиков
        self.graph_field = None  # Объект поля графика

    # def __repr__(self):
    #     return f"GraphData({self.file_name}, show={self.show}, scalable={self.scalable})"

    def u_1_1(self, y):
        return y

    def u_1_2(self, y):
        # print(y)
        return np.where(y > 0, np.log(y), -1e10)

    def u_1_3(self, y):
        # print(y)
        return np.where(y > 0, np.log10(y), -1e10)

    def u_2_1(self, y):
        return np.exp(y)

    def u_3_1(self, y):
        return np.power(10, y)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        global UNITS

        # Заголовок и размеры окна
        self.setWindowTitle("Grapth Researcher by SlobodovReactor")
        self.setGeometry(300, 200, 1000, 400)

        # Главная структура данных для хранения графиков
        self.graphs = []

        self.current_grapth_index = None  # Выделенный график для изменения масштаба
        self.project_name = None  # Путь и имя для файла проекта

        # Задаем общий масштаб всех графиков
        self.scale_x_min = 999999999999
        self.scale_x_max = -999999999999
        self.scale_y_min = 999999999999
        self.scale_y_max = -999999999999

        # Меню
        self.create_menu()

        # Сплиттер и основные элементы
        splitter = QSplitter(Qt.Horizontal)
        left_widget = QWidget()  # Левая колонка (для графиков в будущем)

        left_layout = QVBoxLayout(left_widget)
        left_layout.setAlignment(Qt.AlignTop)

        # Строка для ввода диапазона оси X
        x_range_layout = QHBoxLayout()
        # Создаем и добавляем элементы в строку ввода диапазона Х
        x_range_label = QLabel("Ось Х (общий диапазон):")
        x_range_layout.addWidget(x_range_label)
        self.x_min_input = QLineEdit()
        self.x_min_input.setValidator(QDoubleValidator())  # Ограничение на ввод только чисел
        x_range_layout.addWidget(self.x_min_input)
        x_dash_label = QLabel("-")
        x_range_layout.addWidget(x_dash_label)
        self.x_max_input = QLineEdit()
        self.x_max_input.setValidator(QDoubleValidator())  # Ограничение на ввод только чисел
        x_range_layout.addWidget(self.x_max_input)

        apply_button1_1 = QPushButton("Сохранить")
        apply_button1_1.clicked.connect(self.set_the_scale_1_1)
        x_range_layout.addWidget(apply_button1_1)

        # Добавляем строку ввода диапазона в левую панель
        left_layout.addLayout(x_range_layout)

        # Строка для ввода диапазона оси Y
        y_range_layout = QHBoxLayout()
        # Создаем и добавляем элементы в строку ввода диапазона Y
        y_range_label = QLabel("Ось Y (общий диапазон):")
        y_range_layout.addWidget(y_range_label)
        self.y_min_input = QLineEdit()
        self.y_min_input.setValidator(QDoubleValidator())  # Ограничение на ввод только чисел
        y_range_layout.addWidget(self.y_min_input)
        y_dash_label = QLabel("-")
        y_range_layout.addWidget(y_dash_label)
        self.y_max_input = QLineEdit()
        self.y_max_input.setValidator(QDoubleValidator())  # Ограничение на ввод только чисел
        y_range_layout.addWidget(self.y_max_input)

        apply_button1_2 = QPushButton("Сохранить")
        apply_button1_2.clicked.connect(self.set_the_scale_1_2)
        y_range_layout.addWidget(apply_button1_2)

        # Добавляем строку ввода диапазона в левую панель
        left_layout.addLayout(y_range_layout)

        # Кнопки "Сохранить" и "Сбросить"
        button_layout = QHBoxLayout()
        apply_button = QPushButton("Сохранить")
        apply_button.clicked.connect(self.set_common_scale)
        reset_button = QPushButton("Сбросить")
        reset_button.clicked.connect(self.set_default_scale)
        y_button = QPushButton("Подогнать Y")
        y_button.clicked.connect(self.set_y_scale)
        button_layout.addWidget(apply_button)
        button_layout.addWidget(reset_button)
        button_layout.addWidget(y_button)
        left_layout.addLayout(button_layout)

        self.container_widget = QWidget()
        self.container_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.container_widget.setVisible(False)  # Скрываем контейнер по умолчанию
        container_layout = QVBoxLayout(self.container_widget)
        container_layout.setAlignment(Qt.AlignTop)

        # Создаем горизонтальный лейаут для заголовка и текстового поля
        current_graph_layout = QHBoxLayout()
        example_label = QLabel("Текущий график:")
        current_graph_layout.addWidget(example_label)

        # Пустое текстовое поле, содержание которого можно обновлять
        self.current_graph_name_label = QLabel("")
        current_graph_layout.addWidget(self.current_graph_name_label)

        # Добавляем горизонтальный лейаут в контейнер
        container_layout.addLayout(current_graph_layout)

        # Строка для ввода диапазона оси X
        x1_range_layout = QHBoxLayout()
        x1_range_label = QLabel("Ось Х:")
        x1_range_layout.addWidget(x1_range_label)
        self.x1_min_input = QLineEdit()
        self.x1_min_input.setValidator(QDoubleValidator())  # Ограничение на ввод только чисел
        x1_range_layout.addWidget(self.x1_min_input)
        x1_dash_label = QLabel("-")
        x1_range_layout.addWidget(x1_dash_label)
        self.x1_max_input = QLineEdit()
        self.x1_max_input.setValidator(QDoubleValidator())  # Ограничение на ввод только чисел
        x1_range_layout.addWidget(self.x1_max_input)

        apply_button2_1 = QPushButton("Сохранить")
        apply_button2_1.clicked.connect(self.set_the_scale_2_1)
        x1_range_layout.addWidget(apply_button2_1)

        container_layout.addLayout(x1_range_layout)  # Добавляем строку ввода диапазона Х в контейнер

        # Строка для ввода диапазона оси Y
        y1_range_layout = QHBoxLayout()
        y1_range_label = QLabel("Ось Y:")
        y1_range_layout.addWidget(y1_range_label)

        self.y1_min_input = QLineEdit()
        self.y1_min_input.setValidator(QDoubleValidator())  # Ограничение на ввод только чисел
        y1_range_layout.addWidget(self.y1_min_input)

        y1_dash_label = QLabel("-")
        y1_range_layout.addWidget(y1_dash_label)
        self.y1_max_input = QLineEdit()
        self.y1_max_input.setValidator(QDoubleValidator())  # Ограничение на ввод только чисел
        y1_range_layout.addWidget(self.y1_max_input)

        apply_button2_2 = QPushButton("Сохранить")
        apply_button2_2.clicked.connect(self.set_the_scale_2_2)
        y1_range_layout.addWidget(apply_button2_2)

        container_layout.addLayout(y1_range_layout)  # Добавляем строку ввода диапазона Y в контейнер

        y2_range_layout = QHBoxLayout()
        y2_range_label = QLabel("Изменение размерности Y:")
        y2_range_layout.addWidget(y2_range_label)

        self.unit_list_1 = QComboBox()
        self.unit_list_1.addItems(UNITS)  # Добавляем пункты
        self.unit_list_1.setCurrentIndex(0)  # Устанавливаем первый пункт как выбранный (по умолчанию)
        y2_range_layout.addWidget(self.unit_list_1)
        # Пример реакции на изменение выбора
        self.unit_list_1.currentIndexChanged.connect(self.on_unit_list_1)

        y3_range_label = QLabel("->")
        y2_range_layout.addWidget(y3_range_label)

        self.unit_list_2 = QComboBox()
        self.unit_list_2.addItems(UNITS)  # Добавляем пункты
        self.unit_list_2.setCurrentIndex(0)  # Устанавливаем первый пункт как выбранный (по умолчанию)
        y2_range_layout.addWidget(self.unit_list_2)
        # Пример реакции на изменение выбора
        self.unit_list_2.currentIndexChanged.connect(self.on_unit_list_2)

        container_layout.addLayout(y2_range_layout)  # Добавляем строку ввода диапазона Y в контейнер

        # Кнопки "Сохранить" и "Сбросить"
        button_layout1 = QHBoxLayout()
        apply_button1 = QPushButton("Сохранить")
        apply_button1.clicked.connect(self.set_the_scale)
        reset_button1 = QPushButton("Сбросить")
        reset_button1.clicked.connect(self.reset_the_scale)
        y_button1 = QPushButton("Подогнать Y")
        y_button1.clicked.connect(self.set_y_scale1)
        button_layout1.addWidget(apply_button1)
        button_layout1.addWidget(reset_button1)
        button_layout1.addWidget(y_button1)
        container_layout.addLayout(button_layout1)  # Добавляем кнопки в контейнер

        # Добавляем контейнер в левую панель
        left_layout.addWidget(self.container_widget)


        right_widget = QWidget()  # Правая колонка (таблица и кнопка)
        right_layout = QVBoxLayout(right_widget)
        self.table = QTableWidget()  # Таблица для правой колонки
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)  # Разрешаем выделение только одной строки
        self.setup_table()
        right_layout.addWidget(self.table)

        # Кнопка для добавления графика
        add_button = QPushButton()
        add_button.setIcon(QIcon.fromTheme("list-add"))
        add_button.setIconSize(QSize(48, 48))
        add_button.setFixedSize(80, 80)
        add_button.setStyleSheet("border-radius: 40px;")
        add_button.clicked.connect(self.add_graph)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(add_button)
        right_layout.addLayout(button_layout)

        # Установка сплиттера и центрального виджета
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(splitter)
        self.setCentralWidget(central_widget)

    def on_unit_list_1(self, index):
        # Перерисовать исходя из смены единиц
        gr = self.graphs[self.current_grapth_index]
        gr.unit_initial = index
        self.rewrite_graph(gr)

        
        # uuuu

        # self.graphs[self.current_grapth_index].graph_window.plot_widget.setXRange(x_min, x_max)

    def on_unit_list_2(self, index):
        # Перерисовать исходя из смены единиц
        gr = self.graphs[self.current_grapth_index]
        gr.unit_final = index
        gr.graph_field.setLabel('left', gr.units_list[gr.unit_final], units='')  # Меняем подпись для оси Y
        self.rewrite_graph(gr)


    def closeEvent(self, event):
        """ Срабатывает при закрытии главного окна """
        global IS_SAVE
        if IS_SAVE is True:
            event.accept()  # Подтверждаем закрытие
            return
        reply = QMessageBox.question(
            self,
            "Подтверждение выхода",
            "Проект не сохранен, уверены, что хотите выйти?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()  # Подтверждаем закрытие
        else:
            event.ignore()  # Отменяем закрытие

    def set_the_scale_1_1(self):
        try:
            self.scale_x_min = float(self.x_min_input.text())
            self.scale_x_max = float(self.x_max_input.text())
            # Перерисовать графики исходя из этого:
            for i in self.graphs:
                if not i.scalable:
                    continue
                i.graph_window.plot_widget.setXRange(self.scale_x_min, self.scale_x_max)
                i.graph_window.plot_widget.setYRange(self.scale_y_min, self.scale_y_max)
                # Установить диапазон для каждого из графиков
                i.scale_x_min = self.scale_x_min
                i.scale_x_max = self.scale_x_max
            # Если есть окно настройки текущего графика:
            if self.current_grapth_index is not None:
                if self.graphs[self.current_grapth_index].scalable:
                    self.graphs[self.current_grapth_index].scale_x_min = self.scale_x_min
                    self.graphs[self.current_grapth_index].scale_x_max = self.scale_x_max
        except ValueError:
            # Обработка случаев, когда поля пусты или содержат некорректные значения
            pass

    def set_the_scale_1_2(self):
        try:
            self.scale_y_min = float(self.y_min_input.text())
            self.scale_y_max = float(self.y_max_input.text())
            # Перерисовать графики исходя из этого:
            for i in self.graphs:
                if not i.scalable:
                    continue
                i.graph_window.plot_widget.setXRange(self.scale_x_min, self.scale_x_max)
                i.graph_window.plot_widget.setYRange(self.scale_y_min, self.scale_y_max)
                # Установить диапазон для каждого из графиков
                i.scale_y_min = self.scale_y_min
                i.scale_y_max = self.scale_y_max
            # Если есть окно настройки текущего графика:
            if self.current_grapth_index is not None:
                if self.graphs[self.current_grapth_index].scalable:
                    self.graphs[self.current_grapth_index].scale_y_min = self.scale_y_min
                    self.graphs[self.current_grapth_index].scale_y_max = self.scale_y_max
        except ValueError:
            # Обработка случаев, когда поля пусты или содержат некорректные значения
            pass

    def set_the_scale_2_1(self):
        try:
            x_min = float(self.x1_min_input.text())
            x_max = float(self.x1_max_input.text())
            self.graphs[self.current_grapth_index].scale_x_min = x_min
            self.graphs[self.current_grapth_index].scale_x_max = x_max
            self.graphs[self.current_grapth_index].graph_window.plot_widget.setXRange(x_min, x_max)
        except ValueError:
            pass

    def set_the_scale_2_2(self):
        try:
            y_min = float(self.y1_min_input.text())
            y_max = float(self.y1_max_input.text())
            self.graphs[self.current_grapth_index].scale_y_min = y_min
            self.graphs[self.current_grapth_index].scale_y_max = y_max
            self.graphs[self.current_grapth_index].graph_window.plot_widget.setYRange(y_min, y_max)
        except ValueError:
            pass

    def set_y_scale(self):
        x_min = self.scale_x_min
        x_max = self.scale_x_max
        for i in self.graphs:
            if not i.scalable:
                continue
            filtered_data = i.data.loc[x_min:x_max]
            y_min = filtered_data.min().min()
            y_max = filtered_data.max().max()
            i.graph_window.plot_widget.setYRange(y_min, y_max)
        self.rewrite_scale()

    def set_y_scale1(self):
        x_min = self.graphs[self.current_grapth_index].scale_x_min
        x_max = self.graphs[self.current_grapth_index].scale_x_max
        filtered_data = self.graphs[self.current_grapth_index].data.loc[x_min:x_max]
        y_min = filtered_data.min().min()
        y_max = filtered_data.max().max()
        self.graphs[self.current_grapth_index].graph_window.plot_widget.setYRange(y_min, y_max)
        # self.rewrite_scale()

    def rewrite_scale(self):
        """Обновление виджетов диапазона X и Y на основе текущих значений масштабов."""
        # Установка значений масштаба оси X
        self.x_min_input.setText(str(self.scale_x_min))
        self.x_max_input.setText(str(self.scale_x_max))

        # Установка значений масштаба оси Y
        self.y_min_input.setText(str(self.scale_y_min))
        self.y_max_input.setText(str(self.scale_y_max))

        # Если есть окно изменений масштаба текущего графика:
        if self.current_grapth_index is not None:
            self.x1_min_input.setText(str(self.scale_x_min))  # Устанавливаем значение минимума оси X
            self.x1_max_input.setText(str(self.scale_x_max))  # Устанавливаем значение максимума оси X
            self.y1_min_input.setText(str(self.scale_y_min))  # Устанавливаем значение минимума оси Y
            self.y1_max_input.setText(str(self.scale_y_max))  # Устанавливаем значение максимума оси Y

        # !!!!!! При удалении графика надо бы изменить масштабы? Или нет?

    def set_common_scale(self):  # Функция-обработчик для кнопки "Применить"
        try:
            self.scale_x_min = float(self.x_min_input.text())
            self.scale_x_max = float(self.x_max_input.text())
            self.scale_y_min = float(self.y_min_input.text())
            self.scale_y_max = float(self.y_max_input.text())
            # Перерисовать графики исходя из этого:
            for i in self.graphs:
                if not i.scalable:
                    continue
                i.graph_window.plot_widget.setXRange(self.scale_x_min, self.scale_x_max)
                i.graph_window.plot_widget.setYRange(self.scale_y_min, self.scale_y_max)
                # Установить диапазон для каждого из графиков
                i.scale_x_min = self.scale_x_min
                i.scale_x_max = self.scale_x_max
                i.scale_y_min = self.scale_y_min
                i.scale_y_max = self.scale_y_max
            # Если есть окно настройки текущего графика:
            if self.current_grapth_index is not None:
                if self.graphs[self.current_grapth_index].scalable:
                    self.graphs[self.current_grapth_index].scale_x_min = self.scale_x_min
                    self.graphs[self.current_grapth_index].scale_x_max = self.scale_x_max
                    self.graphs[self.current_grapth_index].scale_y_min = self.scale_y_min
                    self.graphs[self.current_grapth_index].scale_y_max = self.scale_y_max
        except ValueError:
            # Обработка случаев, когда поля пусты или содержат некорректные значения
            pass

    def set_default_scale(self):  # Функция-обработчик для кнопки "Сбросить"
        if len(self.graphs) == 0:
            return
        x_min = self.graphs[0].data.index.min()
        x_max = self.graphs[0].data.index.max()
        y_min = self.graphs[0].data.min().min()
        y_max = self.graphs[0].data.max().max()
        for i in self.graphs:
            if not i.scalable:
                continue
            i.scale_x_min = i.data.index.min()  # Минимум значений индекса "T"
            i.scale_x_max = i.data.index.max()  # Максимум значений индекса "T"
            i.scale_y_min = i.data.min().min()  # Минимум значений во всех столбцах
            i.scale_y_max = i.data.max().max()  # Максимум значений во всех столбцах
            x_min = min(x_min, i.scale_x_min)
            x_max = max(x_max, i.scale_x_max)
            y_min = min(y_min, i.scale_y_min)
            y_max = max(y_max, i.scale_y_max)
            i.graph_window.plot_widget.setXRange(i.scale_x_min, i.scale_x_max)
            i.graph_window.plot_widget.setYRange(i.scale_y_min, i.scale_y_max)
        # Если есть окно настройки текущего графика:
        if self.current_grapth_index is not None:
            if self.graphs[self.current_grapth_index].scalable:
                self.graphs[self.current_grapth_index].scale_x_min = self.graphs[self.current_grapth_index].data.index.min()
                self.graphs[self.current_grapth_index].scale_x_max = self.graphs[self.current_grapth_index].data.index.max()
                self.graphs[self.current_grapth_index].scale_y_min = self.graphs[self.current_grapth_index].data.iloc[:, self.current_grapth_index].min()
                self.graphs[self.current_grapth_index].scale_y_max = self.graphs[self.current_grapth_index].data.iloc[:, self.current_grapth_index].max()
        # Изменим общий масштаб
        self.scale_x_min = x_min
        self.scale_x_max = x_max
        self.scale_y_min = y_min
        self.scale_y_max = y_max
        self.rewrite_scale()

    def set_the_scale(self):
        """ Установить масштаб выбранного графика """
        try:
            x_min = float(self.x1_min_input.text())
            x_max = float(self.x1_max_input.text())
            y_min = float(self.y1_min_input.text())
            y_max = float(self.y1_max_input.text())
            self.graphs[self.current_grapth_index].scale_x_min = x_min
            self.graphs[self.current_grapth_index].scale_x_max = x_max
            self.graphs[self.current_grapth_index].scale_y_min = y_min
            self.graphs[self.current_grapth_index].scale_y_max = y_max
            self.graphs[self.current_grapth_index].graph_window.plot_widget.setXRange(x_min, x_max)
            self.graphs[self.current_grapth_index].graph_window.plot_widget.setYRange(y_min, y_max)
        except ValueError:
            pass

    def reset_the_scale(self):
        """ Сбросить масштаб выбранного графика """
        if self.current_grapth_index is not None:
            x_min = self.graphs[self.current_grapth_index].data.index.min()
            x_max = self.graphs[self.current_grapth_index].data.index.max()
            y_min = self.graphs[self.current_grapth_index].data.min().min()
            y_max = self.graphs[self.current_grapth_index].data.max().max()
            self.graphs[self.current_grapth_index].scale_x_min = x_min  # Минимум значений индекса "T"
            self.graphs[self.current_grapth_index].scale_x_max = x_max  # Максимум значений индекса "T"
            self.graphs[self.current_grapth_index].scale_y_min = y_min  # Минимум значений во всех столбцах
            self.graphs[self.current_grapth_index].scale_y_max = y_max  # Максимум значений во всех столбцах
            self.graphs[self.current_grapth_index].graph_window.plot_widget.setXRange(x_min, x_max)
            self.graphs[self.current_grapth_index].graph_window.plot_widget.setYRange(y_min, y_max)
            self.x1_min_input.setText(str(x_min))  # Устанавливаем значение минимума оси X
            self.x1_max_input.setText(str(x_max))  # Устанавливаем значение максимума оси X
            self.y1_min_input.setText(str(y_min))  # Устанавливаем значение минимума оси Y
            self.y1_max_input.setText(str(y_max))  # Устанавливаем значение максимума оси Y

    def create_menu(self):
        """Создаем меню"""
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("Файл")
        open_project_action = QAction("Открыть проект", self)
        open_project_action.setShortcut("Ctrl+O")
        open_project_action.triggered.connect(self.open)
        file_menu.addAction(open_project_action)

        save_action = QAction("Сохранить проект", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save)
        file_menu.addAction(save_action)

        save_project_action = QAction("Сохранить проект как", self)
        save_project_action.triggered.connect(self.save_as)
        file_menu.addAction(save_project_action)

        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        graph_menu = menu_bar.addMenu("Графики")
        add_graph_action = QAction("Добавить график", self)
        add_graph_action.triggered.connect(self.add_graph)
        graph_menu.addAction(add_graph_action)
        save_graph_action = QAction("Экспортировать текущий график в png", self)
        save_graph_action.triggered.connect(self.screen_save_img)
        graph_menu.addAction(save_graph_action)

        window_menu = menu_bar.addMenu("Окна")
        new_window_action = QAction("Сделать одного размера", self)
        new_window_action.triggered.connect(self.win_as_one)
        window_menu.addAction(new_window_action)

    def save_as(self):
        global IS_SAVE
        if len(self.graphs) == 0:
            return

        # Открываем диалог для выбора пути и имени файла
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить как",
            "",
            "Graph Files (*.sgr)"  # Фильтр для расширения .sgr
        )

        # Если пользователь отменил выбор, выходим
        if not file_path:
            return

        # Убедимся, что файл имеет расширение .sgr
        if not file_path.endswith(".sgr"):
            file_path += ".sgr"

        # Сохраняем список self.graphs в файл
        try:
            with open(file_path, "wb") as file:
                pickle.dump(self.graphs, file)
            # QMessageBox.information(self, "Успех", f"Файл успешно сохранен: {file_path}")
            self.project_name = file_path
            IS_SAVE = True
        except Exception as e:
            # Попытка удаления файла, если он был создан
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError as remove_error:
                    QMessageBox.warning(
                        self,
                        "Предупреждение",
                        f"Не удалось удалить файл после ошибки: {remove_error}"
                    )
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл: {e}")

    def save(self):
        global IS_SAVE
        if self.project_name is None:
            self.save_as()
            return
        # Создаем временное имя файла
        temp_file_path = self.project_name + ".tmp"
        try:
            # Сохраняем данные во временный файл
            with open(temp_file_path, "wb") as temp_file:
                pickle.dump(self.graphs, temp_file)
            # Заменяем старый файл временным
            os.replace(temp_file_path, self.project_name)
            IS_SAVE = True
            # QMessageBox.information(self, "Успех", f"Файл успешно сохранен: {self.project_name}")
        except Exception as e:
            # Удаляем временный файл, если произошла ошибка
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError as remove_error:
                    QMessageBox.warning(
                        self,
                        "Предупреждение",
                        f"Не удалось удалить временный файл: {remove_error}"
                    )
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл: {e}")

    def open(self):
        """Открыть файл и загрузить список графиков в self.graphs"""
        global IS_SAVE
        # !!! восстановить 2 объекта - таблицы и полотно графиков!
        if len(self.graphs) > 0:
            response = QMessageBox.question(
                self,
                "Подтверждение открытия нового проекта",
                f"При открытии текущий проект будет закрыт. Убедитесь, что сохранили его. Открыть новый проект?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if response == QMessageBox.StandardButton.No:
                return
        # Открываем диалог для выбора файла
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть файл",
            "",
            "Graph Files (*.sgr)"  # Фильтр для расширения .sgr
        )
        # Если пользователь отменил выбор, выходим
        if not file_path:
            return
        try:
            # Открываем файл и загружаем данные
            with open(file_path, "rb") as file:
                loaded_graphs = pickle.load(file)
            # Проверяем, что данные корректны
            if not isinstance(loaded_graphs, list):
                raise ValueError("Некорректный формат данных в файле.")
            # Обновляем список self.graphs
            self.graphs = loaded_graphs
            self.project_name = file_path
            # Выполняем действия для обновления интерфейса
            # self.update_graph_table()  # Пример: метод обновления таблицы графиков
            self.rewrite_table()
            for i in self.graphs:
                if i.show is True:
                    self.show_graph(i)
                else:
                    self.show_graph(i)
                    i.graph_window.hide()
            # Обновление глобальных переменных для общего диапазона масштабирования
            self.scale_x_min = min(obj.scale_x_min for obj in self.graphs)
            self.scale_x_max = max(obj.scale_x_max for obj in self.graphs)
            self.scale_y_min = min(obj.scale_y_min for obj in self.graphs)
            self.scale_y_max = max(obj.scale_y_max for obj in self.graphs)
            self.rewrite_scale()  # Скорректируем отображаемый диапазон масштаба графиков
        except (pickle.UnpicklingError, ValueError) as e:
            QMessageBox.critical(self, "Ошибка", f"Файл поврежден или имеет неверный формат: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл: {e}")
        IS_SAVE = True

    def win_as_one(self):
        """ Делаем все окна размером как выбранное """
        if self.current_grapth_index is None:
            QMessageBox.critical(self, "График не выбран", f"Выберите в таблице справа график, размер окна которого получат остальные окна")
            return
        current_size = self.graphs[self.current_grapth_index].graph_window.plot_widget.size()
        for i in self.graphs:
            i.graph_window.plot_widget.resize(current_size.width(), current_size.height())

    def setup_table(self):
        """Настройка таблицы"""
        self.table.setColumnCount(4)  # Увеличиваем количество столбцов до 4
        self.table.setHorizontalHeaderLabels(
            ["График", "Показать", "Масштаб", "Удалить"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 50)  # Устанавливаем ширину столбца для кнопки
        self.table.verticalHeader().setVisible(False)  # Отключаем нумерацию строк
        # Подключаем сигнал выбора элемента к обработчику
        self.table.itemSelectionChanged.connect(self.on_graph_selected)
        # self.table.selectionModel().selectionChanged.connect(
        #     lambda selected, deselected: self.on_selection_changed_1(selected, deselected, table_widget, graph_data,
        #                                                            plot_widget)
        # )

    def on_graph_selected(self):
        """Обработчик выбора графика"""
        selected_indexes = self.table.selectedIndexes()
        if selected_indexes:
            # Получаем индекс выделенной строки
            row_index = selected_indexes[0].row()
            self.current_grapth_index = row_index
            # print(f"Выбран индекс графика: {row_index}")
            self.container_widget.setVisible(True)  # Показываем форму
            self.current_graph_name_label.setText(self.table.item(row_index, 0).text())  # Установка текста в QLabel
            # Установка значений в QLineEdit
            self.x1_min_input.setText(str(self.graphs[row_index].scale_x_min))  # Устанавливаем значение минимума оси X
            self.x1_max_input.setText(str(self.graphs[row_index].scale_x_max))  # Устанавливаем значение максимума оси X
            self.y1_min_input.setText(str(self.graphs[row_index].scale_y_min))  # Устанавливаем значение минимума оси Y
            self.y1_max_input.setText(str(self.graphs[row_index].scale_y_max))  # Устанавливаем значение максимума оси Y
        else:
            # Если не выбран ни один график
            self.container_widget.setVisible(False)  # Показываем форму
            self.current_grapth_index = None

            # Если вам также нужно название графика
            # graph_name = self.table.item(row_index, 0).text()
            # print(f"Название графика: {graph_name}")

            # Теперь можно выполнить нужные действия с row_index или graph_name

    def add_graph(self):
        """Добавление нового графика"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите CSV файл", "", "CSV Files (*.csv)")
        if not file_path:
            return  # Если файл не выбран, выйти

        # Чтение данных из CSV
        data = pd.read_csv(file_path, index_col=0)
        data = data.fillna(0)  # Меняем НаН на 0

        # Создание структуры данных для графика
        graph_data = GraphData(data, file_path)
        self.graphs.append(graph_data)

        graph_data.graphics_visible = [True] * len(data.columns)

        # Установка значений для scale_x_min и scale_x_max из индекса
        graph_data.scale_x_min = data.index.min()  # Минимум значений индекса "T"
        graph_data.scale_x_max = data.index.max()  # Максимум значений индекса "T"

        # Установка значений для scale_y_min и scale_y_max из всех столбцов
        graph_data.scale_y_min = data.min().min()  # Минимум значений во всех столбцах
        graph_data.scale_y_max = data.max().max()  # Максимум значений во всех столбцах

        # Обновление глобальных переменных для общего диапазона масштабирования
        self.scale_x_min = min(self.scale_x_min, graph_data.scale_x_min)
        self.scale_x_max = max(self.scale_x_max, graph_data.scale_x_max)
        self.scale_y_min = min(self.scale_y_min, graph_data.scale_y_min)
        self.scale_y_max = max(self.scale_y_max, graph_data.scale_y_max)

        self.rewrite_scale()  # Скорректируем отображаемый диапазон масштаба графиков

        # Отображение графика в новом окне
        self.show_graph(graph_data)

        # Добавление строки в таблицу
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        self.table.setItem(row_position, 0, QTableWidgetItem(graph_data.file_name))

        # Создание чекбоксов для отображения и масштабирования
        show_checkbox = QCheckBox()
        show_checkbox.setChecked(True)
        show_checkbox.stateChanged.connect(
            lambda state, g=graph_data, r=row_position: self.toggle_graph_visibility(g, state, r))
        self.table.setCellWidget(row_position, 1, show_checkbox)

        scale_checkbox = QCheckBox()
        scale_checkbox.setChecked(graph_data.scalable)
        scale_checkbox.stateChanged.connect(
            lambda state, g=graph_data, r=row_position: self.toggle_graph_scaleble(g, state, r))
        self.table.setCellWidget(row_position, 2, scale_checkbox)

        # Создаем чекбокс удаления
        delete_checkbox = QCheckBox()
        delete_checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 7px;
                background-color: red;
            }
            QCheckBox::indicator:checked {
                background-color: darkred;
            }
        """)
        # Обработка клика по чекбоксу для удаления графика
        delete_checkbox.stateChanged.connect(lambda state, row=row_position, g=graph_data: self.delete_graph(row, g))
        # Размещаем чекбокс в ячейке таблицы
        self.table.setCellWidget(row_position, 3, delete_checkbox)

    def rewrite_table(self):
        """Пересоздает таблицу self.table на основе данных из self.graphs."""
        # Очищаем таблицу
        self.table.setRowCount(0)

        # Добавляем строки для каждого графика в списке self.graphs
        for row_position, graph_data in enumerate(self.graphs):
            self.table.insertRow(row_position)
            self.table.setItem(row_position, 0, QTableWidgetItem(graph_data.file_name))

            # Создание чекбоксов для отображения и масштабирования с учётом состояния в GraphData
            show_checkbox = QCheckBox()
            show_checkbox.setChecked(graph_data.show)
            show_checkbox.stateChanged.connect(
                lambda state, g=graph_data, r=row_position: self.toggle_graph_visibility(g, state, r))
            self.table.setCellWidget(row_position, 1, show_checkbox)

            scale_checkbox = QCheckBox()
            scale_checkbox.setChecked(graph_data.scalable)
            scale_checkbox.stateChanged.connect(
                lambda state, g=graph_data, r=row_position: self.toggle_graph_scaleble(g, state, r))
            self.table.setCellWidget(row_position, 2, scale_checkbox)

            # Создаем чекбокс удаления
            delete_checkbox = QCheckBox()
            delete_checkbox.setStyleSheet("""
                QCheckBox::indicator {
                    width: 14px;
                    height: 14px;
                    border-radius: 7px;
                    background-color: red;
                }
                QCheckBox::indicator:checked {
                    background-color: darkred;
                }
            """)
            # Обработка клика по чекбоксу для удаления графика
            delete_checkbox.stateChanged.connect(
                lambda state, row=row_position, g=graph_data: self.delete_graph(row, g))
            self.table.setCellWidget(row_position, 3, delete_checkbox)

    def delete_graph(self, row_position, graph_data):
        """Удаление графика"""
        # Закрываем окно графика, если оно открыто
        if graph_data.graph_window:  # and graph_data.graph_window.isVisible()
            graph_data.graph_window.close()

        # Удаляем объект графика из списка
        self.graphs.remove(graph_data)
        self.rewrite_table()

        # Если удаляемый график был выбран текущим
        if row_position == self.current_grapth_index:
            self.container_widget.setVisible(False)  # Показываем форму
            self.current_grapth_index = None

    def toggle_all_graphs_visibility(self, state, graph_data, table_widget):
        """Изменение видимости всех графиков"""
        state = Qt.CheckState(state)
        is_visible = state == Qt.Checked
        for i in range(len(graph_data.graphics_visible)):
            graph_data.graphics_visible[i] = is_visible
            # Обновляем состояние отдельных чекбоксов
            checkbox = table_widget.cellWidget(i + 1, 0)  # Пропускаем первый общий чекбокс
            checkbox.setChecked(is_visible)
        self.rewrite_graph(graph_data)

    def toggle_individual_graph_visibility(self, state, idx, graph_data, plot_widget):
        """Изменение видимости отдельного графика"""
        state = Qt.CheckState(state)
        is_visible = state == Qt.Checked
        graph_data.graphics_visible[idx] = is_visible
        # print('state=', state, 'idx=', idx, 'plot_widget.plotItem.items=', plot_widget.plotItem.items)
        # self.on_selection_changed(0, 0,    )jjj
        # Получаем график для соответствующего соединения и устанавливаем его видимость
        plot = plot_widget.plotItem.items[idx]  # !!!! Здесь ошибка - индекс вне диапазона (0)!!!
        plot.setVisible(is_visible)
        self.rewrite_graph(graph_data)

    def show_graph(self, graph_data):
        """Показать график в новом окне с возможностью выбора отображаемых соединений"""
        graph_data.graph_window = QMainWindow(self)
        graph_data.graph_window.setWindowTitle(graph_data.file_name)
        graph_data.graph_window.setGeometry(100, 100, 800, 400)  # Увеличим ширину окна

        # Создаем главный виджет с разделителем
        splitter = QSplitter()
        graph_data.graph_window.setCentralWidget(splitter)

        # Левый виджет с графиком
        plot_widget = pg.PlotWidget()
        graph_data.graph_field = plot_widget  # Сохраняем поле графика
        plot_widget.setBackground("w")
        plot_widget.setLabel('left', graph_data.units_list[graph_data.unit_final], units='')  # Подпись для оси Y
        plot_widget.setLabel('bottom', 'x', units='')  # Подпись для оси X
        splitter.addWidget(plot_widget)

        graph_data.graph_window.plot_widget = plot_widget  # Сохраняем ссылку в graph_window, чтобы менять масштаб!!!
        # graph_window.plot_widget.setXRange(x_min, x_max) - так менять!
        # graph_window.plot_widget.setYRange(y_min, y_max)

        # Правый виджет с таблицей чекбоксов
        table_widget = QTableWidget()
        graph_data.graph_table = table_widget  # Сохраняем ссылку на таблицу
        table_widget.setColumnCount(2)
        table_widget.setHorizontalHeaderLabels(["", "Соединение"])
        table_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table_widget.verticalHeader().setVisible(False)  # Отключаем нумерацию строк
        splitter.addWidget(table_widget)

        # Инициализация таблицы с чекбоксами
        connections = graph_data.data.columns
        table_widget.setRowCount(len(connections) + 1)  # На одну строку больше для общего чекбокса "Все"

        # Создаем общий чекбокс "Все"
        all_checkbox = QCheckBox()
        all_checkbox.setChecked(all(graph_data.graphics_visible))  # Устанавливаем в зависимости от всех графиков
        all_checkbox.stateChanged.connect(
            lambda state: self.toggle_all_graphs_visibility(state, graph_data, table_widget))
        table_widget.setCellWidget(0, 0, all_checkbox)
        table_widget.setItem(0, 1, QTableWidgetItem("Все"))

        # Создаем чекбоксы для каждого соединения
        for i, col_name in enumerate(connections):
            # Создаем чекбокс и устанавливаем его состояние из graphics_visible
            checkbox = QCheckBox()
            checkbox.setChecked(graph_data.graphics_visible[i])
            checkbox.stateChanged.connect(
                lambda state, idx=i: self.toggle_individual_graph_visibility(state, idx, graph_data, plot_widget))
            table_widget.setCellWidget(i + 1, 0, checkbox)  # Первая строка - общий чекбокс, поэтому i+1
            table_widget.setItem(i + 1, 1, QTableWidgetItem(col_name))

        # Построение графиков для каждой колонки, заменяя NaN на 0
        x_values = graph_data.data.index
        data_filled = graph_data.data.fillna(0)  # Заменяем NaN на 0 для всех колонок

        # Подключаем сигнал `selectionChanged` к обработчику
        table_widget.selectionModel().selectionChanged.connect(
            lambda selected, deselected: self.on_selection_changed(selected, deselected, table_widget, graph_data,
                                                                   plot_widget)
        )

        for i, col in enumerate(data_filled.columns):
            column_data = data_filled[col]
            # Добавляем легенду
            # plot_widget.addLegend()
            plot = plot_widget.plot(
                column_data.index.values,
                column_data.values,
                pen=pg.mkPen(color="gray", width=2),
                name=col
            )
            plot.setVisible(graph_data.graphics_visible[i])  # Устанавливаем видимость из graphics_visible
            graph_data.graphics_visible[i] = True  # Включаем все графики по умолчанию

        # # Установка диапазонов осей X и Y на основе масштабов графика
        # plot_widget.setXRange(self.scale_x_min, self.scale_x_max)
        # plot_widget.setYRange(self.scale_y_min, self.scale_y_max)

        # Устанавливаем событие на закрытие окна
        graph_data.graph_window.closeEvent = lambda event: self.on_graph_window_closed(graph_data)
        graph_data.show = True  # Устанавливаем статус графика как отображаемого
        graph_data.graph_window.show()

    # def rewrite_graph(self, graph_data):
    #     # 1. Очистка виджета графиков перед перерисовкой
    #     graph_data.graph_field.clear()
    #
    #     # 2. Перерисовка графиков с учетом свойства graphics_visible и выделения
    #     for i, col_name in enumerate(graph_data.data.columns):
    #         # Устанавливаем цвет графика:
    #         # - "red", если выделено
    #         # - "gray", если видимо, но не выделено
    #         # - цвет фона "w", если не видимо
    #         if graph_data.graphics_visible[i]:
    #             color = "gray"  # Цвет по умолчанию
    #             z_value = 1  # Верхний слой
    #             if graph_data.graph_table.item(i + 1, 1) in graph_data.graph_table.selectedItems():
    #                 color = "red"  # Если график выбран в таблице, делаем его красным
    #                 z_value = 2  # самый Верхний слой
    #         else:
    #             color = "w"  # Цвет фона для невидимых графиков
    #             z_value = 0  # Нижний слой
    #
    #         # Получаем данные и строим график с выбранным цветом
    #         column_data = graph_data.data[col_name].fillna(0)
    #
    #         # Преобразуем значения по оси Y с использованием функций f1 и f2
    #         transformed_y = graph_data.unit_from[graph_data.unit_initial](
    #             graph_data.unit_to[graph_data.unit_final](column_data.values))
    #
    #         # Строим график с преобразованными данными
    #         plot = graph_data.graph_field.plot(
    #             column_data.index.values,  # Значения по оси X остаются неизменными
    #             transformed_y,  # Преобразованные значения по оси Y
    #             pen=pg.mkPen(color=color, width=2),
    #             name=col_name
    #         )
    #
    #         # plot = graph_data.graph_field.plot(
    #         #     column_data.index.values,
    #         #     column_data.values,
    #         #     pen=pg.mkPen(color=color, width=2),
    #         #     name=col_name
    #         # )
    #
    #         # Устанавливаем Z-value: белые графики будут под остальными
    #         plot.setZValue(z_value)

    def rewrite_graph(self, graph_data):
        # 1. Очистка виджета графиков перед перерисовкой
        graph_data.graph_field.clear()

        # 2. Перерисовка графиков с учетом свойства graphics_visible и выделения
        for i, col_name in enumerate(graph_data.data.columns):
            # Устанавливаем цвет графика:
            # - "red", если выделено
            # - "gray", если видимо, но не выделено
            # - цвет фона "w", если не видимо
            if graph_data.graphics_visible[i]:
                color = "gray"  # Цвет по умолчанию
                z_value = 1  # Верхний слой
                if graph_data.graph_table.item(i + 1, 1) in graph_data.graph_table.selectedItems():
                    color = "red"  # Если график выбран в таблице, делаем его красным
                    z_value = 2  # самый Верхний слой
            else:
                color = "w"  # Цвет фона для невидимых графиков
                z_value = 0  # Нижний слой

            # Получаем данные
            column_data = graph_data.data[col_name]

            # Убираем NaN: сохраняем только индексы, где значения не являются NaN
            # print('column_data=', column_data)
            valid_indices = ~column_data.isna()
            valid_x = column_data.index.values[valid_indices]
            valid_y = column_data.values[valid_indices]

            # Преобразуем значения по оси Y с использованием функций f1 и f2
            transformed_y = graph_data.unit_from[graph_data.unit_initial](
                graph_data.unit_to[graph_data.unit_final](valid_y))

            # Применяем преобразования только к значениям, не равным 0
            # transformed_y = np.where(
            #     valid_y != 0,  # Условие: если значение не равно 0
            #     graph_data.unit_from[graph_data.unit_initial](
            #         graph_data.unit_to[graph_data.unit_final](valid_y)
            #     ),
            #     valid_y  # Если значение равно 0, оставляем его без изменений
            # )

            # Строим график с преобразованными данными
            plot = graph_data.graph_field.plot(
                valid_x,  # Ось X только для валидных данных
                transformed_y,  # Преобразованные значения по оси Y
                pen=pg.mkPen(color=color, width=2),
                name=col_name
            )

            # Устанавливаем Z-value: белые графики будут под остальными
            plot.setZValue(z_value)

    def on_selection_changed(self, selected, deselected, table_widget, graph_data, plot_widget):
        """Обработка изменения выделения строк в таблице выбора графиков"""

        # 1. Очистка виджета графиков перед перерисовкой
        plot_widget.clear()

        # 2. Перерисовка графиков с учетом свойства graphics_visible и выделения
        for i, col_name in enumerate(graph_data.data.columns):
            # Устанавливаем цвет графика:
            # - "red", если выделено
            # - "gray", если видимо, но не выделено
            # - цвет фона "w", если не видимо
            if graph_data.graphics_visible[i]:
                color = "gray"  # Цвет по умолчанию
                z_value = 1  # Верхний слой
                if table_widget.item(i + 1, 1) in table_widget.selectedItems():
                    color = "red"  # Если график выбран в таблице, делаем его красным
                    z_value = 2  # самый Верхний слой
            else:
                color = "w"  # Цвет фона для невидимых графиков
                z_value = 0  # Нижний слой

            # Получаем данные и строим график с выбранным цветом
            column_data = graph_data.data[col_name].fillna(0)
            plot = plot_widget.plot(
                column_data.index.values,
                column_data.values,
                pen=pg.mkPen(color=color, width=2),
                name=col_name
            )

            # Устанавливаем Z-value: белые графики будут под остальными
            plot.setZValue(z_value)

        # 3. Проверка, выбрана ли строка "Все" (первая строка)
        if table_widget.item(0, 1) in table_widget.selectedItems():
            # Если выбрана строка "Все", выделяем все строки в таблице
            table_widget.selectAll()

    def toggle_graph_visibility(self, graph_data, state, row_position):
        """Переключение видимости окна графика и обновление состояния GraphData"""
        state = Qt.CheckState(state)
        if state == Qt.CheckState.Checked:
            if not graph_data.graph_window:
                self.show_graph(graph_data)
            else:
                graph_data.graph_window.show()
            graph_data.show = True  # Обновляем состояние в GraphData
        else:
            if graph_data.graph_window:
                graph_data.graph_window.hide()
            graph_data.show = False  # Обновляем состояние в GraphData

    def toggle_graph_scaleble(self, graph_data, state, row_position):
        state = Qt.CheckState(state)
        if state == Qt.CheckState.Checked:
            graph_data.scalable = True
        else:
            graph_data.scalable = False

    def on_graph_window_closed(self, graph_data):
        """Обработчик закрытия окна графика через системную кнопку"""
        graph_data.show = False  # Обновляем состояние GraphData при закрытии окна
        for row in range(self.table.rowCount()):
            # Находим строку, соответствующую данному графику, и снимаем галочку
            if self.table.item(row, 0).text() == graph_data.file_name:
                checkbox = self.table.cellWidget(row, 1)
                checkbox.setChecked(False)
                break

    def screen_save_img(self):
        """ Сохранение изображения графика """
        active_window = QApplication.activeWindow()
        if not active_window:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Нет активных окон для экспорта"
            )
            return

        for i in self.graphs:
            if active_window.windowTitle() == i.file_name:
                # Открываем диалог для выбора пути и имени файла
                file_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Сохранить как",
                    "",
                    "Image Files (*.png)"  # Фильтр для расширения .sgr
                )
                # Если пользователь отменил выбор, выходим
                if not file_path:
                    return
                # Убедимся, что файл имеет расширение .sgr
                if not file_path.endswith(".png"):
                    file_path += ".png"
                # Создаем ImageExporter
                exporter = ImageExporter(i.graph_field.plotItem)
                # Устанавливаем размер изображения (опционально)
                # exporter.parameters()['width'] = 1024  # Установите нужную ширину
                try:
                    # Сохраняем изображение
                    exporter.export(file_path)
                    return
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "Ошибка",
                        "Изображение не сохранено"
                    )

# Запуск приложения
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())