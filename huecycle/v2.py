import requests
import requests_sse
import json
import urllib3
import time

# disable SSL not checked warning
requests.packages.urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)


resource = "https://ecb5fafffea7279d/clip/v2/resource" # ID must be in /etc/hosts
eventstream = "https://ecb5fafffea7279d/eventstream/clip/v2"
username = "IW4mOZWMTo1jrOqZEd66fbGoc7HWsiblPd8r2Qwt"
http_args = dict(verify=False, headers={'hue-application-key': username})


response = requests.get(resource, **http_args)
data = response.json()
error = data['errors']
assert not error, error
index = {obj['id']: obj for obj in data['data']}


class Observable:

    def __init__(self):
        self._observers = []

    def add_observer(self, observer):
        self._observers.append(observer)

    def tick(self):
        for o in self._observers:
            o.tick()

    def send(self, message):
        for o in self._observers:
            o.receive(message)

    def receive(self, message):
        type = message['type']
        getattr(self, type)(**message)


class Device(Observable):

    def __init__(self, data, key):
        self._data = data
        self._key = key
        super().__init__()

    def __repr__(self):
        return repr(self._key)

    def receive(self, message):
        type, id = self._data['type'], self._data['id']
        path = f"{resource}/{type}/{id}"
        print(self, message, '>>', path)
        response = requests.put(path, json=message, **http_args)
        assert response.status_code == requests.codes.ok, reponse.content


user = {}
for obj in index.values():
    id = obj['id']
    type = obj['type']
    owner = index.get(obj.get('owner',{}).get('rid'), {})
    match type:
        case 'light':
            key = obj['metadata']['name']
        case 'grouped_light':
            key = owner.get('metadata', {}).get('name', '')
        case 'button':
            name = owner['metadata']['name']
            key = name, obj['metadata']['control_id']
        case 'motion' | 'light_level' | 'temperature':
            name = owner['metadata']['name']
            key = name, type
        case _:
            continue

    assert key not in user, f"Duplicate key: {key} for object:\n{obj}\nExisting object: {user[key]._data}"
    print(key)
    user[key] = user[id] = Device(obj, key)


class Circadian(Observable):

    def tick(self):
        self.send({"identify": {"action": "identify"}})

    def button(self, **kwargs):
        print("CIRCADIAN BUTTON:", kwargs)


class Logger(Observable):

    def receive(self, message):
        print("LOGGER:", message)


def be(component, *observers):
    if isinstance(component, (str, tuple)):
        component = user[component]
    for c, *o in observers:
        c = be(c, *o)
        component.add_observer(c)
    return component


tree = be(Observable(),
    (("Kantoor knopje", 1),
        (Circadian(),
            ("Tolomeo",
                (Logger(),)),
            ("Bolt",),
        ),
    ),
    (("Sensor Kantoor", "light_level"),
        (Logger(),)
    )
  )

t0 = time.monotonic()

with requests_sse.EventSource(eventstream, **http_args) as messages:
    for message in messages:
        for data in json.loads(message.data):
            for event in data['data']:
                owner_id = event['id']
                if owner := user.get(owner_id):
                    owner.send(event)
                t1 = time.monotonic()
                if t1 > t0 + 1.0:
                    tree.tick()
                    t0 = time.monotonic()
    
