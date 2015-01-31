from requests import put, get
from prototype import object
from sensors import sensor, flag_sensor, status_sensor
from rules import button_hit, flag_eq, put_light, put_flag

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
def tap_control(self):
    def init(self):
        self._tap_sensor = sensor(baseurl=self.bridge.baseurl, id=self.id)
        assert self._tap_sensor.info()["type"] == "ZGPSwitch", "Sensor %s is not a Tap." % self.id
        self.flag = flag_sensor(baseurl=self.bridge.baseurl, name="tap-%s-flag" % self.id)
        self.flag.init()
        self.status = status_sensor(baseurl=self.bridge.baseurl, name="tap-%s-status" % self.id)
        self.status.init()
        self.bridge.create_rule("tap-%s-on" % self.id,
            button_hit(self.id, BUTTON1) + flag_eq(self.flag.id, "false"),
            [put_light(light, on=True) for light in self.lights] + [put_flag(self.flag.id, flag=True)])
        self.bridge.create_rule("tap-%s-off" % self.id,
            button_hit(self.id, BUTTON1) + flag_eq(self.flag.id, "true"),
            [put_light(light, on=False) for light in self.lights] + [put_flag(self.flag.id, flag=False)])

from autotest import autotest
from bridge import bridge
from config import LOCAL_HUE_API
from rules import delete_all_rules

delete_all_rules(LOCAL_HUE_API)

b = bridge(baseurl=LOCAL_HUE_API)

@object
def mockbridge(self):
    pass

@autotest
def get_state():
    t = tap(LOCAL_HUE_API, 2)
    s = t.next()
    assert s in (NOEVENT, BUTTON1, BUTTON2, BUTTON3, BUTTON4), s

@autotest
def TapControl():
    tap = tap_control(bridge=b, id=2, lights=(7,9))
    tap.init()

    sensors = b.sensors()
    flag, flag_id = ((sensor,id) for id, sensor in sensors.sensors if sensor["name"] == "tap-2-flag").next()
    assert flag["type"] == "CLIPGenericFlag"
    assert flag["state"]["flag"] == False
    assert flag["name"] == "tap-2-flag"

    status, status_id = ((sensor,id) for id, sensor in sensors.sensors if sensor["name"] == "tap-2-status").next()
    assert status["type"] == "CLIPGenericStatus"
    assert status["state"]["status"] == 0
    assert status["name"] == "tap-2-status"

    rules = b.rules()
    on_rule = (rule for id, rule in rules.rules if rule["name"].startswith("tap-%s-on" % 2)).next()
    print on_rule
    assert on_rule["name"] == "tap-2-on"
    assert on_rule["actions"][0] == dict(address="/lights/7/state", method="PUT", body=dict(on=True))
    assert on_rule["actions"][1] == dict(address="/lights/9/state", method="PUT", body=dict(on=True))
    assert on_rule["actions"][2] == dict(address="/sensors/%s/state" % flag_id, method="PUT", body=dict(flag=True))
    assert on_rule["conditions"][0] == dict(address="/sensors/2/state/buttonevent", operator="eq", value="34")
    assert on_rule["conditions"][1] == dict(address="/sensors/2/state/lastupdated", operator="dx")
    assert on_rule["conditions"][2] == dict(address="/sensors/%s/state/flag" % flag_id, operator="eq", value="false")

    off_rule = (rule for id, rule in rules.rules if rule["name"].startswith("tap-%s-off" % 2)).next()
    assert off_rule["name"] == "tap-2-off"
    assert off_rule["actions"][0] == dict(address="/lights/7/state", method="PUT", body=dict(on=False))
    assert off_rule["actions"][1] == dict(address="/lights/9/state", method="PUT", body=dict(on=False))
    assert off_rule["actions"][2] == dict(address="/sensors/%s/state" % flag_id, method="PUT", body=dict(flag=False))
    assert off_rule["conditions"][0] == dict(address="/sensors/2/state/buttonevent", operator="eq", value="34")
    assert off_rule["conditions"][1] == dict(address="/sensors/2/state/lastupdated", operator="dx")
    assert off_rule["conditions"][2] == dict(address="/sensors/%s/state/flag" % flag_id, operator="eq", value="true")

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

