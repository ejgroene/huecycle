from sensors import flag_sensor, status_sensor
from http import post, delete, get, put
from sunphase import MIREK

def get_rules(API):
    return get(LOCAL_HUE_API + "/rules")

def delete_rule(API, rule_id):
    delete("%(API)s/rules/%(rule_id)s" % locals())

def delete_all_rules(API):
    for rule in get_rules(API):
        print "Deleting rule %s..." % rule
        delete_rule(API, rule)

def button_hit(tap, button):
    return [dict(address="/sensors/%s/state/buttonevent" % tap, operator="eq", value=str(button)),
            dict(address="/sensors/%s/state/lastupdated" % tap, operator="dx")]

def flag_eq(sensor, value):
    return [dict(address=sensor+"/flag", operator="eq", value=value)]

def status_eq(sensor, value):
    return [dict(address=sensor+"/status", operator="eq", value=value)]

def put_body(target, **body):
    return [dict(address=target, method="PUT", body=body)]

def create_rule(API, name, conditions, actions):
    return int(post(API + "/rules", name=name, conditions=conditions, actions=actions)["id"])

def create_onoff_rule(API, name, tap_id, button, lights):
    flag = flag_sensor(name=name+"_STATE", baseurl=API)
    flag.init()
    toggle_state = flag.state().state_address()
    button_event = button_hit(tap_id, button)
    create_rule(API, name + "_ON", button_event + flag_eq(toggle_state, "false"),
                put_body(lights+"/state", on=True) + put_body(toggle_state, flag=True))
    create_rule(API, name + "_OFF", button_event + flag_eq(toggle_state, "true"),
                put_body(lights+"/state", on=False) + put_body(toggle_state, flag=False))
    return flag

def create_step_rule(API, name, tap_state, button, val_0, val_1, int_state, lights, **kwargs):
    create_rule(API, name, button_hit(tap_state, button) + status_eq(int_state, str(val_0)),
                put_body(lights+"/state", **kwargs) + put_body(int_state, status=val_1))

def create_4step_rule(API, name, tap_id, button_down, button_up, lights):
    status = status_sensor(name=name+"_STATE", baseurl=API)
    status.init()
    status.state().set(4)
    #state_id = create_sensor(API, name+"_STATE", "CLIPGenericStatus")
    #int_state = "/sensors/%s/state" % state_id
    #put(API + int_state, status=4)
    int_state = status.state().state_address()
    print int_state
    create_step_rule(API, name+"_UP1", tap_id, button_up, 4, 3, int_state, lights, bri=128, ct=MIREK/2700)
    create_step_rule(API, name+"_UP2", tap_id, button_up, 3, 2, int_state, lights, bri=196, ct=MIREK/3400)
    create_step_rule(API, name+"_UP3", tap_id, button_up, 2, 1, int_state, lights, bri=255, ct=MIREK/4100)
    create_step_rule(API, name+"_DOWN1", tap_id, button_down, 1, 2, int_state, lights, bri=196, ct=MIREK/3400)
    create_step_rule(API, name+"_DOWN2", tap_id, button_down, 2, 3, int_state, lights, bri=128, ct=MIREK/2700)
    create_step_rule(API, name+"_DOWN3", tap_id, button_down, 3, 4, int_state, lights, bri= 64, ct=MIREK/2000)
    return status.id
    
from misc import autotest
from config import LOCAL_HUE_API

@autotest
def InvalidRuleConditions():
    try:
        create_rule(LOCAL_HUE_API, "--test--", [], put_body("/lights/1/state", v=1))
        assert False
    except Exception as e:
        assert str(e) == "invalid value, [], for parameter, conditions (/rules/conditions)", str(e)

@autotest
def InvalidRuleActions():
    try:
        create_rule(LOCAL_HUE_API, "--test--", button_hit(2,1), [])
        assert False
    except Exception as e:
        assert str(e) == "invalid value, [], for parameter, actions (/rules/actions)", str(e)

@autotest
def CreateAndDeleteRule():
    rule_id = create_rule(LOCAL_HUE_API, "--test--", button_hit(2, 1), put_body("/lights/1/state", a=1))
    assert 0 < rule_id < 100, rule_id
    assert str(rule_id) in get_rules(LOCAL_HUE_API)
    delete_rule(LOCAL_HUE_API, rule_id)
    assert str(rule_id) not in get_rules(LOCAL_HUE_API)
