from prototype import object
from rest import get, put, post, delete
from extended_cct import extend_cct

@object
def bridge():

    def path(self):
        return ""

    def url(self):
        return self.baseurl + self.path()

    def read(self):
        return get(self.url())

    def send(self, subpath='', **kwargs):
        # ignore connection errors here? #TODO
        put(self.url() + subpath, **kwargs)

    def create_rule(self, name, conditions, actions):
        return int(post(self.baseurl + "/rules", name=name, conditions=conditions, actions=actions)["id"])

    def create_group(self, name, light_ids):
        return post(self.baseurl + "/groups", name=name, lights=[str(i) for i in light_ids])

    def delete_groups(self, name=''):
        for group in self.groups():
            if name.lower() in group.name.lower():
                print "Deleting group", group.name
                delete(group.url())

    def sensors(self):
        sensors = self(path=lambda self: self.up.path() + "/sensors")
        for id, attrs in sensors.read().iteritems():
            yield sensors(path=lambda self: self.up.path() + "/%s" % id, id=int(id), **attrs)

    def sensor(self, name):
        return (s for s in self.sensors() if name.lower() in s.name.lower()).next()

    def groups(self):
        grps = self(path=lambda self: self.up.path() + "/groups")
        for id, attrs in grps.read().iteritems():
            yield grps(id=id, path=lambda self: self.up.path() + "/%s" % self.id, **attrs)

    def rules(self):
        @self
        def rules():
            def path(self):
                return "/rules"
            return locals()
        for id, attrs in rules.read().iteritems():
            yield rules(id=int(id), **attrs)

    def lights(self, name=None):
        lights = self(path=lambda self: self.up.path() + "/lights")
        for id, attrs in lights.read().iteritems():
            if name and name.lower() not in attrs["name"].lower():
                continue
            def send(self, **kw):
                if self.type == "Dimmable light":
                    "ct" in kw and kw.pop("ct")
                if not kw: #TESTME
                    return
                kw = extend_cct(**kw)
                self.up.send("/state", **kw),
            light = lights(
                path=lambda self:
                    self.up.path() + "/%s" % self.id,
                send=send,
                id=int(id),
                **attrs
            )
            light.state = light(
                path=lambda self:
                    self.up.path() + "/state",
                **attrs["state"]
            )
            yield light

    def delete_all_scenes(self):
        scenes = self(path=lambda self: self.up.path() + "/scenes")
        for id in scenes.read().keys():
            print "Deleting scene:", id
            # scene cannot be deleted, they are GC'ed
            #delete(scenes.url() + "/%s" % id)

    return locals()

from autotest import autotest
from config import LOCAL_HUE_API

@autotest
def DeleteScenes():
    b = bridge(baseurl=LOCAL_HUE_API)
    b.delete_all_scenes()

@autotest
def ConnectBridge():
    b = bridge(baseurl=LOCAL_HUE_API)
    assert b
    data = b.read()
    assert data["config"]["name"] == "Nr19"

@autotest
def GetSensors():
    b = bridge(baseurl=LOCAL_HUE_API)
    sensor = (sensor for sensor in b.sensors() if sensor.name == "Daylight").next()
    assert sensor.name == "Daylight", sensor
    assert sensor.config.on == True

@autotest
def GetSensorByName():
    b = bridge(baseurl=LOCAL_HUE_API)
    tap = b.sensor("keuKe")
    assert tap.name == "Keuken"

@autotest
def GetRules():
    b = bridge(baseurl=LOCAL_HUE_API)
    b.create_rule("-a-test-rule-", [{"address":"/sensors/1/state/daylight","operator":"dx"}],
                [{"address":"/groups/0/action","method":"PUT","body":{"on": True}}])
    rule = (r for r in b.rules() if r.name == "-a-test-rule-").next()
    assert "-a-test-rule-" in rule.name, rule.name

@autotest
def GetLights():
    b = bridge(baseurl=LOCAL_HUE_API)
    lights = b.lights("stud")
    assert lights
    l1 = lights.next()
    assert l1.id == 1, l1.id
    assert l1.name == "Studeerkamer-buro (test)"
    assert l1.modelid == "LCT001"
    assert l1.path() == "/lights/%d" % l1.id, l1.path()

    state = l1.state()
    assert state.on in (True, False), state
    assert state.path() == "/lights/%d/state" % l1.id, state.path()
    state.send(on=False)
    assert b.lights().next().state().on == False
    state.send(on=True)
    assert b.lights().next().state().on == True
  
@autotest
def GetLightsByName():
    b = bridge(baseurl=LOCAL_HUE_API)
    lights = b.lights("keuke")
    names = [l.name for l in lights]
    assert names == ["Keuken-tafel", "Keuken-aanrecht"], names

@autotest
def ExtendedCCT():
    b = bridge(baseurl=LOCAL_HUE_API)
    light = b.lights("test").next()
    light.send(ct=10000)
    light = b.lights("test").next()
    assert light.state["hue"] == 46920, light.state["hue"]
    assert light.state["sat"] == 254, light.state["sat"]

    light.send(ct=1000)
    light = b.lights("test").next()
    assert light.state["hue"] == 0, light.state["hue"]
    assert light.state["sat"] == 254, light.state["sat"]

@autotest
def FindGroups():
    b = bridge(baseurl=LOCAL_HUE_API)
    b.delete_groups()
    groups = list(b.groups())
    assert groups == [], groups
    b.create_group("test-name", [1,3,5])
    group = (b.groups()).next()
    assert group.name == "test-name", group
    assert group.type == "LightGroup", group
    assert group.lights == ['1', '3', '5'], group

    
