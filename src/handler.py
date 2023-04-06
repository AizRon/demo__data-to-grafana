from src.db import LoadData, ZoneData


class LoadHandler:
    def __init__(self, zones_data: list[ZoneData]):
        self.infsys = zones_data
        self.data_to_db = []
        self.read_id = []
        self.sum_load = (0, 0, 0)       # (cpu, ram, hdd)

    def _add_data_to_db(self, zone: ZoneData):
        self.sum_load = (self.sum_load[0] + zone.cpu,
                         self.sum_load[1] + zone.ram,
                         self.sum_load[2] + zone.hdd)

        self.data_to_db.append(LoadData(date=zone.date,
                                        cpu=round(self.sum_load[0], 2),
                                        ram=round(self.sum_load[1], 2),
                                        hdd=round(self.sum_load[2], 2)))
        self.read_id.append(zone.zone_id)

    def create_load_data(self) -> list[LoadData]:
        for row in self.infsys:
            if row.zone_id not in self.read_id:
                self._add_data_to_db(zone=row)
            else:
                old_vals = [item for item in self.infsys
                            if item.zone_id == row.zone_id and item.date < row.date]
                old_vals = old_vals[-1]

                self._add_data_to_db(zone=ZoneData(zone_id=row.zone_id,
                                                   cpu=(row.cpu - old_vals.cpu),
                                                   ram=(row.ram - old_vals.ram),
                                                   hdd=(row.hdd - old_vals.hdd),
                                                   date=row.date))
        return self.data_to_db


if __name__ == '__main__':

    # Tests:

    # DON'T CHANGE VALUES (cpu, ram, hdd) - this used for assert
    # [ (zone_id, datetime, cpu, ram, hdd), ... ]
    RAW_DATA = [(1, '2022-08-03 12:21:26.566858', 4.0, 8.0, 215.0),         # +
                (2, '2022-08-03 12:21:26.574630', 36.0, 76.0, 1500.0),      # +
                (3, '2022-08-03 12:21:26.581471', 32.0, 42.0, 1024.0),      # +
                (2, '2022-08-03 12:22:22.222222', 4.0, 16.0, 32.0),         # + -(36.0, 76.0, 1500.0)
                (3, '2022-08-03 12:33:33.333333', 123.0, 234.0, 2048.0),    # + -(32.0, 42.0, 1024.0)
                (4, '2022-08-03 13:00:00.000000', 1.0, 1.0, 1.0),           # +
                (2, '2022-08-03 13:22:22.222222', 16.0, 32.0, 64.0)]        # + -(4.0, 16.0, 32.0)
    ZONES_DATA = [ZoneData(row[0], row[2], row[3], row[4], row[1]) for row in RAW_DATA]

    print('\nCreate handler object:')
    handler = LoadHandler(zones_data=ZONES_DATA)
    for i in range(len(handler.infsys)):
        assert handler.infsys[i].date == RAW_DATA[i][1]
    print(f'\tcreated: {handler}')

    print('\nCreate LOAD data:')
    res_data = handler.create_load_data()
    assert (res_data[-1].cpu, res_data[-1].ram, res_data[-1].hdd) == (144.0, 275.0, 2328.0)
    [print(f'\t{i}') for i in res_data]
