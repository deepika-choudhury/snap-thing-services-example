from __future__ import print_function
import logging
import base64
import json

from Adafruit_IO import Client

import paho.mqtt.client as mqtt


# Set this to your Adafruit IO API Key
ADAFRUIT_IO_KEY = 'Add your key here'
LOG = logging.getLogger(__name__)

# Set this to point to your E20.
E20_HOSTNAME = 'localhost'

# Set this to your user credentials
STS_USER = 'snap'
STS_PASS = 'Synapse$0123'

# Set this to your interval data collector description
POLL_TOPIC = 'light_level'

# Set this to your event-based data collector description
EVENT_TOPIC = 'light_level_alarm'

aio = Client(ADAFRUIT_IO_KEY)


def create_client(host, port):
    client = mqtt.Client()
    client.username_pw_set(STS_USER, STS_PASS)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port, 60)
    return client


def on_connect(client, userdata, flags, rc):
    print("Connected to E20 with result code " + str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("dc/+/polled")
    client.subscribe("dc/+/+/data")


def send_adafruit_payload(data, topic, snap_addr):
    # Parse the string from the node
    light_level = int(base64.b64decode(data))

    # Build the Adafruit IO payload
    feed = '{id}-{topic}'.format(id=snap_addr, topic=topic)
    aio.send(feed, light_level)


def post_poll_to_adafruit(poll, topic):
    """Post mapped poll results to Adafruit."""
    for snap_addr, data in poll["successful"].iteritems():
        send_adafruit_payload(data, topic, snap_addr)


def on_message(client, userdata, msg):
    print("{topic} {payload}".format(topic=msg.topic, payload=str(msg.payload)))
    parsed_payload = json.loads(msg.payload.decode("utf-8"))
    if "dc/{topic}/".format(topic=POLL_TOPIC) in msg.topic:
        post_poll_to_adafruit(parsed_payload, POLL_TOPIC)
    elif "dc/{topic}/".format(topic=EVENT_TOPIC) in msg.topic:
        send_adafruit_payload(parsed_payload["data"], EVENT_TOPIC, parsed_payload["address"])


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    client = create_client(E20_HOSTNAME, 1883)

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    client.loop_forever()