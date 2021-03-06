import requests
from json import dumps
from time import sleep, time

IGNORED_ERRORS = (201,)

total_reqs = 0
start_time = time()

def try_forever(method, *args, **kwargs):
    global total_reqs
    total_reqs += 1
    if total_reqs % 100 == 0:
        print " * requests/second:", total_reqs / (time() - start_time)
    r = None
    while r is None:
        # Hue is so unreliable, we just keep trying....
        try:
            r = method(*args, **kwargs)
        except requests.exceptions.RequestException as e:
            print e, args, kwargs
            sleep(5)
    assert r.status_code == 200, r
    return r

def go(method, *args, **kwargs):
    r = try_forever(method, *args, **kwargs)
    if len(r.json) >= 1:
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
    r = try_forever(requests.get, url)
    return check_status(r.json)

