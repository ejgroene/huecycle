import rest
import bridge
import pprint
import logging

logging.captureWarnings(True) # get rid of unverified https certificate
logging.basicConfig(level=logging.ERROR)

endpoint = rest.rest(baseurl='https://192.168.178.78')
b = bridge.bridge(endpoint, username="IW4mOZWMTo1jrOqZEd66fbGoc7HWsiblPd8r2Qwt")

burobuttonid = "2e8fe788-8f2d-48eb-8de2-30931635a062" # /sensors/48
burobutton_buttonserviceid = 'f25b7e3c-23f5-4dd2-a917-def75626dfb0'

burolampid = 'a894d1b6-2416-4eb7-9f3d-b1cb5163f6c1' # /lights/1
burolamp_lightserviceid = 'fc3fcd56-5485-4e23-809e-e1b8088581f5'


for device in b.devices():
    print()
    print("Device {name!r} ({archetype})".format(**(device.metadata)))
    print(f"  {device.product_data['product_name']!r}  {device.id}  ({device.id_v1})")
    for s in device.services:
        print(f"  {s['rtype']}:  {s['rid']}")

for rule in b.rules():
    print()
    print(f"Rule {rule.id} of {rule.owner}")
    print("  if")
    for c in rule.conditions:
        print("    {address} {operator} {value}".format(**{'value':''} | c))
    print("  then")
    for a in rule.actions:
        print("    {method} {body} on {address}".format(**a))


for event in b.eventstream():
    print()
    data = event['data'][0]
    pprint.pprint(data)
    #print(event['type'])
    #if data['id'] == burobutton_buttonserviceid:
    #    print(data['button']['last_event'])
    #if data['id'] == burolamp_lightserviceid:
    #    if 'on' in data:
    #        print(data['on'])
    #    if 'color_temperature' in data:
    #        print(data['color_temperature'])
    #    if 'dimming' in data:
    #        print(data['dimming'])
    #else:
    #    print(data['type'])
