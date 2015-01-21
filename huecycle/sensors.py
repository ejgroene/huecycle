from rest import get, post, put
from json import dumps
from prototype import object

def delete_all_sensors():
    sensors = get(LOCAL_HUE_API + "/sensors")
    for k, v in ((k, v) for k, v in sensors.json.iteritems() if v["manufacturername"] == "ErikGroeneveld"):
        delete(LOCAL_HUE_API + "/sensors/%s" % k)

def create_sensor(API, name, type):
    r = post(API + "/sensors", dumps(dict(name=name, type=type, modelid=type,
                                    manufacturername="ErikGroeneveld", swversion="0.1", uniqueid=name)))
    return r.json[0]["success"]["id"]

@object
def sensor(self):
    def address(self): return "/sensors/%s" % self.id
    def url(self): return self.baseurl + self.address()
    def info(self): return get(self.url())
    def state(self): return self.info()["state"]
    def send(self, part, **data):
        put(self.url() + part, **data)
    def config(self):
        @self
        def config_state(self):
            self.update(self.info()["config"])
            def set(self, val):
                self.send("/config", on=val)
        return config_state

@sensor
def tap(self):
    pass

from misc import autotest
from config import LOCAL_HUE_API

@autotest
def ReadTap():
    tap1 = tap(id=2)
    assert tap1.id == 2
    assert tap1.address() == "/sensors/2"
    tap1.baseurl = LOCAL_HUE_API
    state = tap1.state()
    assert "lastupdated" in state
    assert "buttonevent" in state

@autotest
def ReadAndWriteConfig():
    tap1 = tap(id=2)
    tap1.baseurl = LOCAL_HUE_API
    config = tap1.config()
    assert "on" in config
    assert config.on in (True, False)
    config.set(False)
    config = tap1.config()
    assert config.on == False
    config.set(True)
    config = tap1.config()
    assert config.on == True


