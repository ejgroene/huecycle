from rest import post, delete, get

def get_rules(API):
    return get(LOCAL_HUE_API + "/rules")

def delete_rule(API, rule_id):
    delete("%(API)s/rules/%(rule_id)s" % locals())

def delete_all_rules(API):
    for rule in get_rules(API):
        print("Deleting rule %s..." % rule)
        delete_rule(API, rule)

def button_hit(tapid, button):
    return [dict(address="/sensors/%s/state/buttonevent" % tapid, operator="eq", value=str(button)),
            dict(address="/sensors/%s/state/lastupdated" % tapid, operator="dx")]

def sensor_eq(sensor, value):
    return [dict(address=sensor, operator="eq", value=value)]

def flag_eq(flagid, value):
    return sensor_eq("/sensors/%s/state/flag" % flagid, value)

def status_eq(statusid, value):
    return sensor_eq("/sensors/%s/state/status" % statusid, value)

def put_body(target, **body):
    return dict(address=target, method="PUT", body=body)

def put_light(lightid, **body):
    return put_body("/lights/%s/state" % lightid, **body)

def put_flag(flagid, **body):
    return put_body("/sensors/%s/state" % flagid, **body)

def create_rule(API, name, conditions, actions):
    return int(post(API + "/rules", name=name, conditions=conditions, actions=actions)["id"])

from misc import autotest
from config import LOCAL_HUE_API

@autotest
def DeleteAllRules():
    delete_all_rules(LOCAL_HUE_API)

@autotest
def InvalidRuleConditions():
    try:
        create_rule(LOCAL_HUE_API, "--test--", [], [put_body("/lights/1/state", v=1)])
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
    rule_id = create_rule(LOCAL_HUE_API, "--test--", button_hit(2, 1), [put_body("/lights/1/state", a=1)])
    assert 0 < rule_id < 100, rule_id
    assert str(rule_id) in get_rules(LOCAL_HUE_API)
    delete_rule(LOCAL_HUE_API, rule_id)
    assert str(rule_id) not in get_rules(LOCAL_HUE_API)
