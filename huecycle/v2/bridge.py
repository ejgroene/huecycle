from prototype import object
from extended_cct import extend_cct
from sseclient import SSEClient
import json

@object
class bridge:
    """ requires:
        - get method
        - username string
     """

    def read(self):
        return self.get()

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
                print("Deleting group", group.name)
                delete(group.url())

    def eventstream(self):
        for event in SSEClient(self.baseurl + f"/eventstream/clip/v2", verify=False,
                headers={'hue-application-key': 'IW4mOZWMTo1jrOqZEd66fbGoc7HWsiblPd8r2Qwt'}):
            if data := event.data:
                for message in json.loads(data):
                    yield message

    def devices(self):
        @self
        class device:
            path = f"/clip/v2/resource/device"
        response = device.read()
        assert not response['errors']
        for dev in response['data']:
            yield device(path=f"/clip/v2/resource/device/{dev['id']}", **dev)
        

    def sensors(self):
        @self
        class sensors:
            path = f"/api/{self.username}/sensors"
        for id, attrs in sensors.read().items():
            yield sensors(path=f"/api/{self.username}/sensors/{id}", id=int(id), **attrs)

    def sensor(self, name):
        return next((s for s in self.sensors() if name.lower() in s.name.lower()))

    def groups(self):
        grps = self(path=lambda self: self.up.path() + "/groups")
        for id, attrs in grps.read().items():
            yield grps(id=id, path=lambda self: self.up.path() + "/%s" % self.id, **attrs)

    def rules(self):
        @self
        class rules:
            path = f"/api/{self.username}/rules"
        for id, attrs in rules.read().items():
            yield rules(id=int(id), **attrs)

    def lights(self, name=None):
        lights = self(path=lambda self: self.up.path() + "/lights")
        for id, attrs in lights.read().items():
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
        for id in list(scenes.read().keys()):
            print("Deleting scene:", id)
            # scene cannot be deleted, they are GC'ed
            #delete(scenes.url() + "/%s" % id)



def live_bridge_tests(LOCAL_HUE_API):
    from autotest import autotest

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
        sensor = next((sensor for sensor in b.sensors() if sensor.name == "Daylight"))
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
        rule = next((r for r in b.rules() if r.name == "-a-test-rule-"))
        assert "-a-test-rule-" in rule.name, rule.name

    @autotest
    def GetLights():
        b = bridge(baseurl=LOCAL_HUE_API)
        lights = b.lights("stud")
        assert lights
        l1 = next(lights)
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
        light = next(b.lights("test"))
        light.send(ct=10000)
        light = next(b.lights("test"))
        assert light.state["hue"] == 46920, light.state["hue"]
        assert light.state["sat"] == 254, light.state["sat"]

        light.send(ct=1000)
        light = next(b.lights("test"))
        assert light.state["hue"] == 0, light.state["hue"]
        assert light.state["sat"] == 254, light.state["sat"]

    @autotest
    def FindGroups():
        b = bridge(baseurl=LOCAL_HUE_API)
        b.delete_groups()
        groups = list(b.groups())
        assert groups == [], groups
        b.create_group("test-name", [1,3,5])
        group = next((b.groups()))
        assert group.name == "test-name", group
        assert group.type == "LightGroup", group
        assert group.lights == ['1', '3', '5'], group

        
