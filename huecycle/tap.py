from requests import put, get
from prototype import object
from sensors import sensor, flag_sensor, status_sensor
from rules import button_hit, flag_eq, status_eq, put_light, put_flag

NOEVENT = 00
BUTTON1 = 34
BUTTON2 = 16
BUTTON3 = 17
BUTTON4 = 18

def tap(url, n):
    while True:
        r = get(url + "/sensors/%d" % n).json
        yield r["state"]["buttonevent"]

@object
def tap_control():

    def init(self):
        self._tap_sensor = sensor(baseurl=self.bridge.baseurl, id=self.id)
        assert self._tap_sensor.info()["type"] == "ZGPSwitch", "Sensor %s is not a Tap." % self.id
        self.flag = flag_sensor(baseurl=self.bridge.baseurl, name="tap-%s-flag" % self.id)
        self.flag.init()
        self.status = status_sensor(baseurl=self.bridge.baseurl, name="tap-%s-status" % self.id)
        self.status.init()
        def put_lights(**kwargs):
            return [put_light(light.id, **kwargs) for light in self.lights]
        def create_onoff_rule(name, btn, s0, s1):
            self.bridge.create_rule("tap-%s-%s" % (self.id, name),
                button_hit(self.id, btn) + flag_eq(self.flag.id, s0),
                put_lights(on=s1) + [put_flag(self.flag.id, flag=s1)])
        create_onoff_rule("on", BUTTON1, "false", True)
        create_onoff_rule("off", BUTTON1, "true", False)
        def create_rule(btn, s0, s1, bri):
            self.bridge.create_rule("tap-%s-step-%d-%d" % (self.id, s0, s1),
                button_hit(self.id, btn) + status_eq(self.status.id, str(s0)),
                put_lights(bri=bri) + [put_flag(self.status.id, status=s1)])
        create_rule(BUTTON4, 0, 1, 127)
        create_rule(BUTTON4, 1, 2, 191)
        create_rule(BUTTON4, 2, 3, 255)
        create_rule(BUTTON2, 3, 2, 191)
        create_rule(BUTTON2, 2, 1, 127)
        create_rule(BUTTON2, 1, 0,  63)

    def external_switch(self):
        def turn_on(self, on):
            self.flag.state().send(flag=on)
        def send(self, bri=0, **kwargs):
            self.status.state().send(status=max(0, bri - 32) // 64)
        return self(turn_on, send)

    return locals()

from autotest import autotest
from bridge import bridge
from config import LOCAL_HUE_API
from rules import delete_all_rules

delete_all_rules(LOCAL_HUE_API)

b = bridge(baseurl=LOCAL_HUE_API)

@object
def mockbridge(self):
    pass

def find(source, name):
    return (o for o in source if o.name == name).next()

@autotest
def get_state():
    t = tap(LOCAL_HUE_API, 2)
    s = t.next()
    assert s in (NOEVENT, BUTTON1, BUTTON2, BUTTON3, BUTTON4), s

@autotest
def TapControl():
    tap = tap_control(bridge=b, id=2, lights=(object(id=7),object(id=9)))
    tap.init()

    flag = find(b.sensors(), "tap-2-flag")
    assert flag["type"] == "CLIPGenericFlag"
    assert flag["state"]["flag"] == False
    assert flag["name"] == "tap-2-flag"

    status = find(b.sensors(), "tap-2-status")
    assert status["type"] == "CLIPGenericStatus"
    assert status["state"]["status"] == 0
    assert status["name"] == "tap-2-status"

    on_rule = find(b.rules(), "tap-%s-on" % 2)
    assert on_rule["name"] == "tap-2-on"
    assert on_rule["actions"][0] == dict(address="/lights/7/state", method="PUT", body=dict(on=True))
    assert on_rule["actions"][1] == dict(address="/lights/9/state", method="PUT", body=dict(on=True))
    assert on_rule["actions"][2] == dict(address="/sensors/%s/state" % flag.id, method="PUT", body=dict(flag=True))
    assert on_rule["conditions"][0] == dict(address="/sensors/2/state/buttonevent", operator="eq", value="34")
    assert on_rule["conditions"][1] == dict(address="/sensors/2/state/lastupdated", operator="dx")
    assert on_rule["conditions"][2] == dict(address="/sensors/%s/state/flag" % flag.id, operator="eq", value="false")

    off_rule = find(b.rules(), "tap-%s-off" % 2)
    assert off_rule["name"] == "tap-2-off"
    assert off_rule["actions"][0] == dict(address="/lights/7/state", method="PUT", body=dict(on=False))
    assert off_rule["actions"][1] == dict(address="/lights/9/state", method="PUT", body=dict(on=False))
    assert off_rule["actions"][2] == dict(address="/sensors/%s/state" % flag.id, method="PUT", body=dict(flag=False))
    assert off_rule["conditions"][0] == dict(address="/sensors/2/state/buttonevent", operator="eq", value="34")
    assert off_rule["conditions"][1] == dict(address="/sensors/2/state/lastupdated", operator="dx")
    assert off_rule["conditions"][2] == dict(address="/sensors/%s/state/flag" % flag.id, operator="eq", value="true")

    def assert_step_rule(s0, s1, bri, btn):
        rule = find(b.rules(), "tap-2-step-%d-%d" % (s0, s1))
        assert rule["conditions"][0] == dict(address="/sensors/2/state/buttonevent", operator="eq", value=str(btn))
        assert rule["conditions"][1] == dict(address="/sensors/2/state/lastupdated", operator="dx")
        assert rule["conditions"][2] == dict(address="/sensors/%s/state/status" % status.id, operator="eq", value=str(s0)), rule
        assert rule["actions"][0] == dict(address="/lights/7/state", method="PUT", body=dict(bri=bri)), rule
        assert rule["actions"][1] == dict(address="/lights/9/state", method="PUT", body=dict(bri=bri)), rule
        assert rule["actions"][2] == dict(address="/sensors/%s/state" % status.id, method="PUT", body=dict(status=s1))
    assert_step_rule(0, 1, 127, 18)
    assert_step_rule(1, 2, 191, 18)
    assert_step_rule(2, 3, 255, 18)
    assert_step_rule(3, 2, 191, 16)
    assert_step_rule(2, 1, 127, 16)
    assert_step_rule(1, 0,  63, 16)

@autotest
def ExternalSwitch():
    tap = tap_control(bridge=b, id=2, lights=(object(id=1),))
    tap.init()
    flag = tap.flag.id
    switch = tap.external_switch()
    assert switch
    switch.turn_on(False)
    assert (s for s in b.sensors() if s.id == flag).next().state["flag"] == False
    switch.turn_on(True)
    assert (s for s in b.sensors() if s.id == flag).next().state["flag"] == True
    
@autotest
def ExternalStatus():
    tap = tap_control(bridge=b, id=2, lights=(object(id=1),))
    tap.init()
    switch = tap.external_switch()
    switch.send(bri=0)
    def status():
        return (s for s in b.sensors() if s.id == tap.status.id).next()
    assert status().state["status"] == 0
    switch.send(bri=95)
    assert status().state["status"] == 0
    switch.send(bri=96)
    assert status().state["status"] == 1
    switch.send(bri=159)
    assert status().state["status"] == 1
    switch.send(bri=160)
    assert status().state["status"] == 2
    switch.send(bri=223)
    assert status().state["status"] == 2
    switch.send(bri=224)
    assert status().state["status"] == 3
    switch.send(bri=255)
    assert status().state["status"] == 3



@autotest
def InvalidTapId():
    tap = tap_control(bridge=b, id=1)
    try:
        tap.init()
        assert false
    except Exception as e:
        assert str(e) == "Sensor 1 is not a Tap.", str(e)
    tap = tap_control(bridge=b, id=399)
    try:
        tap.init()
        assert false
    except Exception as e:
        assert str(e) == "resource, /sensors/399, not available (/sensors/399)", str(e)

