from prototype import object
from rest import get, put, post

@object
def bridge(self):
    def url(self):
        return self.baseurl + (self.subpath if self.subpath else "")
    def info(self):
        return get(self.url())
    def update_state(self):
        self.update(self.info())
    def send(self, part, **kwargs):
        put(self.url() + part, **kwargs)
    def create_rule(self, name, conditions, actions):
        return int(post(self.baseurl + "/rules", name=name, conditions=conditions, actions=actions)["id"])
    def config(self):
        @self
        def config_state(self):
            self.update(self.info()["config"])
        return config_state
    def sensors(self):
        @self
        def sensor_state(self):
            self.subpath = "/sensors"
            self.sensors = object(self, **self.info())
        return sensor_state
    def rules(self):
        @self
        def rules_state(self):
            self.subpath = "/rules"
            self.rules = object(self, **self.info())
        return rules_state
    def lights(self):
        @self
        def lights_state(self):
            self.subpath = "/lights"
            self.lights = object(self, **self.info())
        return lights_state

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
    sensors = b.sensors()
    assert sensors
    assert sensors.sensors[1].name == "Daylight"
    assert sensors.sensors[1].config.on == True

@autotest
def GetRules():
    b = bridge(baseurl=LOCAL_HUE_API)
    rules = b.rules()
    assert rules
    #assert "Turn" in rules.rules[1].name, rules.rules[1].name

@autotest
def GetLights():
    b = bridge(baseurl=LOCAL_HUE_API)
    lights = b.lights()
    assert lights
    assert lights.lights[1].name == "Studeer", lights[1].name
    
