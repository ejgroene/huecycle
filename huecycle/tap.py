from requests import put, get
from misc import autotest
from config import LOCAL_HUE_API

NOEVENT = 00
BUTTON1 = 34
BUTTON2 = 16
BUTTON3 = 17
BUTTON4 = 18

def tap(url, n):
    while True:
        r = get(url + "/sensors/%d" % n).json
        yield r["state"]["buttonevent"]

@autotest
def get_state():
    t = tap(LOCAL_HUE_API, 2)
    s = t.next()
    assert s in (NOEVENT, BUTTON1, BUTTON2, BUTTON3, BUTTON4), s
