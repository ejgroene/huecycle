import requests
import time
from functools import partialmethod
from prototype3 import prototype
import utils

import autotest
test = autotest.get_tester(__name__)


class bridge(prototype):

    index = {}
    apiv2 = property("{baseurl}/clip/v2".format_map)
    apiv1 = property("{baseurl}/api/{username}".format_map)
    headers = property(lambda self: {'hue-application-key': self.username})


    def request(self, *a, **kw): # intended for mocking
        return requests.request(*a, **kw)
    

    def http_get(self, method='get', api='/clip/v2', path='', **kw):
        path = f"{self.baseurl}{api}{path}"
        response = self.request(method, path, verify=False, headers=self.headers, **kw)
        assert response.status_code == 200, f"{method}:{path}, {response.text}"
        return response


    http_put = partialmethod(http_get, method='put')


    def read_objects(self):
        response = self.http_get(path='/resource')
        for data in response.json()['data']:
            resource = self(data['type'], **data) # clone/delegate to me
            self.index[resource.id] = resource
        return self.index


    def put(self, data):
        return self.http_put(path=f'/resource/{self.type}/{self.id}', json=data)


    def eventstream(self):
        while True:
            try:
                response = self.http_get(api="/eventstream/clip/v2", timeout=100)
            except requests.exceptions.ReadTimeout as e:
                print(e)
                continue
            except requests.exceptions.ConnectionError as e:
                print(e)
                time.sleep(1)
                continue
            for event in response.json():
                for data in event['data']:
                    yield self.filter_event(data)


    def filter_event(self, event):
        update = event.get(event['type']) or \
                 {k:event[k] for k in event if k not in 'type owner id_v1'}
        return self.index[event['id']], prototype('update', **update)


    def byname(self):
        byname = {}
        for r in self.index.values():
            if qname := utils.get_qname(r, self.index):
                r['qname'] = qname
                if qname in byname:
                    print(test.diff2(byname[qname], r))
                    raise Exception("Duplicate name")
                byname[qname] = r
        return byname


@test
def init():
    b = bridge(baseurl="http://base.org", username='itsme')
    test.ne(b, bridge)
    test.eq("http://base.org", b.baseurl)
    test.eq("http://base.org/clip/v2", b.apiv2)
    test.eq("http://base.org/api/itsme", b.apiv1)
    test.eq({'hue-application-key': 'itsme'}, b.headers)
    test.eq('itsme', b.username)
    with test.raises(AttributeError):
        bridge.username
    with test.raises(AttributeError):
        bridge.baseurl
    with test.raises(AttributeError):
        bridge.apiv1
    with test.raises(AttributeError):
        bridge.apiv2
    with test.raises(AttributeError):
        bridge.headers


@test
def read_objects():
    def request(self, method='', path='', headers=None, **kw):
        assert path == 'base9/clip/v2/resource', path
        assert method == 'get'
        assert headers == {'hue-application-key': 'pietje'}, headers
        assert kw == {'verify': False}, kw
        return prototype('response', status_code=200,
            json=lambda self: {'data': [
                {'id': 'one', 'type': 'One'},
            ]})
    b = bridge(baseurl='base9', username='pietje', request=request)
    objs = b.read_objects()
    test.eq({'one': {'id': 'one', 'type': 'One'}}, objs)
    test.eq('One', objs['one'].type)


@test
def write_object():
    def request(self, method='', path='', headers=None, **kw):
        if method == 'put':
            assert path == 'b7/clip/v2/resource/OneType/oneId', path
            assert headers == {'hue-application-key': 'jo'}, headers
            assert kw == {'verify': False, 'json': {'add': 'this'}}, kw
            return prototype('response', status_code=200)
        else:
            return prototype('response', status_code=200,
                json=lambda self: {'data': [
                    {'id': 'oneId', 'type': 'OneType'},
                ]})
    b = bridge(baseurl='b7', username='jo', request=request)
    objs = b.read_objects()
    b.index['oneId'].put({'add': 'this'})


@test
def event_stream():
    def request(self, method='', path='', headers=None, **kw):
        assert path == 'k9/eventstream/clip/v2', path
        assert method == 'get'
        assert headers == {'hue-application-key': 'K1'}, headers
        assert kw == {'verify': False, 'timeout': 100}, kw
        return prototype('response', status_code=200,
            json=lambda self: [{
                'data': [
                    {'id': 'event1', 'type': 'happening'},
                    {'id': 'event2', 'type': 'party'},
                ]}, {
                'data': [
                    {'id': 'event3', 'type': 'closing'},
                ]},
            ])
    b = bridge(baseurl='k9', username='K1', request=request, filter_event=lambda s,e: e)
    events = b.eventstream()
    test.eq({'id': 'event1', 'type': 'happening'}, next(events))
    test.eq({'id': 'event2', 'type': 'party'}, next(events))
    test.eq({'id': 'event3', 'type': 'closing'}, next(events))

 
@test
def handle_timeout():
    gooi = False
    calls = 0
    def request(self, *_, **__):
        nonlocal gooi, calls
        calls += 1
        if gooi:
            gooi = False
            raise requests.exceptions.ReadTimeout
        gooi = True
        return prototype('response', status_code=200,
            json=lambda self: [{
                'data': [
                    {'id': 'event1', 'type': 'happening'},
                ]},
            ])
    b = bridge(baseurl='err', username='my', request=request, filter_event=lambda s,e: e)
    events = b.eventstream()
    test.eq({'id': 'event1', 'type': 'happening'}, next(events))
    test.eq({'id': 'event1', 'type': 'happening'}, next(events))
    test.eq(3, calls)


@test
def wait_a_sec_on_connectionerror():
    gooi = False
    call_times = []
    def request(self, *_, **__):
        nonlocal gooi
        call_times.append(time.monotonic())
        if gooi:
            gooi = False
            raise requests.exceptions.ConnectionError
        gooi = True
        return prototype('response', status_code=200,
            json=lambda self: [{
                'data': [
                    {'id': 'event1', 'type': 'happening'},
                ]},
            ])
    b = bridge(baseurl='err', username='my', request=request, filter_event=lambda s,e: e)
    events = b.eventstream()
    test.eq({'id': 'event1', 'type': 'happening'}, next(events))
    test.eq({'id': 'event1', 'type': 'happening'}, next(events))
    test.eq(3, len(call_times))
    test.gt(call_times[2] - call_times[1], 0.9)

@test
def filter_event_data():
    b = bridge()
    b.index['1'] = {'id': '1', 'resource': 'A'}
    owner, update = b.filter_event(prototype(type='A', id='1', on=False))
    test.eq({'id': '1', 'resource': 'A'}, owner)
    test.eq(False, update.on)

@test
def byname():
    b = bridge()
    mies = {'id': '1', 'type': 'girl', 'metadata': {'name': 'mies'}}
    b.index['1'] = mies
    byname = b.byname()
    test.eq(mies, byname['girl:mies'])

