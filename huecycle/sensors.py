from rest import get, post, put, delete
from json import dumps
from prototype import object

def delete_all_sensors():
    sensors = get(LOCAL_HUE_API + "/sensors")
    for k, v in ((k, v) for k, v in sensors.iteritems() if v["manufacturername"] == "ErikGroeneveld"):
        delete(LOCAL_HUE_API + "/sensors/%s" % k)

@object
def sensor():
    def path(self):
        return "/sensors/%s" % self.id

    def url(self):
        return self.baseurl + self.path()

    def info(self):
        return get(self.url())

    def send(self, **data):
        put(self.url(), **data)

    def config(self):
        def path(self):
            return self.up.path() + "/config"
        def set(self, val):
            self.send(on=val)
        return self(set, path, **self.info()["config"])

    def state(self):
        def path(self):
            return self.up.path() + "/state"
        def set(self, val):
            self.send(**{self.attr_name:val})
        return self(set, path, **self.info()["state"])

    return locals()

tap = sensor()

@sensor
def synthetic_sensor():
    manufacturername = "ErikGroeneveld"
    swversion = "0.1"

    def create(self, **data):
        return post(self.baseurl + "/sensors", **data)

    def init(self):
        r = self.create(name=self.name, type=self.type, modelid=self.type,
                        manufacturername=self.manufacturername, swversion=self.swversion, uniqueid=self.name)
        self.id = int(r["id"])

    return locals()

flag_sensor = synthetic_sensor(type="CLIPGenericFlag", attr_name="flag")
status_sensor = synthetic_sensor(type="CLIPGenericStatus", attr_name="status")


from misc import autotest
from config import LOCAL_HUE_API

@autotest
def ReadTap():
    tap1 = tap(id=2)
    assert tap1.id == 2
    assert tap1.path() == "/sensors/2"
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

@autotest
def ToggleFlagSensor():
    flag1 = flag_sensor(baseurl=LOCAL_HUE_API, name="testflag")
    flag1.init()
    Id = flag1.id
    assert 0 < Id < 100, Id
    assert flag1.path() == "/sensors/%s" % Id, flag1.path()
    state = flag1.state()
    assert "flag" in state
    assert state.flag == False
    state.set(True)
    state = flag1.state()
    assert state.flag == True
    assert state.path() == "/sensors/%s/state" % Id


@autotest
def CreateAndSetStatusSensor():
    status1 = status_sensor(baseurl=LOCAL_HUE_API, name="testflag")
    status1.init()
    Id = status1.id
    assert 0 < Id < 100, Id
    assert status1.path() == "/sensors/%s" % Id, status1.path()
    state = status1.state()
    assert "status" in state
    assert state.status == 0, state
    state.set(2)
    state = status1.state()
    assert state.status == 2, state
    assert state.path() == "/sensors/%s/state" % Id

@autotest
def DeleteAllSensors():
    delete_all_sensors()
