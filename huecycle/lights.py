from prototype import object
from bridge import bridge



@bridge
def lights_controller(self):
    self.subpath = "/lights"
    def light(self, Id):
        @self
        def light_n(self):
            self.id = str(Id)
            def turn_on(self, on):
                self.send("/%s/state" % Id, on=on)
            def name(self):
                return self[Id].name
            def set_state(self, **kwargs):
                return self.send("/%s/state" % Id, **kwargs)
        return light_n
    def lights(self):
        self.update_state()
        for Id in (Id for Id in self.__dict__ if Id.isdigit()):
            yield self.light(Id)

@bridge
def groups_controller(self):
    self.subpath = "/groups"

from autotest import autotest
from config import LOCAL_HUE_API

@autotest
def GetAllLights():
    l = lights_controller(baseurl=LOCAL_HUE_API)
    l.update_state()
    assert l
    assert l[1].state.on in (True, False)
    l.light(1).turn_on(True)
    l.light(1).update_state()
    #assert l[1].state.on == True
    l.light(1).turn_on(False)
    l.light(1).update_state()
    #assert l[1].state.on == False

@autotest
def EnumerateLights():
    l = lights_controller(baseurl=LOCAL_HUE_API)
    for light in l.lights():
        print light.name()
    
   
@autotest
def Groups():
    g = groups_controller(baseurl=LOCAL_HUE_API)
    assert g
    g.update_state()
