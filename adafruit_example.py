from __future__ import print_function
import logging
import base64
import json

import requests
import time
from Adafruit_IO import Client

import paho.mqtt.client as mqtt


# Set this to your Adafruit IO API Key
from requests.auth import HTTPBasicAuth

ADAFRUIT_IO_KEY = #'Add your key here'
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

# Set node address to be actuateD and the function name that is going to be called on the node
ACTUATION_FUNCTION = 'turn_on_light10s'  # SPY function name
DEVICE_ADDRESS = 'mac address of the device'  # set mac address of the node to actuate
ACTUATION_IO_ACTUATION_FEED= 'your actuation feed name in ADAFruit.io '

aio = Client(ADAFRUIT_IO_KEY)


class Actuation(object):
    """Source Code to do get/post to the api and test."""

    def __init__(
            self, host="http://localhost:3000", url=None, data=None, *args, **kwargs):
        """Constructor method to initialize instance for testing.

        :param host: host server where the service is running, default is localhost:3000
        :param data: json data related to device and actuation method.
        :param url: api path to actuate
        """
        self.url = host + url
        self.data = data

    def get(self, *args, **kwargs):
        """Method to do a get to the url and benchmark the time taken.

        :returns timedelta: time difference of get method execution.
        """
        requests.get(
            self.url, verify=False, auth=HTTPBasicAuth(STS_USER, STS_PASS))

    def post(self, *args, **kwargs):
        """Method to do a post to the url

        :returns response: return the content in json format
        """
        r = requests.post(
            self.url, auth=HTTPBasicAuth(STS_USER, STS_PASS),
            data=json.dumps(self.data), verify=False
        )
        task_url = r.headers['Location']

        # Keep doing get until we get the result in response
        while 'results' not in self.get_url(task_url):
            pass
        else:
            response = json.loads(self.get_url(task_url))

        send_adafruit_actuation_payload(response)

    def get_url(self, url):
        """Get method for a particular url."""
        r = requests.get(
            url, auth=HTTPBasicAuth(STS_USER, STS_PASS),
            verify=False)
        return r.content


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


def send_adafruit_actuation_payload(data):
    # Parse the string from the node
    d = data['data']['results'][0]['result']

    # Build the Adafruit IO payload
    aio.send(ACTUATION_IO_ACTUATION_FEED, d)


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


def actuate_nodes():
    """Actuate nodes"""
    host = "https://%s" % E20_HOSTNAME
    url = "/api/v1/actuation/requests"
    device_list = list()
    device_list.append(DEVICE_ADDRESS)
    data = {
        "function": ACTUATION_FUNCTION,
        "devices": device_list,
        "parameters": [True]
    }
    a = Actuation(host=host, url=url, data=data)
    a.post()


def create_actuation_feed():
    """Create the feed in adafruit for actuation"""
    aio.send(ACTUATION_IO_ACTUATION_FEED, 0)


def call_actuation():
    """Call actuation when user toggles the button 'ON'"""
    while True:
        data = aio.receive(ACTUATION_IO_ACTUATION_FEED)
        if str(data.value) in ('success', 'failure'):
            continue
        elif str(data.value) == 'ON':
            actuate_nodes()
            time.sleep(10)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    client = create_client(E20_HOSTNAME, 1883)

    # Actuate node
    create_actuation_feed()
    call_actuation()

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.

    client.loop_forever()