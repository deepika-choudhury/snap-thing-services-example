from __future__ import print_function
import logging
from time import sleep

from Adafruit_IO import Client

from synapse_data_collector_client.simple_client import simple_data_collector_client


# Set this to your Adafruit IO API Key
ADAFRUIT_IO_KEY = 'Add your key here'
LOG = logging.getLogger(__name__)

# Set this to point to your E20.
E20_HOSTNAME = 'localhost'

# Set this to your user credentials
STS_USER = 'snap'
STS_PASS = 'Synapse$0123'

# Set this to your data collector description
TOPIC = 'light_level'

aio = Client(ADAFRUIT_IO_KEY)


def post_poll_to_adafruit(poll):
    """Post mapped poll results to Adafruit."""
    for snap_addr, data in poll['successful'].items():
        # Parse the string from the node
        light_level = int(data)

        # Build the Adafruit IO payload
        feed = '{id}-light_level'.format(id=snap_addr)
        aio.send(feed, light_level)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    client = simple_data_collector_client(
        poll_cb=post_poll_to_adafruit,
        metrics_cb=print,
        status_cb=print,
        topic=TOPIC,
        host=E20_HOSTNAME,
        mqtt_user=STS_USER,
        mqtt_pass=STS_PASS
    )
    print("Polling until CTRL-C is pressed")
    client.loop_forever()