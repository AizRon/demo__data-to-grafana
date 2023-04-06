# DC_Load from Notif

Для отрисовки графиков нагрузки ##### в Grafana (по данным с http://#####/notif/is_data/0)


> Данный скрипт был необходим для отрисовки данных (из сторонней базы данных) по нагруженности информационных систем,
> где в явном виде данные нельзя было передать в Grafana.
> 
> Скрипт вычленяет и обрабатывает эти данные, создавая отдельную базу, которая используется в Grafana.
> 
> Некоторые конкретные данные заменены на "#####"



## Описание
После запуска `run-update.sh` (с указанием аргумента - пути до сервера:папки (как в `ssh (scp)`)):

- читается конфиг файл `conf.yml`;
- для каждой информационной системы (указанными в конфиге под ключем `infsyss`):
  - делается запрос (см. ниже) к оригинальной базе данных из репозитория проекта Notif (путь до базы указан в конфиге под ключем `databases.src_db`)
  - полученные данные обрабатываются для предоставление в новом виде _(суммируются значения по временным меткам)_
  - обработанные данные заносятся в новую таблицу _(в новую, заранее созданную, БД - `databases.dst_db`)_ (имя таблицы указывается на основе имени в конфиге под ключем `[infsyss]name`)
- читается и сохраняется в переменную путь до новой базы данных (запуск скрипта `update-load_table.py` с аргументом `--get-db-path`)
- копирование новой БД на сервер с Grafana посредством `rsync`

> Ведется логирование в файл (по умолчанию `logs/update.log`, см. конфиг), если указано имя файла в конфиге под ключем `logging.filename`, иначе (если оно пустое) сообщения выводятся в консоль

## Как запустить

### Команда:
* ```commandline
  run-update.sh USER@HOST:DEST_DIR_DB
  ```
* ```commandline
  bash run-update.sh USER@HOST:DEST_DIR_DB
  ```
> USER@HOST - SSH опции для соединения с сервером (используются `rsync`)

> DEST_DIR_DB - путь к папке с базой данных на удаленном сервере _(Grafana)_

### Подробно:
1.      git clone https://#####/service-admins/grafana/dc_load-from-notif.git
2.      cd dc_load-from-notif
3. Создать/отредактировать конфигурационный файл `conf.yml` _(аналогично `conf.yml.example`)_
4. Отредактировать переменную `PATH_TO_SSH_KEY` в стартовом скрипте `run-update.sh` - путь до приватного ключа _(создайте или возьмите в Psono)_
5.      sudo crontab -e
6. Внести запись о запуске, например:

```commandline
0 0 * * * bash /usr/local/share/dc_load-from-notif/run-update.sh rsync-db@#####:/opt/docker/grafana/usr/share/grafana/notif-db
```

## Используемый запрос к БД Notif
`src/db.py`:
```commandline
SELECT zd.zone_id, zd.date, 
       zd.cpu, zd.ram, zd.hdd 
FROM zone_data AS zd 
INNER JOIN zones ON zd.zone_id=zones.id 
WHERE ...{{ QUERY_STRING_FROM_CONFIG }}
```
Например, если `QUERY_STRING_FROM_CONFIG` = `zones.infsys=35`, то
данный запрос будет соответствовать (похож) представленным данным: http://#####/notif/is_data/35
## Шаблон схемы для таблиц в новой БД
`src/db.py`:
```commandline
CREATE TABLE zn_{{ INFSYS_NAME_FROM_CONFIG }}(
    id INTEGER NOT NULL,
    date DATETIME NOT NULL,
    cpu FLOAT,
    ram FLOAT,
    hdd FLOAT,
    PRIMARY KEY (id)
)
```
> Если в таблице присутствует ID=0, то это данные самого последнего значения с текущей меткой времени (на момент запуска скрипта)

## Часть схемы БД Notif
```commandline
CREATE TABLE zone_data (
        id INTEGER NOT NULL,
        cpu FLOAT,
        ram FLOAT,
        hdd FLOAT,
        sfup BOOLEAN,
        date DATETIME,
        note VARCHAR(255),
        zone_id INTEGER,
        PRIMARY KEY (id),
        FOREIGN KEY(zone_id) REFERENCES zones (id)
)
```
```commandline
CREATE TABLE zones (
        id INTEGER NOT NULL,
        name VARCHAR(255),
        note VARCHAR(255),
        infsys INTEGER,
        PRIMARY KEY (id),
        FOREIGN KEY(infsys) REFERENCES infsyss (id)
)
```
```commandline
CREATE TABLE IF NOT EXISTS "infsyss" (
        id INTEGER NOT NULL,
        f_name VARCHAR(255) DEFAULT ('') NOT NULL,
        name VARCHAR(255) DEFAULT ('') NOT NULL,
        note VARCHAR(255),
        infsys_type_id INTEGER,
        start_year INTEGER,
        PRIMARY KEY (id),
        CONSTRAINT uq_infsyss_f_name UNIQUE (f_name),
        CONSTRAINT uq_infsyss_name UNIQUE (name),
        UNIQUE (f_name),
        UNIQUE (name),
        FOREIGN KEY(infsys_type_id) REFERENCES infsys_types (id)
)
```
