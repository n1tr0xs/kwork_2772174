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
        self.database = database

    def _execute_query(self, query: str, params: tuple = ()):
        """Executes a query and returns the result."""
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def csv_to_table(self, csv_path: str, csv_columns: list, table_name: str, sql_columns: list, drop: bool = True):
        """Converts a CSV file into an SQLite table."""
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            if drop:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            fields = ','.join(f"'{col}'" for col in sql_columns)
            cursor.execute(f"CREATE TABLE IF NOT EXISTS '{table_name}'({fields})")

            with open(csv_path, 'r', encoding='utf-8') as fin:
                reader = csv.DictReader(fin)
                to_db = [[row[col] for col in csv_columns] for row in reader]

            values = ', '.join('?' * len(sql_columns))
            cursor.executemany(f"INSERT INTO '{table_name}' VALUES ({values});", to_db)

            # Clean non-human receptors
            cursor.execute("""
                DELETE FROM receptors WHERE
                (name NOT LIKE 'h%') AND (display_name NOT LIKE 'h%')
            """)

            conn.commit()

    def get_compounds_by_receptor(self, receptor: str):
        """Returns compounds associated with a given receptor."""
        query = """
            SELECT DISTINCT c.id, c.name
            FROM receptors r
            JOIN ligands l ON (r.id = l.receptor_id)
            JOIN compounds c ON (l.compound_id = c.id)
            WHERE LOWER(r.name) = ? OR LOWER(r.display_name) = ?
            ORDER BY c.id ASC, c.name ASC
        """
        return self._execute_query(query, (receptor.lower(), receptor.lower()))

    def get_compounds_by_name(self, compound: str):
        """Returns a list of compounds matching the given name."""
        query = """
            SELECT DISTINCT id, name FROM compounds
            WHERE LOWER(name) = ?
            ORDER BY id ASC, name ASC
        """
        return self._execute_query(query, (compound.lower(),))

    def get_receptors_by_compound(self, compound: str, compound_id: int):
        """Returns a list of receptors that interact with a given compound."""
        query = """
            SELECT DISTINCT r.name
            FROM compounds c
            JOIN ligands l ON (c.id = l.compound_id)
            JOIN receptors r ON (l.receptor_id = r.id)
            WHERE LOWER(c.name) = ? AND c.id = ?
            ORDER BY r.name ASC
        """
        return self._execute_query(query, (compound.lower(), compound_id))


def make_tables(database: str):
    """Creates the necessary tables in the database."""
    db = SQLite3DB(database)
    db.csv_to_table(RECEPTOR_FILE_PATH, ['rID', 'rName', 'DisplayName'], 'receptors', ['id', 'name', 'display_name'])
    db.csv_to_table(COMPOUND_FILE_PATH, ['cID', 'cName', 'order'], 'compounds', ['id', 'name', 'ord'])
    db.csv_to_table(LIGAND_FILE_PATH, ['cID', 'rID'], 'ligands', ['compound_id', 'receptor_id'])
