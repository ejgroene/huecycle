import requests
from json import dumps

IGNORED_ERRORS = (201,)

def go(method, *args, **kwargs):
    r = method(*args, **kwargs)
    assert r.status_code == 200, r
    if len(r.json) == 1:
        response = r.json[0]
        return check_status(response)

def check_status(response):
    if isinstance(response, list):
        response = response[0]
    if "error" in response:
        if response["error"]["type"] not in IGNORED_ERRORS:
            raise Exception("%(description)s (%(address)s)" % response["error"])
        return
    if "success" in response:
        return response["success"]
    return response

def post(url, **kwargs):
    return go(requests.post, url, dumps(kwargs))

def delete(url):
    return go(requests.delete, url)

def put(url, **kwargs):
    return go(requests.put, url, dumps(kwargs))

def get(url):
    r = requests.get(url)
    assert r.status_code == 200, r
    return check_status(r.json)

from misc import autotest

@autotest
def InvalidURL():
    try:
        post("http:/niks.niet", a=2)
        assert False
    except Exception as e:
        assert str(e) == "HTTPConnectionPool(host='', port=80): Max retries exceeded with url: /niks.niet", e

@autotest
def IgnoreDeviceOff():
    from config import LOCAL_HUE_API
    put(LOCAL_HUE_API + "/lights/1/state", on=False)
    put(LOCAL_HUE_API + "/lights/1/state", bri=100)
    put(LOCAL_HUE_API + "/lights/1/state", on=True)
