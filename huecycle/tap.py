from requests import put, get
from misc import autotest
from config import LOCAL_HUE_API

def tap(url, n):
    while True:
        r = get(url + "/sensors/%d" % n).json
        yield r["sensors"]["2"]["state"]["buttonevent"]

@autotest
def get_state():
    t = tap(LOCAL_HUE_API, 2)
    s = t.next()
    assert s in (0, 16, 17, 18), s
