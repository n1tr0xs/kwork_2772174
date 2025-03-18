import sys
import csv
import configparser
from PySide6.QtWidgets import QApplication, QMainWindow, QTableView, QVBoxLayout, QWidget, QPushButton, QLineEdit, QMessageBox, QDialog, QRadioButton, QLabel, QComboBox
from PySide6.QtCore import Qt, QAbstractTableModel, QSettings, QByteArray, QTranslator, QLibraryInfo, QLocale
from PySide6.QtGui import QCloseEvent
from datetime import datetime

import DB

WINDOW_TITLE = 'Bitter DB'

config = configparser.ConfigParser()
config.read('settings.ini', encoding='UTF-8')
DB_FILE_PATH = config['настройки']['DB_FILE_PATH']


class TableModel(QAbstractTableModel):
    model_name = None
    headers = []

    def __init__(self, data=None):
        super().__init__()
        self.data_list = data or []

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

    def to_csv(self):
        now = datetime.strftime(datetime.now(), "%d %m %y %H %M %S")
        file_name = f'{self.model_name} {now}.csv'

        with open(file_name, 'w', encoding='utf-8', newline='') as fout:
            writer = csv.writer(fout)
            writer.writerow(self.headers)
            for row in self.data_list:
                writer.writerow(row)


class CompoundModel(TableModel):
    model_name = 'compound'
    headers = ['Bitter ID', 'Название вещества']

    def __init__(self, data=None):
        super().__init__(data=data)


class ReceptorModel(TableModel):
    model_name = 'receptor'
    headers = ['Название рецептора', 'Bitter ID']

    def __init__(self, data=None):
        super().__init__(data=data)


class SelectUserDialog(QDialog):
    def __init__(self, title='Выбор', options=None):
        super().__init__()
        options = options or []
        self.setWindowTitle(title)

        # Layout for dialog
        layout = QVBoxLayout()

        # Combo box to display the list of users
        self.combo_box = QComboBox()
        for i, option in enumerate(options):
            self.combo_box.addItem(option, option)

        layout.addWidget(self.combo_box)

        # OK button to confirm selection
        self.button_OK = QPushButton("OK")
        self.button_OK.clicked.connect(self.accept)
        layout.addWidget(self.button_OK)

        self.setLayout(layout)
        self.resize(self.sizeHint())

    def get_selected(self):
        return self.combo_box.currentData()


class Window(QMainWindow):
    def __init__(self):
        super().__init__()

        self.settings = QSettings('n1tr0xs', WINDOW_TITLE)
        self.setWindowTitle(WINDOW_TITLE)

        # Layout
        layout = QVBoxLayout()

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Data
        self.model = TableModel()

        # Widgets
        self.edit = QLineEdit('Quinine')
        layout.addWidget(self.edit)

        self.button_search = QPushButton("Поиск")
        self.button_search.clicked.connect(self.search)
        layout.addWidget(self.button_search)

        self.table = QTableView()
        layout.addWidget(self.table)

        self.button_export = QPushButton("Экспорт в csv")
        self.button_export.clicked.connect(lambda x: self.model.to_csv())
        layout.addWidget(self.button_export)

        self.button_update_db = QPushButton("Обновить базу данных")
        self.button_update_db.clicked.connect(self.update_db)
        layout.addWidget(self.button_update_db)

        # Restoring window settings
        self.resize(self.sizeHint())
        self.restore_settings()
        self.show()

    def search(self):
        self.db = DB.SQLite3DB(DB_FILE_PATH)

        self.get_compounds()

        del self.db
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

    def get_compounds(self):
        name = self.edit.text()

        # Get compounds with same name, but distinct id
        compounds = self.db.get_compounds_by_name(name)
        if compounds:
            # Select one of the compunds
            dialog = SelectUserDialog(title=name, options=(c[0] for c in compounds))
            if dialog.exec() == QDialog.Accepted:
                id_ = dialog.get_selected()
                # Get receptors that sensed selected compound
                data = self.db.get_receptors_by_compound(name, id_)
                self.model = ReceptorModel(data)
        else:
            # Get compounds sensed by receptor
            data = self.db.get_compounds_by_receptor(name)
            self.model = CompoundModel(data)

        self.table.setModel(self.model)

    def update_db(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Подтверждение")
        msg_box.setText("Обновление базы данных полностью пересоздаст её из csv файлов.")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)

        # Execute the message box and check user response
        response = msg_box.exec()

        if response == QMessageBox.Yes:
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

    Window()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
