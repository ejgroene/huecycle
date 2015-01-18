from requests import post
from json import dumps

def delete_all_sensors():
    sensors = get(LOCAL_HUE_API + "/sensors")
    for k, v in ((k, v) for k, v in sensors.json.iteritems() if v["manufacturername"] == "ErikGroeneveld"):
        delete(LOCAL_HUE_API + "/sensors/%s" % k)

def create_sensor(API, name, type):
    r = post(API + "/sensors", dumps(dict(name=name, type=type, modelid=type,
                                    manufacturername="ErikGroeneveld", swversion="0.1", uniqueid=name)))
    return r.json[0]["success"]["id"]

