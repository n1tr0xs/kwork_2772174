import os
import sys
import csv
import configparser
from datetime import datetime
from PySide6.QtWidgets import QApplication, QMainWindow, QTableView, QVBoxLayout, QWidget, QPushButton, QLineEdit, QMessageBox, QDialog, QComboBox, QGridLayout, QLabel
from PySide6.QtCore import Qt, QAbstractTableModel, QSettings, QByteArray, QTranslator, QLibraryInfo, QLocale, QRect
from PySide6.QtGui import QCloseEvent, QPixmap

import DB

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
    margin: 0;
    padding: 0;
}

QDialog {
    background: #000000;
}

QPushButton {
    border-radius: 10px;
}

QPushButton,
QComboBox,
QComboBox{
    background: #5a9bd5;
    color: #ffffff;
}
"""

    def __init__(self, title='Выбор', options=None):
        super().__init__()
        options = options or []
        self.setWindowTitle(title)
        self.setStyleSheet(self.CSS)

        layout = QVBoxLayout()

        # Widgets
        self.combo_box = QComboBox()
        for option in options:
            self.combo_box.addItem(option, option)
        layout.addWidget(self.combo_box)

        self.button_OK = QPushButton("OK")
        self.button_OK.clicked.connect(self.accept)
        layout.addWidget(self.button_OK)

        # Window resize
        self.setLayout(layout)
        self.resize(self.sizeHint())

    def get_selected(self):
        return self.combo_box.currentData()


class ConfirmDialog(QMessageBox):
    CSS = """
* {
    color: #ffffff;
    border-radius: 10px;
    font-family: Arial;
    font-size: 20px;
    font-weight: bold;
    margin: 0;
    padding: 0;
}

QMessageBox {
    background: #000000;
}

QPushButton[text="&Yes"] {
    background: green;
}

QPushButton[text="&No"] {
    background: red;
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
        self.setDefaultButton(QMessageBox.No)
        self.setStyleSheet(self.CSS)


class MainWindow(QMainWindow):
    CSS = """
* {
    color: #ffffff;
    border-radius: 10px;
    font-family: Arial;
    font-size: 20px;
    font-weight: bold;
    margin: 0;
    padding: 0;
}

MainWindow {
    background: #000000;
}

#edit_prompt {
    padding: 5px;
}

#edit_prompt,
#button_export,
#button_update_db,
#label_result {
    background: #5a9bd5;
}

#button_export:hover,
#button_update_db:hover {
    background: #8CB9E1;
}

#button_search {
    background: #70ad46;
}

#button_search:hover {
    background: #96C87D;
}

QHeaderView::section {
    color: #000000;
    text-align: center;
    padding: 0;
}

#label_result {
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
}

#table_result {
    border-top-left-radius: 0;
    border-top-right-radius: 0;
    border: 5px solid #5a9bd5;
    color: #000000;
    text-align: left;
}
"""

    def __init__(self):
        super().__init__()
        self.model = TableModel()
        self.init_ui()

    def init_ui(self):
        self.settings = QSettings('n1tr0xs', WINDOW_TITLE)
        self.setWindowTitle(WINDOW_TITLE)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.setStyleSheet(self.CSS)

        # Label for App name
        self.label_name = QLabel(self.central_widget)
        self.label_name.setObjectName('label_name')
        self.label_name.setText("ЭЛЕКТРОННАЯ БИБЛИОТЕКА ГОРЬКИХ ВЕЩЕСТВ \nИ РЕЦЕПТОРОВ hTAS2R")
        self.label_name.setAlignment(Qt.AlignCenter)

        # Edit for user input
        self.edit_prompt = QLineEdit(self.central_widget)
        # Quinine
        # hTas2r2
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
        self.label_logo.setGeometry(0, 0, 280, 300)
        self.label_logo.setObjectName('label_logo')
        self.label_name.setGeometry(365, 110, 575, 75)

        self.edit_prompt.setGeometry(300, 330, 650, 70)
        self.button_search.setGeometry(300 + 650 - 125, 330 + (70 - 60) // 2, 120, 60)

        self.button_export.setGeometry(515, 410, 230, 60)
        self.button_update_db.setGeometry(50, 650, 265, 35)
        self.label_result.setGeometry(1000, 10, 355, 60)
        self.table_result.setGeometry(1000, 65, 355, 625)

        # Restoring window settings
        self.setFixedSize(1400, 735)
        self.restore_settings()
        self.show()

    def search(self):
        db = DB.SQLite3DB(DB_FILE_PATH)

        name = self.edit_prompt.text()

        # Get compounds with same name, but distinct id
        compounds = db.get_compounds_by_name(name)
        if compounds:
            # Select one of the compunds
            dialog = SelectDialog(title=name, options=(c[0] for c in compounds))
            if dialog.exec() == QDialog.Accepted:
                bitter_id = dialog.get_selected()
                # Get receptors that sensed selected compound
                data = db.get_receptors_by_compound(name, bitter_id)
                self.model = ReceptorModel(data, metadata={'Bitter ID': bitter_id})
        else:
            # Get compounds sensed by receptor
            data = db.get_compounds_by_receptor(name)
            self.model = CompoundModel(data, metadata={'Receptor': name})

        self.table_result.setModel(self.model)
        self.table_result.resizeColumnsToContents()
        self.table_result.resizeRowsToContents()

    def update_db(self):
        dialog = ConfirmDialog(
            'Подтверждение',
            "Обновление базы данных полностью пересоздаст её из csv файлов, указанных в файле settings.ini."
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
    # qt_translator = QTranslator()
    # qt_translation_path = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
    # if qt_translator.load(f"qtbase_{system_locale}", qt_translation_path):
    #     app.installTranslator(qt_translator)

    MainWindow()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
