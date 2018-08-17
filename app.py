# app.py

import os
import threading
import time
import boto3
import json
from flask import Flask
from urllib3.exceptions import ProtocolError
from TwitterAPI import TwitterAPI, TwitterConnectionError, TwitterRequestError

# aws credentials
aws_access_key_id = os.environ['aws_access_key_id']
aws_secret_access_key = os.environ['aws_secret_access_key']
region_name = os.environ['aws_region_name']

# twitter credentials
consumer_key = os.environ['twitter_consumer_key']
consumer_secret = os.environ['twitter_consumer_secret']
access_token_key = os.environ['twitter_access_token']
access_token_secret = os.environ['twitter_access_token_secret']

kinesis = boto3.client('kinesis',
                       aws_access_key_id=aws_access_key_id,
                       aws_secret_access_key=aws_secret_access_key,
                       region_name=region_name
                       )

twitter = TwitterAPI(consumer_key, consumer_secret,
                     access_token_key, access_token_secret)

usersToFollow = [822215679726100480, 25073877]  # realdonaldtrump, potus


class Twitter2Kinesis(threading.Thread):
    def __init__(self, name='Twitter2Kinesis'):
        """ constructor, setting initial variables """
        self._stopevent = threading.Event()
        self._sleepperiod = 1.0
        threading.Thread.__init__(self, name=name)
        self.daemon = True  # Daemonize thread

    def run(self):
        """ main control loop """

        while not self._stopevent.isSet():
            print("%s starts" % (self.getName(),))
            try:
                stream = twitter.request('statuses/filter',
                                         {'track': '#trump', 'follow': usersToFollow})
                for item in stream:
                    # stop proccesing when stopevent is set
                    if self._stopevent.isSet():
                        break
                    if 'text' in item:

                        # # filter out responses
                        # if tweet['user']['id'] == usersToFollow[0] or tweet['user']['id'] == usersToFollow[1]:
                        #     print(tweet['user']['id'])
                        #     kinesis.put_record(StreamName="twitter",
                        #                        Data=json.dumps(tweet), PartitionKey="filler")

                        # put tweets on kinesis stream
                        kinesis.put_record(StreamName="twitter",
                                           Data=json.dumps(item), PartitionKey="filler")

                        print('tweet from: ' + item['user']['screen_name'],)
                        self._stopevent.wait(self._sleepperiod)
                    elif 'disconnect' in item:
                        event = item['disconnect']
                        if event['code'] in [2, 5, 6, 7]:
                            # something needs to be fixed before re-connecting
                            raise Exception(event['reason'])
                        else:
                            # temporary interruption, retry request
                            break
            except TwitterRequestError as e:
                if e.status_code < 500:
                    # something needs to be fixed before re-connecting
                    raise
                else:
                    # temporary interruption, retry request
                    pass
            except TwitterConnectionError:
                # temporary interruption, retry request
                pass

        print("%s ends" % (self.getName(),))

    def join(self, timeout=None):
        """ Stop the thread and wait for it to end. """
        self._stopevent.set()
        threading.Thread.join(self, timeout)


t2k = Twitter2Kinesis()

app = Flask(__name__)


@app.route('/')
def index():
    if t2k.is_alive():
        return "Yo, it's working!"
    else:
        return str('nope, not working!')


# @app.route('/start')
# def start():
#     global t2k
#     if not t2k.is_alive():
#         t2k = Twitter2Kinesis()
#         t2k.start()
#     return str('running: ' + str(t2k.is_alive()))


# @app.route('/stop')
# def stop():
#     if t2k.is_alive():
#         t2k.join()
#     return str('running: ' + str(t2k.is_alive()))


if __name__ == "__main__":
    t2k.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
