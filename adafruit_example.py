from __future__ import print_function
import logging
import base64
import json

import requests
from Adafruit_IO import Client
from Adafruit_IO import MQTTClient
import paho.mqtt.client as mqtt
from requests.auth import HTTPBasicAuth

# Set this to your Adafruit IO API Key
ADAFRUIT_IO_KEY = 'Add your key here'
ADAFRUIT_IO_USERNAME = 'Add your username here'
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
ACTUATION_DEVICE_ADDRESS = 'mac address of the device to actuate'  # set mac address of the node to actuate
ACTUATION_TOPIC = 'your actuation feed name in ADAFruit.io '

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

        return response

    def get_url(self, url):
        """Get method for a particular url."""
        r = requests.get(
            url, auth=HTTPBasicAuth(STS_USER, STS_PASS),
            verify=False)
        return r.content


def actuate_nodes():
    """Actuate nodes"""
    host = 'https://{0}'.format(E20_HOSTNAME)
    url = "/api/v1/actuation/requests"
    device_list = list()
    device_list.append(ACTUATION_DEVICE_ADDRESS)
    data = {
        "function": ACTUATION_FUNCTION,
        "devices": device_list,
        "parameters": [True]
    }

    a = Actuation(host=host, url=url, data=data)
    response_data = a.post()

    return response_data


def create_actuation_feed():
    """Create the feed for actuation"""
    feed_id = aio.send(ACTUATION_TOPIC, 0)
    return feed_id


def aio_connected(mclient):
    print ('Connected to Adafruit IO! Listening for {0} ...'.format(ACTUATION_TOPIC))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    mclient.subscribe(ACTUATION_TOPIC)


def aio_message(mclient, feed_id, payload):
    print ('Feed {0} received: {1}'.format(feed_id, payload))

    if feed_id == ACTUATION_TOPIC and payload == 'ON':
        data = actuate_nodes()
        d = data['data']['results'][0]['result']
        mclient.publish(ACTUATION_TOPIC, d)


def create_aio_mqtt_client():
    mclient = MQTTClient(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)
    # Setup the callback functions defined above.
    mclient.on_connect = aio_connected
    mclient.on_message = aio_message
    mclient.connect()

    return mclient


def create_client(host, port):
    eclient = mqtt.Client()
    eclient.username_pw_set(STS_USER, STS_PASS)
    eclient.on_connect = on_connect
    eclient.on_message = on_message
    eclient.connect(host, port, 60)
    return eclient


def on_connect(eclient, userdata, flags, rc):
    print("Connected to E20 with result code " + str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    eclient.subscribe("dc/+/polled")
    eclient.subscribe("dc/+/+/data")


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


def on_message(eclient, userdata, msg):
    print("{topic} {payload}".format(topic=msg.topic, payload=str(msg.payload)))
    parsed_payload = json.loads(msg.payload.decode("utf-8"))
    if "dc/{topic}/".format(topic=POLL_TOPIC) in msg.topic:
        post_poll_to_adafruit(parsed_payload, POLL_TOPIC)
    elif "dc/{topic}/".format(topic=EVENT_TOPIC) in msg.topic:
        send_adafruit_payload(parsed_payload["data"], EVENT_TOPIC, parsed_payload["address"])


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    # Actuate light using aio MQTTClient
    aio_mqtt_client = create_aio_mqtt_client()
    create_actuation_feed()
    aio_mqtt_client.loop_background()

    # DC using E20 HOST mqtt client
    e20_client = create_client(E20_HOSTNAME, 1883)

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.

    e20_client.loop_forever()