import requests
from json import dumps

def go(method, *args, **kwargs):
    r = method(*args, **kwargs)
    assert r.status_code == 200, r
    assert len(r.json) == 1, r.json
    response = r.json[0]
    if "success" in response:
        return response["success"]
    else:
        raise Exception("%(description)s (%(address)s)" % response["error"])

def post(url, **kwargs):
    return go(requests.post, url, dumps(kwargs))

def delete(url):
    return go(requests.delete, url)

def put(url, **kwargs):
    return go(requests.put, url, dumps(kwargs))

def get(url):
    r = requests.get(url)
    assert r.status_code == 200, r
    return r.json

from misc import autotest

@autotest
def InvalidURL():
    try:
        post("http:/niks.niet", a=2)
        assert False
    except Exception as e:
        assert str(e) == "HTTPConnectionPool(host='', port=80): Max retries exceeded with url: /niks.niet", e

