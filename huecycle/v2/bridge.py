
import requests
import urllib3
import asyncio
import logging
import json

import aiohttp

from devices import Device
from observable import Observable, be
from utils import logexceptions

# disable SSL not checked warning
requests.packages.urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)

class Bridge:

    def __init__(self, baseurl, username):
        self._baseurl = baseurl
        self._resource = self._baseurl + "clip/v2/resource"
        self.appkey = {'hue-application-key': username}
        self.index = self.create_index()
        self.configured = {}


    def create_index(self):
        """ create an index of selected json blobs by id or by key """
        all_json_blobs = self.get()['data']
        blob_by_id = {obj['id']: obj for obj in all_json_blobs}
        index = {}
        for obj in blob_by_id.values():
            id = obj['id']
            type = obj['type']
            owner = blob_by_id.get(obj.get('owner',{}).get('rid'), {})
            match type:
                case 'light':
                    key = obj['metadata']['name'],
                case 'grouped_light':
                    key = owner.get('metadata', {}).get('name', ''),
                case 'button':
                    name = owner['metadata']['name']
                    key = name, obj['metadata']['control_id']
                case 'motion' | 'light_level' | 'temperature':
                    name = owner['metadata']['name']
                    key = name, type
                case 'scene':
                    group = blob_by_id[obj['group']['rid']]
                    parentname = group['metadata']['name']
                    name = obj['metadata']['name']
                    key = parentname, name
                case _:
                    continue

            assert key not in index, f"Duplicate key: {key} for object:\n{obj}\nExisting object: {index[key]._data}"
            logging.info(f"{type}: {key!r}")
            index[key] = index[id] = obj
        return index


    def get(self):
        """ retrieve all devices of the bridge """
        response = requests.get(self._resource, verify=False, headers=self.appkey)
        assert response.status_code == requests.codes.ok, response.content
        return response.json()


    def put(self, path, message):
        """ put messages for devices on the queue for sending """
        self.queue.put_nowait((path, message))


    def device(self, *key, **kwargs):
        """ creates device objects for use in configurations (dna) """
        if device := self.configured.get(key):
            return device
        device = Device(self.index[key], key, self.put)
        self.configured[key] = self.configured[device._data['id']] = device
        return device


    def configure(self, *dna):
        """ register all observers and return event loop to be ran by app """
        self.tree, seen = be(None, Observable(), *dna)

        def on_event(update, container):
            if owner := self.configured.get(update['id']):
                update = {k: v for k, v in update.items() if k not in ('id', 'id_v1', 'owner', 'service_id')}
                logging.info(f" *** {owner!r}  {update}")
                owner.send(update)

        return lambda: self.sse(on_event)


    async def putter(self):
        """ monitor send queue and forward messages to the bridge """
        with logexceptions():
            async with aiohttp.ClientSession(self._resource+'/', raise_for_status=True, headers=self.appkey) as session:
                while True:
                    with logexceptions():
                        path, message = await self.queue.get()
                        logging.info(f"{message} >>> {path}")
                        async with session.put(path, json=message, ssl=False) as response:
                            await response.json()
                        await asyncio.sleep(0)


    async def sse(self, callback):
        with logexceptions():
            """ main event loop; processes events from the bridge and dispatches them """
            self.queue = asyncio.Queue()
            self.tree.init_all()
            asyncio.create_task(self.putter())
            eventstream = self._baseurl + "/eventstream/clip/v2"
            http_args = dict(raise_for_status = True,
                             timeout = aiohttp.ClientTimeout(total=0, sock_read=0),
                             headers = dict(self.appkey, Accept = "text/event-stream"))
            async with aiohttp.ClientSession(**http_args) as session:
                while True:
                    with logexceptions():
                        logging.info("Connecting to SSE")
                        async with session.get(eventstream, ssl=False) as response:
                            assert response.headers.get('Content-Type') == 'text/event-stream; charset=utf-8', response.headers
                            async for line in response.content:
                                if line.startswith(b'data: '):
                                    container = json.loads(line[6:])
                                    for event in container:
                                        for update in event['data']:
                                            callback(update, {event[k] for k in event if k != 'data'})
                                            await asyncio.sleep(0)
       

