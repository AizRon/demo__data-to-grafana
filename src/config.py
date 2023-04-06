from dataclasses import dataclass
import yaml
from typing import Literal
import logging


logger = logging.getLogger('CONFIG')


@dataclass(slots=True, frozen=True)
class DatabasesConf:
    SRC_DB: str
    DEST_DB: str


@dataclass(slots=True, frozen=True)
class InfsysConf:
    NAME: str
    QUERY_WHERE: str


@dataclass(slots=True, frozen=True)
class LoggerConf:
    LOGFILE: str
    FILEMODE: Literal['a', 'w']
    LEVEL: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR']
    FORMAT: str


@dataclass(slots=True, frozen=True)
class ConfigData:
    databases: DatabasesConf
    infsyss: list[InfsysConf]
    logging: LoggerConf


class Config:
    def __init__(self, cfg_path: str):
        self.path = cfg_path
        self.error = None
        self.raw_cfg = self._read_cfg()
        self._check_cfg()

    def _check_cfg(self):
        if self.error is None:
            keys = {
                'databases': ['src_db', 'dst_db'],
                'logging': ['filename', 'level', 'format', 'filemode'],
                'infsyss': ['name', 'query_where']
            }
            try:
                for key in keys:
                    if key == 'infsyss':
                        assert type(self.raw_cfg[key]) is list, 'Wrong data type: ' \
                                                                'key "infsyss" must be list (see comments)'
                        for inf_sys in self.raw_cfg[key]:
                            _ = [inf_sys[sub_key] for sub_key in keys[key]]
                    else:
                        for sub_key in keys[key]:
                            _ = self.raw_cfg[key][sub_key]
                            if key == 'logging' and sub_key == 'filemode':
                                assert self.raw_cfg[key][sub_key] in ('w', 'a'), 'Wrong value of "logging.filemode" ' \
                                                                                 'must be "w" or "a"'
            except KeyError as err:
                self.error = f'[CONFIG ERROR] Wrong key in config: look key(keys) - {err}'
            except AssertionError as err:
                self.error = f'[CONFIG ERROR] {err}'

        if self.error:
            logger.error(self.error)

    def _read_cfg(self) -> dict:
        try:
            with open(self.path) as file:
                conf = yaml.safe_load(file)
        except FileNotFoundError as err:
            self.error = f'[ERROR] [CONFIG NOT FOUND] {err}'
            conf = {}

        return conf

    def get_config(self) -> ConfigData:
        return ConfigData(databases=DatabasesConf(SRC_DB=self.raw_cfg['databases']['src_db'],
                                                  DEST_DB=self.raw_cfg['databases']['dst_db']),
                          infsyss=[
                              InfsysConf(NAME=remove_space(inf_sys['name']),
                                         QUERY_WHERE=inf_sys['query_where'])
                              for inf_sys in self.raw_cfg['infsyss']
                          ],
                          logging=LoggerConf(LOGFILE=self.raw_cfg['logging']['filename'],
                                             LEVEL=self.raw_cfg['logging']['level'],
                                             FORMAT=self.raw_cfg['logging']['format'],
                                             FILEMODE=self.raw_cfg['logging']['filemode']))


def remove_space(string: str) -> str:
    return string.strip().replace(' ', '_')


if __name__ == '__main__':
    cfg = Config('../conf.yml')
    print(cfg.raw_cfg, '\n----------\n')

    conf = cfg.get_config()
    print(f'Databases:\n\t{conf.databases}\n')
    print(f'Logging:\n\t{conf.logging}\n')
    print('Infsyss:')
    [print(f'\t{i_sys}') for i_sys in conf.infsyss]
