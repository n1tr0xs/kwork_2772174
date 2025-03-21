import os
import sys
import csv
import configparser
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QDialog, QWidget,
    QVBoxLayout,
    QTableView, QPushButton, QLineEdit, QComboBox, QLabel
)
from PySide6.QtCore import (
    Qt, QSettings, QByteArray, QTranslator, QLibraryInfo, QLocale,
    QAbstractTableModel,
)
from PySide6.QtGui import QCloseEvent, QPixmap, QIcon

import DB

"""
CSS COLORS

blue:
#5a9bd5
#8CB9E1
#4B91CD

green:
#70ad46
#96C87D
#64A045

red:
#ff0000
#e74c3c
#a93226
"""


def load_stylesheet(file_path: str):
    """Load the QSS stylesheet from file."""
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


WINDOW_TITLE = 'DNCBI.BITTER.LIB'

config = configparser.ConfigParser()
config.read('settings.ini', encoding='UTF-8')
EXPORT_FOLDER = config['настройки']['EXPORT_FOLDER']
DB_FILE_PATH = config['настройки']['DB_FILE_PATH']


def create_folder(path: str):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        print(f'Error: {e}')


class WarningBox(QMessageBox):
    def __init__(self, title, text, parent=None):
        super().__init__(parent=parent)
        self.setIcon(QMessageBox.Warning)
        self.setWindowTitle(title)
        self.setText(text)
        self.setStandardButtons(QMessageBox.Ok)
        self.setStyleSheet(load_stylesheet(r'qss\warning_dialog.qss'))


class TableModel(QAbstractTableModel):
    def __init__(self, data=None, headers=None, metadata=None):
        super().__init__()
        self.data_list = data or []
        self.headers = [] or headers
        self.metadata = {
            'Время и дата запроса': datetime.strftime(datetime.now(), "%d.%m.%y %H:%M:%S"),
        }
        if metadata:
            self.metadata.update(metadata)

    def rowCount(self, parent=None):
        return len(self.data_list)

    def columnCount(self, parent=None):
        return len(self.data_list[0]) if self.data_list else 0

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            return self.data_list[index.row()][index.column()]
        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                headers = self.headers
                return headers[section] if section < len(headers) else None
        return None

    def add_data(self, new_data):
        self.beginInsertRows(self.index(self.rowCount(), 0), self.rowCount(), self.rowCount())
        self.data_list.append(new_data)
        self.endInsertRows()

    def get_file_name(self):
        return datetime.strftime(datetime.now(), "%d.%m.%y %H %M %S")

    def to_csv(self):
        create_folder(EXPORT_FOLDER)
        file_name = self.get_file_name() + '.csv'
        file_path = os.path.join(EXPORT_FOLDER, file_name)

        with open(file_path, 'w', encoding='utf-8', newline='') as fout:
            writer = csv.writer(fout)

            for key, value in self.metadata.items():
                writer.writerow([f'# {key}: {value}'])

            writer.writerow(self.headers)
            for row in self.data_list:
                writer.writerow(row)


class SelectDialog(QDialog):
    def __init__(self, title='Выбор', text='', options=None, parent=None):
        super().__init__(parent=parent)
        options = options or []
        self.setWindowTitle(title)
        self.setStyleSheet(load_stylesheet(r'qss\select_dialog.qss'))

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Widgets
        self.label = QLabel(text)
        layout.addWidget(self.label)

        self.combo_box = QComboBox()
        for option in options:
            self.combo_box.addItem(option, option)
        layout.addWidget(self.combo_box)

        self.button_OK = QPushButton("OK")
        self.button_OK.clicked.connect(self.accept)
        layout.addWidget(self.button_OK)

        # Window resize
        self.resize(self.sizeHint())

    def get_selected(self):
        return self.combo_box.currentData()


class ConfirmDialog(QMessageBox):
    def __init__(self, title, text, parent=None):
        super().__init__(
            QMessageBox.Question,
            title,
            text,
            buttons=QMessageBox.Yes | QMessageBox.No,
            parent=parent
        )
        yes_button = self.button(QMessageBox.Yes)
        no_button = self.button(QMessageBox.No)

        self.setStyleSheet(load_stylesheet(r'qss\confirm_dialog.qss'))
        yes_button.setStyleSheet(load_stylesheet(r'qss\button_yes.qss'))
        no_button.setStyleSheet(load_stylesheet(r'qss\button_no.qss'))

        self.setDefaultButton(no_button)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings('n1tr0xs', WINDOW_TITLE)
        self.db = DB.SQLite3DB(DB_FILE_PATH)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(QIcon("icon.ico"))
        self.setStyleSheet(load_stylesheet(r'qss\main_window.qss'))

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        # Label for App name
        self.label_name = QLabel(self.central_widget)
        self.label_name.setObjectName('label_name')
        self.label_name.setText("ЭЛЕКТРОННАЯ БИБЛИОТЕКА ГОРЬКИХ ВЕЩЕСТВ \nИ РЕЦЕПТОРОВ hTAS2R")
        self.label_name.setAlignment(Qt.AlignCenter)

        # Edit for user input
        self.edit_prompt = QLineEdit(self.central_widget)
        self.edit_prompt.setObjectName('edit_prompt')

        # Button to search
        self.button_search = QPushButton(self.central_widget)
        self.button_search.setObjectName('button_search')
        self.button_search.setText("Найти")
        self.button_search.clicked.connect(self.search)

        # Table for output
        self.label_result = QLabel(self.central_widget)
        self.label_result.setObjectName('label_result')
        self.label_result.setText("Результат")
        self.label_result.setAlignment(Qt.AlignCenter)

        self.table_result = QTableView(self.central_widget)
        self.table_result.setObjectName('table_result')
        self.table_result.setModel(TableModel())

        # Button to export found data
        self.button_export = QPushButton(self.central_widget)
        self.button_export.setObjectName('button_export')
        self.button_export.setText("Экспорт в csv")
        self.button_export.clicked.connect(lambda x: self.table_result.model().to_csv())

        # Button to update database
        self.button_update_db = QPushButton(self.central_widget)
        self.button_update_db.setObjectName('button_update_db')
        self.button_update_db.setText("Обновить базу данных")
        self.button_update_db.clicked.connect(self.update_db)

        # Image label
        self.label_logo = QLabel(self.central_widget)
        self.label_logo.setObjectName('label_logo')
        self.label_logo.setPixmap(QPixmap("background.png"))
        self.label_logo.setScaledContents(True)

        # Layout
        self.setFixedSize(1400, 735)
        self.label_logo.setGeometry(0, 0, 280, 300)
        self.label_name.setGeometry(365, 110, 575, 75)
        self.edit_prompt.setGeometry(300, 330, 650, 70)
        self.button_search.setGeometry(825, 335, 120, 60)
        self.button_export.setGeometry(515, 410, 230, 60)
        self.button_update_db.setGeometry(50, 650, 265, 35)
        self.label_result.setGeometry(1000, 10, 355, 60)
        self.table_result.setGeometry(1000, 65, 355, 625)

        # Restoring window settings
        self.restore_settings()
        self.show()

    def search(self):
        '''
        Handles search and "Not found" dialog.
        '''
        prompt = self.edit_prompt.text()
        if not prompt:
            return

        self.update_table()

        if (model := self.search_database(prompt)):
            self.update_table(model)
        else:
            WarningBox(
                'Ошибка',
                'В базе данных не обнаружено',
                parent=self
            ).exec()

    def search_database(self, prompt):
        '''
        Searches prompt in DB.
        '''
        if (receptors := self.search_receptors(prompt)):
            return receptors
        elif (compounds := self.search_compounds(prompt)):
            return compounds

    def update_table(self, model=TableModel()):
        self.table_result.setModel(model)
        self.table_result.resizeColumnsToContents()
        self.table_result.resizeRowsToContents()

    def search_receptors(self, compound_name):
        '''
        Searches receptors that can sense `compound_name`.
        '''
        # Get compounds with same name, but distinct id
        compounds = self.db.get_compounds_by_name(compound_name)
        if not compounds:
            return None

        # Select one of the compunds
        dialog = SelectDialog(
            title=compound_name,
            text='Выберите Bitter ID',
            options=(c[0] for c in compounds),
            parent=self,
        )
        if dialog.exec() == QDialog.Rejected:
            return TableModel()

        bitter_id = dialog.get_selected()
        data = self.db.get_receptors_by_compound(compound_name, bitter_id)
        if not data:
            return None

        return TableModel(
            data,
            headers=['Название рецептора'],
            metadata={'Bitter ID': bitter_id, 'Название вещества': compound_name},
        )

    def search_compounds(self, receptor_name):
        '''
        Gets compounds that can be sensed by receptor.
        '''
        data = self.db.get_compounds_by_receptor(receptor_name)
        if not data:
            return None

        return TableModel(
            data,
            headers=['Bitter ID', "Название вещества"],
            metadata={'Receptor': receptor_name},
        )

    def update_db(self):
        '''
        Updates database.
        '''
        dialog = ConfirmDialog(
            'Подтверждение',
            "Обновление базы данных полностью пересоздаст её из csv файлов, указанных в файле settings.ini.",
            parent=self,
        )

        if dialog.exec() == QMessageBox.Yes:
            DB.make_tables(DB_FILE_PATH)

    def closeEvent(self, event: QCloseEvent):
        self.save_settings()
        super().closeEvent(event)

    def save_settings(self):
        '''
        Saves current window geometry.
        '''
        self.settings.setValue("geometry", self.saveGeometry())

    def restore_settings(self):
        '''
        Restores last window geometry.
        '''
        self.restoreGeometry(self.settings.value("geometry", type=QByteArray))


def main():
    app = QApplication([])

    # Translations
    system_locale = QLocale.system().name()
    QLocale.setDefault(QLocale(system_locale))
    qt_translator = QTranslator()
    qt_translation_path = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
    if qt_translator.load(f"qtbase_{system_locale}", qt_translation_path):
        app.installTranslator(qt_translator)

    MainWindow()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
