from prototype import object
from rest import get, put, post

@object
def bridge():
    def path(self):
        return ""

    def url(self):
        return self.baseurl + self.path()

    def info(self):
        return get(self.url())

    def update_state(self):
        self.update(self.info())

    def send(self, part='', **kwargs):
        put(self.url() + part, **kwargs)

    def read(self, path):
        return get(self.baseurl + path)

    def create_rule(self, name, conditions, actions):
        return int(post(self.baseurl + "/rules", name=name, conditions=conditions, actions=actions)["id"])

    def config(self):
        return self(**self.read("/config"))

    def sensors(self):
        @self
        def sensor(self):
            def path(self): return "/sensors/%d" % self.id
        for id, attrs in self.read("/sensors").iteritems():
            yield sensor(id=int(id), **attrs)

    def rules(self):
        for id, attrs in self.read("/rules").iteritems():
            yield self(id=int(id), **attrs)

    def lights(self):
        def path(self):
            return "/lights/%d" % self.id
        def get_state(self):
            def path(self):
                return self.up.path() + "/state"
            return self(path, self.state)
        def send(self, **kw):
            self.up.send("/state", **kw)
        light = self(path, get_state, send)
        for id, attrs in self.read("/lights").iteritems():
            yield light(id=int(id), **attrs)

    return locals()

from autotest import autotest
from config import LOCAL_HUE_API

@autotest
def ConnectBridge():
    b = bridge(baseurl=LOCAL_HUE_API)
    assert b
    config = b.config()
    assert config
    assert config.name == "Nr19"

@autotest
def GetSensors():
    b = bridge(baseurl=LOCAL_HUE_API)
    sensor = (sensor for sensor in b.sensors() if sensor.name == "Daylight").next()
    assert sensor.name == "Daylight", sensor
    assert sensor.config.on == True

@autotest
def GetRules():
    b = bridge(baseurl=LOCAL_HUE_API)
    #rule = b.rules().next()
    #assert "tap-" in rule.name, rule.name

@autotest
def GetLights():
    b = bridge(baseurl=LOCAL_HUE_API)
    lights = b.lights()
    assert lights
    l1 = lights.next()
    assert l1.id == 1, l1.id
    assert l1.name == "Bureaulamp"
    assert l1.modelid == "LCT001"
    assert l1.path() == "/lights/%d" % l1.id

    state = l1.get_state()
    assert state.on in (True, False), state
    assert state.path() == "/lights/%d/state" % l1.id, state.path()
    state.send(on=False)
    assert b.lights().next().state().on == False
    state.send(on=True)
    assert b.lights().next().state().on == True
   
