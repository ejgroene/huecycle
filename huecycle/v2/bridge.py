import asyncio
import aiohttp
import time
import inspect

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


    async def request(self, *a, **kw): # intended for mocking
        async with aiohttp.ClientSession() as session:
            async with session.request(*a, **kw) as response:
                assert response.status == 200, f"{a} {kw}"
                return await response.json()
    

    async def http_get(self, method='get', api='/clip/v2', path='', **kw):
        path = f"{self.baseurl}{api}{path}"
        return await self.request(method, path, verify_ssl=False, headers=self.headers, **kw)


    http_put = partialmethod(http_get, method='put')


    async def read_objects(self):
        response = await self.http_get(path='/resource')
        for data in response['data']:
            resource = self(data['type'], **data) # clone/delegate to me
            self.index[resource.id] = resource
        return self.index


    def put(self, data):
        """ keep put synchronous as to keep using it simple; hence the task
            no one is interested in the response anyway, we could log errors though TODO
        """
        asyncio.create_task(self.http_put(path=f'/resource/{self.type}/{self.id}', json=data))


    async def eventstream(self):
        while True:
            try:
                response = await self.http_get(api="/eventstream/clip/v2", timeout=100)
            except asyncio.exceptions.TimeoutError as e:
                print(e)
                continue
            except aiohttp.client_exceptions.ClientConnectorError as e:
                print(e)
                time.sleep(1)
                continue
            for event in response:
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


    def handler(self, h):
        assert inspect.isfunction(h)
        self.event_handler = h


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
async def read_objects():
    async def request(self, method='', path='', headers=None, **kw):
        assert path == 'base9/clip/v2/resource', path
        assert method == 'get'
        assert headers == {'hue-application-key': 'pietje'}, headers
        assert kw == {'verify_ssl': False}, kw
        return {'data': [{'id': 'one', 'type': 'One'}]}
    b = bridge(baseurl='base9', username='pietje', request=request)
    objs = await b.read_objects()
    test.eq({'one': {'id': 'one', 'type': 'One'}}, objs)
    test.eq('One', objs['one'].type)


@test
async def write_object():
    async def request(self, method='', path='', headers=None, **kw):
        if method == 'put':
            assert path == 'b7/clip/v2/resource/OneType/oneId', path
            assert headers == {'hue-application-key': 'jo'}, headers
            assert kw == {'verify_ssl': False, 'json': {'add': 'this'}}, kw
            return {} 
        else:
            return {'data': [{'id': 'oneId', 'type': 'OneType'}]}
    b = bridge(baseurl='b7', username='jo', request=request)
    objs = await b.read_objects()
    b.index['oneId'].put({'add': 'this'})


@test
async def event_stream():
    async def request(self, method='', path='', headers=None, **kw):
        assert path == 'k9/eventstream/clip/v2', path
        assert method == 'get'
        assert headers == {'hue-application-key': 'K1'}, headers
        assert kw == {'verify_ssl': False, 'timeout': 100}, kw
        return [{
                'data': [
                    {'id': 'event1', 'type': 'happening'},
                    {'id': 'event2', 'type': 'party'},
                ]}, {
                'data': [
                    {'id': 'event3', 'type': 'closing'},
                ]},
            ]
    b = bridge(baseurl='k9', username='K1', request=request, filter_event=lambda s,e: e)
    events = b.eventstream()
    test.eq({'id': 'event1', 'type': 'happening'}, await anext(events))
    test.eq({'id': 'event2', 'type': 'party'}, await anext(events))
    test.eq({'id': 'event3', 'type': 'closing'}, await anext(events))

 
@test
async def handle_timeout():
    gooi = False
    calls = 0
    async def request(self, *_, **__):
        nonlocal gooi, calls
        calls += 1
        if gooi:
            gooi = False
            raise asyncio.exceptions.TimeoutError
        gooi = True
        return [{
                'data': [
                    {'id': 'event1', 'type': 'happening'},
                ]},
            ]
    b = bridge(baseurl='err', username='my', request=request, filter_event=lambda s,e: e)
    events = b.eventstream()
    test.eq({'id': 'event1', 'type': 'happening'}, await anext(events))
    test.eq({'id': 'event1', 'type': 'happening'}, await anext(events))
    test.eq(3, calls)


@test(slow_callback_duration=2)
async def wait_a_sec_on_connectionerror():
    gooi = False
    call_times = []
    async def request(self, *_, **__):
        nonlocal gooi
        call_times.append(time.monotonic())
        if gooi:
            gooi = False
            connection_key = prototype(ssl=None, host=None, port=None)
            raise aiohttp.client_exceptions.ClientConnectorError(connection_key, OSError(1))
        gooi = True
        return [{
                'data': [
                    {'id': 'event1', 'type': 'happening'},
                ]},
            ]
    b = bridge(baseurl='err', username='my', request=request, filter_event=lambda s,e: e)
    events = b.eventstream()
    test.eq({'id': 'event1', 'type': 'happening'}, await anext(events))
    test.eq({'id': 'event1', 'type': 'happening'}, await anext(events))
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

