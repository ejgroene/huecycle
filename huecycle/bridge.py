from prototype import object
from rest import get, put

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
    def config(self):
        @self
        def config_state(self):
            self.update(self.info()["config"])
        return config_state
    def sensors(self):
        @self
        def sensor_state(self):
            self.subpath = "/sensors"
            self.update_state()
        return sensor_state
    def rules(self):
        @self
        def rules_state(self):
            self.subpath = "/rules"
            self.update_state()
        return rules_state
    def lights(self):
        @self
        def lights_state(self):
            self.subpath = "/lights"
            self.update_state()
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
    assert sensors[1].name == "Daylight"
    assert sensors[1].config.on == True

@autotest
def GetRules():
    b = bridge(baseurl=LOCAL_HUE_API)
    rules = b.rules()
    assert rules
    assert "Turn" in rules[1].name, rules[1].name

@autotest
def GetLights():
    b = bridge(baseurl=LOCAL_HUE_API)
    lights = b.lights()
    assert lights
    assert lights[1].name == "Studeer", lights[1].name
    
