import asyncio
import aiohttp
import time
import inspect
import asyncio

from functools import partialmethod
from prototype3 import prototype
import utils

import logging
logging.captureWarnings(True) # get rid of unverified https certificate
logging.basicConfig(level=logging.ERROR)

import autotest
test = autotest.get_tester(__name__)


class bridge(prototype):

    apiv2 = property("{baseurl}/clip/v2".format_map)
    apiv1 = property("{baseurl}/api/{username}".format_map)
    headers = property(lambda self: {'hue-application-key': self.username})


    async def request(self, *a, **kw): # intended for mocking
        async with aiohttp.ClientSession() as session:
            async with session.request(*a, **kw) as response:
                assert response.status == 200, (f"{a} {kw}", await response.text())
                return await response.json()
    

    async def http_get(self, method='get', api='/clip/v2', path='', **kw):
        path = f"{self.baseurl}{api}{path}"
        return await self.request(method, path, verify_ssl=False, headers=self.headers, **kw)


    http_put = partialmethod(http_get, method='put')


    def read_objects(self):
        self.index = index = {}
        self._byname = byname = {}
        async def task():
            response = await self.http_get(path='/resource')
            for data in response['data']:
                resource = self(data['type'], **data) # clone/delegate to me
                index[resource.id] = resource
            for resource in index.values():
                if qname := utils.get_qname(resource, index):
                    resource['qname'] = qname
                    if resource['type'] == 'grouped_light':
                        mirek_min, mirek_max = utils.find_color_temperature_limits(resource, index)
                        resource.color_temperature = { 'mirek_schema':
                                             {'mirek_minimum': mirek_min, 'mirek_maximum': mirek_max}}
                    if qname in byname:
                        print(test.diff2(byname[qname], resource))
                        raise Exception(f"Duplicate name {qname!r}")
                    byname[qname] = resource
            return index
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(task())
        else:
            return asyncio.create_task(task())
    

    def byname(self, name):
        return self._byname.get(name)
        

    def put(self, data, tail=''):
        """ keep put synchronous as to keep using it simple; hence the task
            no one is interested in the response anyway, we could log errors though TODO
        """
        asyncio.create_task(self.http_put(path=f'/resource/{self.type}/{self.id}{tail}', json=data))


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
        # TODO new devices could be absent
        return self.index[event['id']], prototype('update', **update)


    def handler(self, h):
        assert inspect.isfunction(h)
        self.event_handler = h


    async def dispatch_events(self):
        async for service, update in self.eventstream():
            if service:
                print(f"{service.qname!r}: {dict(update)}")
            else:
                print(f"<unknown>: {dict(update)}")
                continue
        
            if service.event_handler:
                service.event_handler(update)
                continue
            """ update internal state to reflect changes """
            old = service.keys()
            service.update(update)
            diff = old ^ service.keys()
            assert diff <= {'temperature_valid'}, diff



@test
def init():
    b = bridge(baseurl="http://base.org", username='itsme')
    test.ne(b, bridge)
    test.eq("http://base.org", b.baseurl)
    test.eq("http://base.org/clip/v2", b.apiv2)
    test.eq("http://base.org/api/itsme", b.apiv1)
    test.eq({'hue-application-key': 'itsme'}, b.headers)
    test.eq('itsme', b.username)
    test.eq(None, bridge.username)
    test.eq(None, bridge.baseurl)
    test.eq("None/api/None", bridge.apiv1)
    test.eq("None/clip/v2", bridge.apiv2)
    test.eq({'hue-application-key': None}, bridge.headers)


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
    test.eq({'one': {'id': 'one', 'type': 'One', 'qname': 'One:None'}}, objs)
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
    b.index = {'1': {'id': '1', 'resource': 'A'}}
    owner, update = b.filter_event(prototype(type='A', id='1', on=False))
    test.eq({'id': '1', 'resource': 'A'}, owner)
    test.eq(False, update.on)


@test
def byname():
    b = bridge()
    mies = {'id': '1', 'type': 'girl', 'metadata': {'name': 'mies'}}
    b._byname = {'firl:miep': mies}
    test.eq(mies, b.byname('firl:miep'))

