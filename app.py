# app.py

import os
import threading
import re
import time
import boto3
import json
from flask import Flask
from TwitterAPI import TwitterAPI, TwitterConnectionError, TwitterRequestError
from dateutil.parser import parse

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

# variables that are accessible from anywhere
latestTweet = {}
# lock to control access to variable
dataLock = threading.Lock()


urlfinder = re.compile(
    r"((https?):((//)|(\\\\))+[\w\d:#@%/;$()~_?\+-=\\\.&]*)", re.MULTILINE | re.UNICODE)


def urlify2(value):
    return urlfinder.sub(r'<a href="\1">\1</a>', value)


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

                        global latestTweet
                        with dataLock:
                            latestTweet = item

                        # filter out responses to tweets from trump
                        kinesis.put_record(StreamName="twitter",
                                           Data=json.dumps(item), PartitionKey="filler")

                        print('tweet from: ' + item['user']['screen_name'],)

                        # # put tweets on kinesis stream
                        # kinesis.put_record(StreamName="twitter",
                        #                    Data=json.dumps(item), PartitionKey="filler")

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
        msg = "<html><body><p>Yo, it's working!<br><br>Latest Tweet from " + latestTweet['user']['screen_name'] + " - " + parse(
            latestTweet['created_at']).strftime("%B %d, %Y – %H:%M %z") + "<br><br>" + urlify2(json.dumps(latestTweet, indent=2)) + "</p></body></html>"
        msg = msg.replace('\n', '<br />')
        return msg
    else:
        return str('nope, not working!')


@app.route('/start')
def start():
    global t2k
    if not t2k.is_alive():
        t2k = Twitter2Kinesis()
        t2k.start()
    return str('<html><body>running: ' + str(t2k.is_alive()) + '</body></html>')


# @app.route('/stop')
# def stop():
#     if t2k.is_alive():
#         t2k.join()
#     return str('running: ' + str(t2k.is_alive()))


if __name__ == "__main__":
    t2k.start()
    app.run(host='0.0.0.0')
