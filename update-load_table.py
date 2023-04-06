from src.db import NotifDatabase, LoadInfoDatabase, TableExistError, DataExistError
from src.handler import LoadHandler, LoadData
from src.config import Config, InfsysConf, DatabasesConf

import os.path
import sys
import logging


cfg = Config(cfg_path='conf.yml')
logger = logging.getLogger('MAIN')

# If you change this value - need delete old database (if she exists)
# (databases.DEST_DB)
CREATE_LAST_STAMP: bool = True


def _get_not_present_data(db: LoadInfoDatabase, zn_name: str,
                          new_data: list[LoadData]) -> list[LoadData] | list:
    """ Difference list[LoadData] between present data (in database) and new data (data_to_db) """
    old_data = db.select_data(zn_name=zn_name)
    return new_data[len(old_data):]


def add_data_to_db(db: LoadInfoDatabase, zn_name: str,
                   data: list[LoadData], last_data: LoadData):
    """ Used for condition: CREATE_LAST_STAMP """
    if CREATE_LAST_STAMP:
        db.update_last_data_to_zn(zn_name=zn_name, last_data=last_data)
    db.insert_into_zn(zn_name=zn_name, data=data)


def update_load_table(inf_sys: InfsysConf,
                      databases: DatabasesConf):
    """ Main function:

     - Get origin data from Notif-database;
     - Prepare data for loading into new database;
     - Add data to new database
     """
    # logger.info(f'Collect data of "{inf_sys.NAME}"')

    # Get origin data from Notif-database
    with NotifDatabase(databases.SRC_DB) as notif_db:
        data = notif_db.select_load_where(where_str=inf_sys.QUERY_WHERE)

    if data[0]:
        # Prepare data for loading into new database
        handler = LoadHandler(zones_data=data)
        data_to_db = handler.create_load_data()
        last_record = data_to_db[-1]

        # Add data to new database
        with LoadInfoDatabase(databases.DEST_DB,
                              use_last_stamp=CREATE_LAST_STAMP) as new_db:
            zone_name = inf_sys.NAME

            try:
                new_db.create_table_zone(zn_name=zone_name, if_not_exists=False)
                add_data_to_db(db=new_db,
                               zn_name=zone_name,
                               data=data_to_db,
                               last_data=last_record)

            except (TableExistError, DataExistError):
                data_to_db = _get_not_present_data(db=new_db,
                                                   new_data=data_to_db,
                                                   zn_name=zone_name)
                add_data_to_db(db=new_db,
                               zn_name=zone_name,
                               data=data_to_db,
                               last_data=last_record)

        # .. write result
        if data_to_db:
            logger.info(f'[{inf_sys.NAME}]: Data load to "{databases.DEST_DB}" - {len(data_to_db)} new records:\n'
                        f'{view(data_to_db)}')
        else:
            logger.info(f'[{inf_sys.NAME}]: not have new data')


def view(data: list | tuple) -> str:
    output = "\n\t".join([str(row) for row in data])
    return f'\n\t{output}\n'


if __name__ == '__main__':
    if cfg.error:
        sys.exit(1)

    try:
        conf = cfg.get_config()

        log_conf = conf.logging

        if len(sys.argv) == 1:
            logging.basicConfig(
                filename=log_conf.LOGFILE,
                format=log_conf.FORMAT,
                level=log_conf.LEVEL,
                filemode=log_conf.FILEMODE
            )

            if os.path.exists(conf.databases.SRC_DB) is False:
                logger.error(f'[DATABASE NOT EXIST] Cannot find source database (notif-db): {conf.databases.SRC_DB}')
                sys.exit(1)

            for zone in conf.infsyss:
                update_load_table(inf_sys=zone,
                                  databases=conf.databases)

        elif sys.argv[1] == '--get-db-path':
            print(conf.databases.DEST_DB)

        else:
            sys.exit(1)

    except Exception as e:
        logger.error('Exception occurred', exc_info=True)
        sys.exit(1)
