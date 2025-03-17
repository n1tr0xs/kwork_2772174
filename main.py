import sys
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtWidgets import QApplication, QMainWindow, QTableView, QVBoxLayout, QWidget, QPushButton
from PySide6.QtCore import Qt, QAbstractTableModel

import DB
from constants import *

class TableModel(QAbstractTableModel):
    def __init__(self, data=None, headers=None):
        super().__init__()
        self.data_list = data or []
        self.headers = headers or []

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

class CompoundModel(TableModel):
    def __init__(self, data=None):
        super().__init__(data=data, headers=['Bitter ID', 'Название'])

class ReceptorModel(TableModel):
    def __init__(self, data=None):
        super().__init__(data=data, headers=['Название'])

class Window(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(100, 100, 600, 400)

        # Widgets
        self.edit = QtWidgets.QLineEdit('hTAS2R2')
        self.search_btn = QtWidgets.QPushButton("Поиск")
        self.table = QTableView()
        self.export_btn = QtWidgets.QPushButton("Экспорт в csv")
        
        # Signals
        self.search_btn.clicked.connect(self.search)
        self.export_btn.clicked.connect(self.export)

        # Layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.edit)
        layout.addWidget(self.search_btn)
        layout.addWidget(self.table)
        layout.addWidget(self.export_btn)

        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def search(self):
        db = DB.SQLite3DB(DB_FILE_PATH)
        prompt = self.edit.text()
        model_func = (
            (CompoundModel, db.get_compounds),
            (ReceptorModel, db.get_receptors),
        )
        
        for (model, func) in model_func:
            self.data = func(prompt)
            if self.data:
                self.table.setModel(model(self.data))

    def export(self):
        pass

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = Window()
    window.show()
    sys.exit(app.exec())
