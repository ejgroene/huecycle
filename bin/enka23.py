from ephem import Observer, Sun ,localtime
from math import tan, pi

def Ede():
    loc = Observer()
    loc.horizon = "0"
    loc.lat = str(52.)
    loc.lon = str(5.6)
    loc.elevation = 24.5
    return loc

ede = Ede()
sun = Sun()

def print_for_date(date):
    for m in range(0, 24*60, 60):
        h_bos = 17.85
        h_nok = 7
        ede.date = "%s %s:%s:00" % (date, m / 60, m % 60) # UTC
        sun.compute(ede)
        if sun.alt > 0:
            t = localtime(ede.date)
            print("%s  azimut:%s  hoogte:%s  schaduw:%d  (nok:%d)" % (t, sun.az, sun.alt, h_bos/tan(sun.alt), (h_bos-h_nok)/tan(sun.alt)))

print("== winter ==")
print_for_date("2014/12/21")
print()
print("== lente ==")
print_for_date("2014/03/21")
print()
print("== zomer ==")
print_for_date("2014/06/21")
print()
print("== herfst ==")
print_for_date("2014/09/21")
