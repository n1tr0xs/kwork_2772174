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


class TableModel(QAbstractTableModel):
    model_name = None
    headers = []

    def __init__(self, data=None, metadata=None):
        super().__init__()
        self.data_list = data or []
        self.metadata = {
            'Время и дата запроса': datetime.strftime(datetime.now(), "%d %m %y %H %M %S"),
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
        return datetime.strftime(datetime.now(), "%d %m %y %H %M %S")

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


class CompoundModel(TableModel):
    model_name = 'compound'
    headers = ['Bitter ID', "Название вещества"]

    def __init__(self, data=None, metadata=None):
        super().__init__(data=data, metadata=metadata)


class ReceptorModel(TableModel):
    model_name = 'receptor'
    headers = ['Название рецептора']

    def __init__(self, data=None, metadata=None):
        super().__init__(data=data, metadata=metadata)


class SelectDialog(QDialog):
    CSS = """
* {
    color: #ffffff;
    font-family: Arial;
    font-size: 16px;
}

QDialog {
    background: #000000;
}

QPushButton,
QComboBox,
QComboBox QAbstractItemView {
    font-size: 14px;
    border-radius: 5px;
    background: #69B0E4;
    padding: 5px;
}

QAbstractItemView::item:hover {
    background-color: #4B91CD;
    border: 0;
}

QPushButton:hover {
    background: #8CB9E1;
}
QPushButton:pressed {
    background: #4B91CD;
}
"""

    def __init__(self, title='Выбор', text='', options=None, parent=None):
        super().__init__(parent=parent)
        options = options or []
        self.setWindowTitle(title)
        self.setStyleSheet(self.CSS)

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
    CSS = """
* {
    color: #ffffff;
    border-radius: 10px;
    font-family: Arial;
    font-size: 16px;
}

QMessageBox {
    background: #000000;
}

QPushButton {
    width: 45px;
    height: 32px;
}
"""
    BUTTON_YES_CSS = """
QPushButton {
    background: #70ad46;
}

QPushButton:hover {
    background-color: #96C87D;
}

QPushButton:pressed {
    background-color: #64A045;
}
"""
    BUTTON_NO_CSS = """
QPushButton {
    background: #ff0000;
}

QPushButton:hover {
    background-color: #e74c3c;
}
QPushButton:pressed {
    background-color: #a93226;
}
"""

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

        self.setStyleSheet(self.CSS)
        yes_button.setStyleSheet(self.BUTTON_YES_CSS)
        no_button.setStyleSheet(self.BUTTON_NO_CSS)

        self.setDefaultButton(no_button)


class MainWindow(QMainWindow):
    CSS = """
* {
    color: #ffffff;
    border-radius: 10px;
    font-family: Arial;
    font-size: 20px;
}

QMenu {
    background-color: #000000;
}

QMenu:item:selected {
    background-color: #8CB9E1;
}

MainWindow {
    background: #000000;
}

#edit_prompt {
    padding: 5px;
}

#edit_prompt,
QPushButton#button_export,
QPushButton#button_update_db,
#label_result {
    background: #5a9bd5;
}

QPushButton#button_export:hover,
QPushButton#button_update_db:hover {
    background: #8CB9E1;
}

QPushButton#button_export:pressed,
QPushButton#button_update_db:pressed {
    background: #4B91CD;
}

QPushButton#button_search {
    background: #70ad46;
}

QPushButton#button_search:hover {
    background: #96C87D;
}

QPushButton#button_search:pressed {
    background: #64A045;
}

#label_result {
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
}

#table_result {
    background: #ffffff;
    color: #000000;
    border-top-left-radius: 0;
    border-top-right-radius: 0;
    border: 5px solid #5a9bd5;
    text-align: left;
    gridline-color: black;
}

QHeaderView::section {
    background: #ffffff;
    color: #000000;
}
"""

    def __init__(self):
        super().__init__()
        self.model = TableModel()
        self.init_ui()

    def init_ui(self):
        self.settings = QSettings('n1tr0xs', WINDOW_TITLE)
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(QIcon("icon.ico"))
        self.setStyleSheet(self.CSS)

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

        # Button to export found data
        self.button_export = QPushButton(self.central_widget)
        self.button_export.setObjectName('button_export')
        self.button_export.setText("Экспорт в csv")
        self.button_export.clicked.connect(lambda x: self.model.to_csv())

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
        db = DB.SQLite3DB(DB_FILE_PATH)

        name = self.edit_prompt.text()

        # Get compounds with same name, but distinct id
        compounds = db.get_compounds_by_name(name)
        if compounds:
            # Select one of the compunds
            dialog = SelectDialog(
                title=name,
                text='Выберите Bitter ID',
                options=(c[0] for c in compounds),
                parent=self,
            )
            if dialog.exec() == QDialog.Accepted:
                bitter_id = dialog.get_selected()
                # Get receptors that sensed selected compound
                data = db.get_receptors_by_compound(name, bitter_id)
                self.model = ReceptorModel(data, metadata={'Bitter ID': bitter_id})
        # Get compounds sensed by receptor
        elif (data := db.get_compounds_by_receptor(name)):
            self.model = CompoundModel(data, metadata={'Receptor': name})
        else:
            self.show_not_found()

        self.table_result.setModel(self.model)
        self.table_result.resizeColumnsToContents()
        self.table_result.resizeRowsToContents()

    def show_not_found(self):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Ошибка")
        msg.setText("В базе данных не обнаружено")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setStyleSheet("""
* {
    color: #ffffff;
    border-radius: 10px;
    font-family: Arial;
    font-size: 16px;
}

QMessageBox {
    background: #000000;
}

QPushButton {
    background: #5a9bd5;
    width: 45px;
    height: 32px;
}
QPushButton:hover {
    background: #8CB9E1;
}
QPushButton:pressed {
    background: #4B91CD;
}
""")
        msg.exec()

    def update_db(self):
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
