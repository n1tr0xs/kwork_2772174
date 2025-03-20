import csv
import sqlite3
import configparser


config = configparser.ConfigParser()
config.read('settings.ini', encoding='UTF-8')

RECEPTOR_FILE_PATH = config['настройки']['RECEPTOR_FILE_PATH']
COMPOUND_FILE_PATH = config['настройки']['COMPOUND_FILE_PATH']
LIGAND_FILE_PATH = config['настройки']['LIGAND_FILE_PATH']
DB_FILE_PATH = config['настройки']['DB_FILE_PATH']


class SQLite3DB:
    def __init__(self, database: str):
        self.connection = sqlite3.connect(database)
        self.cursor = self.connection.cursor()

    def csv_to_table(self, csv_path: str, csv_columns: list[str], table_name: str, sql_columns: list[str], drop: bool = True):
        if drop:
            self.cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        fields = ','.join(f"'{col}'" for col in sql_columns)
        self.cursor.execute(f"CREATE TABLE '{table_name}'({fields})")

        with open(csv_path, 'r', encoding='utf-8') as fin:
            reader = csv.DictReader(fin)
            to_db = [[row[col] for col in csv_columns] for row in reader]
        values = ', '.join('?' * len(sql_columns))
        self.cursor.executemany(f"INSERT INTO '{table_name}' VALUES ({values});", to_db)

        # Clean not h%
        self.cursor.execute(f"""
            DELETE FROM receptors
            WHERE (name NOT LIKE 'h%') AND (display_name NOT LIKE 'h%')
        """)

        self.connection.commit()

    def get_compounds_by_receptor(self, receptor: str):
        self.cursor.execute(f"""
            SELECT DISTINCT c.id, c.name
            FROM receptors r
                join ligands l on (r.id=receptor_id)
                join compounds c on (l.compound_id=c.id)
            WHERE LOWER(r.name)='{receptor.lower()}' OR LOWER(r.display_name)='{receptor.lower()}'
            ORDER BY c.id ASC, c.name ASC
        """)
        return self.cursor.fetchall()

    def get_compounds_by_name(self, compound: str):
        self.cursor.execute(f"""
            SELECT DISTINCT c.id, c.name
            FROM compounds c
            WHERE c.name='{compound}'
            ORDER BY c.id ASC, c.name ASC
        """)
        return self.cursor.fetchall()

    def get_receptors_by_compound(self, compound: str, compound_id: int | str):
        self.cursor.execute(f"""
            SELECT DISTINCT r.name
            FROM compounds c
                join ligands l on (c.id=l.compound_id)
                join receptors r on (l.receptor_id=r.id)
            WHERE LOWER(c.name)='{compound.lower()}' AND c.id='{compound_id}'
            ORDER BY r.name ASC
        """)
        return self.cursor.fetchall()

    def close_connection(self):
        self.connection.close()


def make_tables(database: str):
    db = SQLite3DB(database)
    db.csv_to_table(RECEPTOR_FILE_PATH, ('rID', 'rName', 'DisplayName'), 'receptors', ('id', 'name', 'display_name'))
    db.csv_to_table(COMPOUND_FILE_PATH, ('cID', 'cName', 'order'), 'compounds', ('id', 'name', 'ord'))
    db.csv_to_table(LIGAND_FILE_PATH, ('cID', 'rID'), 'ligands', ('compound_id', 'receptor_id'))
    db.close_connection()
