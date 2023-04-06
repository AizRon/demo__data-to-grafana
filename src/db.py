import sqlite3
from dataclasses import dataclass
import logging
from datetime import datetime


logger = logging.getLogger(' db ')


def inj_value(val: str):
    """ For injection STRING (word) to database query """
    return val.split(' ')[0].strip()


@dataclass(slots=True, frozen=True)
class ZoneData:
    zone_id: int
    cpu: float
    ram: float
    hdd: float
    date: str


@dataclass(slots=True, frozen=True)
class LoadData:
    date: str
    cpu: float
    ram: float
    hdd: float


class Database(sqlite3.Connection):
    def __init__(self, db_name):
        super().__init__(db_name)

    def __exit__(self, exc_type, exc_val, exc_tb):
        sqlite3.Connection.__exit__(self, exc_type, exc_val, exc_tb)
        self.close()


class NotifDatabase(Database):
    def __init__(self, db_name):
        super(NotifDatabase, self).__init__(db_name)

    def select_load_where(self, where_str: str):
        """ Get LOAD INFO about Information System """
        all_records = self.execute('SELECT zd.zone_id, zd.date, '
                                   '       zd.cpu, zd.ram, zd.hdd '
                                   'FROM zone_data AS zd '
                                   'INNER JOIN zones ON zd.zone_id=zones.id '
                                   f'WHERE {where_str}').fetchall()
        return [ZoneData(zone_id=record[0],
                         date=record[1],
                         cpu=record[2],
                         ram=record[3],
                         hdd=record[4]) for record in all_records]


class LoadInfoDatabase(Database):
    def __init__(self, db_name, use_last_stamp: bool = False):
        super().__init__(db_name)
        self._table_prefix = 'zn_'
        self.use_last_stamp = use_last_stamp
        if use_last_stamp:
            self.id_last = 0

    def select_data(self, zn_name: str) -> list[LoadData]:
        """ Get current records """
        if self.use_last_stamp:
            result = self.execute(f'SELECT date, cpu, ram, hdd '
                                  f'FROM {self._table_prefix}{zn_name} '
                                  f'WHERE id<>?', (self.id_last,)).fetchall()
        else:
            result = self.execute(f'SELECT date, cpu, ram, hdd '
                                  f'FROM {self._table_prefix}{zn_name}').fetchall()
        return [LoadData(date=item[0],
                         cpu=item[1],
                         ram=item[2],
                         hdd=item[3])
                for item in result]

    def create_table_zone(self, zn_name: str, if_not_exists: bool = True):
        zn_name = inj_value(zn_name)

        if if_not_exists:
            exist_str = 'IF NOT EXISTS'
        else:
            exist_str = ''

        table_cols = """
            id INTEGER NOT NULL,
            date DATETIME NOT NULL,
            cpu FLOAT,
            ram FLOAT,
            hdd FLOAT,
            PRIMARY KEY (id)
        """
        try:
            self.executescript(f'CREATE TABLE {exist_str} {self._table_prefix}{zn_name}({table_cols})')
        except sqlite3.OperationalError as err:
            raise TableExistError(f'[CREATE TABLE] {err}') from err

    def insert_into_zn(self, zn_name, data: list[LoadData]):
        if data:
            zn_name = inj_value(zn_name)
            try:
                self.executemany(f'INSERT INTO {self._table_prefix}{zn_name} (date, cpu, ram, hdd)'
                                 f'VALUES (?, ?, ?, ?)', [(record.date, record.cpu, record.ram, record.hdd)
                                                          for record in data])
            except sqlite3.IntegrityError as err:
                raise DataExistError(f'[INSERT INTO] {err}') from err

    def update_last_data_to_zn(self, zn_name, last_data: LoadData):
        """ Add/Update last data (AS id=self.id_last) with new datetime stamp - datetime.now() """
        if self.use_last_stamp:
            zn_name = inj_value(zn_name)
            cur_data = LoadData(date=str(datetime.now()),
                                cpu=last_data.cpu,
                                ram=last_data.ram,
                                hdd=last_data.hdd)
            try:
                self.execute(f'INSERT INTO {self._table_prefix}{zn_name} (id, date, cpu, ram, hdd) '
                             f'VALUES (?, ?, ?, ?, ?)', (self.id_last, cur_data.date,
                                                         cur_data.cpu, cur_data.ram, cur_data.hdd))
            except sqlite3.IntegrityError:      # this ID ("id_last") is exist
                self.execute(f'UPDATE {self._table_prefix}{zn_name} '
                             f'SET date=:DATE, cpu=:CPU, ram=:RAM, hdd=:HDD '
                             f'WHERE id=:ID_LAST', {'ID_LAST': self.id_last,
                                                    'DATE': cur_data.date,
                                                    'CPU': cur_data.cpu,
                                                    'RAM': cur_data.ram,
                                                    'HDD': cur_data.hdd})

    def view_select_query(self, zn_name):
        zn_name = inj_value(zn_name)
        return f'SELECT cpu, ram, hdd, date as time ' \
               f'FROM {self._table_prefix}{zn_name};'

    def get_table_name(self, name: str) -> str:
        return self._table_prefix + name


class TableExistError(Exception):
    def __init__(self, message=None):
        self.message = 'In database table already exist'
        if message:
            self.message = message
        super(TableExistError, self).__init__(self.message)


class DataExistError(Exception):
    def __init__(self, message=None):
        self.message = 'You try "INSERT INTO" data to database with some UNIQUE data'
        if message:
            self.message = message
        super(DataExistError, self).__init__(self.message)


if __name__ == '__main__':

    # ---------------- Tests: -------------------------
    DB_NAME = '../tests/test.sqlite'
    TABLE_NAME = 'TEST_NAME'
    RAW_DATA = (1, '2022-08-03 00:00:00.000000', 4.0, 8.0, 215.0)

    from os import remove, path
    if path.exists(DB_NAME):
        remove(DB_NAME)

    print('\nConnect to db:')
    with LoadInfoDatabase(DB_NAME) as db:
        print(f'\t{db}')

        print('\nCreate table:')
        db.create_table_zone(zn_name=TABLE_NAME)
        print(f'\tcreated table with name: {db.get_table_name(TABLE_NAME)}')
        try:
            db.create_table_zone(zn_name=TABLE_NAME, if_not_exists=False)
        except (sqlite3.OperationalError, TableExistError) as er:
            assert str(er) == f'[CREATE TABLE] table {db.get_table_name(TABLE_NAME)} already exists'
            print('\texception: OK')

        print('\nINSERT INTO Table:')
        data = [LoadData(date=RAW_DATA[1],
                         cpu=RAW_DATA[2],
                         ram=RAW_DATA[3],
                         hdd=RAW_DATA[4])]
        db.insert_into_zn(zn_name=TABLE_NAME, data=data)
        print(f'\tto {db.get_table_name(TABLE_NAME)} add data: {data}')

        print('\nVerification:')
        query_str = f'SELECT * FROM {db.get_table_name(TABLE_NAME)}'
        query_res = db.execute(query_str).fetchall()
        assert query_res[0] == RAW_DATA
        print(f'\t{query_str}:\n\t\t{query_res}')

        select_res = db.select_data(TABLE_NAME)
        assert select_res[0].date == query_res[0][1]
        print(f'\tSELECT from function:\n\t\t{select_res}')

    remove(DB_NAME)
    # ---------------- end tests -------------------------

    from datetime import datetime
    NOTIF_DB = '../tests/app.db'
    DATA = (24.0, 42.8, 354.0, str(datetime.now()), 53)

    with NotifDatabase(NOTIF_DB) as db:
        # r = db.select_load_where('zones.infsys=35')
        # print(r)
        db.execute('INSERT INTO zone_data (cpu, ram, hdd, date, zone_id) '
                   'VALUES (?, ?, ?, ?, ?)', DATA)

        r = db.select_load_where('zones.infsys=35')
        print(r)
