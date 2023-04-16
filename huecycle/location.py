import zoneinfo
from prototype3 import prototype
from ephem import Observer, Sun, to_timezone


utc = zoneinfo.ZoneInfo("UTC")


def ephem_to_datetime(e):
    return to_timezone(e, utc).replace(second=0, microsecond=0)


def location(lat, lon, elevation=6.0):
    assert isinstance(lat, str), lat
    assert isinstance(lon, str), lon
    assert isinstance(elevation, float), elevation

    class mylocation(prototype):
        sun = Sun()  # used for tracking sun rise and set
        obs = Observer()
        obs.lon = lon  # longitude in "52:01.224" format
        obs.lat = lat  # latitude in "5:41.065" format
        obs.elevation = 6.0  # twilight angle (civil = 6)

        def next_rising(self, start=None):
            return ephem_to_datetime(self.obs.next_rising(self.sun, start=start))

        def next_transit(self, start=None):
            return ephem_to_datetime(self.obs.next_transit(self.sun, start=start))

        def next_setting(self, start=None):
            return ephem_to_datetime(self.obs.next_setting(self.sun, start=start))

    return mylocation


# TODO test (extracted from cct_cycle)
