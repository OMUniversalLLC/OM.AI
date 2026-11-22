#!/usr/bin/env python3
"""Optional Frigate MQTT -> secured local event collector adapter.

Install paho-mqtt and configure broker credentials for your own NVR.
Only after an 'end' track event is received will an object be counted.
Camera heartbeats are NOT inferred from absence/presence of car events.
"""
import os, json
from urllib.request import Request, urlopen
import paho.mqtt.client as mqtt

BROKER=os.environ['OM_MQTT_HOST']
LOCAL=os.getenv('OM_EDGE_URL','http://127.0.0.1:8766').rstrip('/')
TOKEN=os.environ['OM_EDGE_TOKEN']

def on_message(client,userdata,msg):
    try:
        payload=json.loads(msg.payload)
        data=json.dumps(payload).encode()
        req=Request(LOCAL+'/frigate',data=data,method='POST',headers={'Content-Type':'application/json','X-OM-EDGE-TOKEN':TOKEN})
        with urlopen(req,timeout=6) as res:res.read()
    except Exception as e:
        print('Failed to ingest Frigate event:', str(e)[:200],flush=True)

if __name__=='__main__':
    client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if os.getenv('OM_MQTT_USER'):
        client.username_pw_set(os.environ['OM_MQTT_USER'],os.environ['OM_MQTT_PASSWORD'])
    client.on_message=on_message
    client.connect(BROKER,int(os.getenv('OM_MQTT_PORT','1883')),60)
    client.subscribe('frigate/events',qos=1)
    client.loop_forever()
