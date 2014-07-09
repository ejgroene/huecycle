from config import LOCAL_HUE_API
from requests import put, get
from json import dumps
from time import sleep
from misc import autostart, lamp


l = lamp(LOCAL_HUE_API + "lights/1")

l.send(dict(hue=    0, sat=255))    #  1000 K
l.send(dict(hue=10500, sat=255))    #  1500 K
l.send(dict(hue=12521, sat=255))    #  2000 K
l.send(dict(hue=34534, sat=240))    #  6500 K
l.send(dict(hue=46920, sat=255))    # 10000 K

# This represent a night phase, with rising moon going into a stary night

# phase 1: from approx 1000K to approx 1500K
for hue in range(0, 10500, 200):
    l.send(dict(hue=hue, sat=255))

# phase 2: from approx 1500K to 2000K
for hue in range(10500, 12521, 200):
    sat = 225 + (12521-hue)/(12521-10500.) * (255-225)
    l.send(dict(hue=hue, sat=int(sat)))
    
# phase 3: from 2000k to 6500K:
for ct in range(2000, 6500, 100):
    l.send(dict(ct=1000000/ct))

# phase 4: from 6500K and beyond, to approx 10,000 ??
for hue in range(34534, 46920, 200):
    sat = 240 + (hue-34534)/(46920-34534.) * (255-240)
    l.send(dict(hue=hue, sat=int(sat)))

