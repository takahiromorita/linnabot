import json
import os
import sys
import requests
import pya3rt
import falcon
import time
import datetime
from logging import DEBUG, StreamHandler, getLogger


# logger
logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)


REPLY_ENDPOINT = 'https://api.line.me/v2/bot/message/reply'
A3RT_API_KEY = 'DZZDe9fEhdOO1qNJcEsS99brUOtUeS64'
a3rtclient = pya3rt.TalkClient(A3RT_API_KEY)
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', 'yh0SCsdQtIQR6+UTVPKZfZF/fF4Yna1wpBnjyyUbYCgcY9sqgQf27nNDF9RVlsllCChQ7ZGwTcKz2EN4Tkyt0KAkBHJ658xzmeFg4nreiPwtFrFIL19g4+ZDskA570n9gIVOH6fenXTnyFKPdvMy9gdB04t89/1O/w1cDnyilFU=')


class CallbackResource(object):
    # line
    header = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer {}'.format(LINE_CHANNEL_ACCESS_TOKEN)
    }

    def on_post(self, req, resp):

        body = req.stream.read()
        if not body:
            raise falcon.HTTPBadRequest('Empty request body','A valid JSON document is required.')

        receive_params = json.loads(body.decode('utf-8'))
        logger.debug('receive_params: {}'.format(receive_params))

        for event in receive_params['events']:
            logger.debug('event: {}'.format(event))
            if event['type'] == 'message':
                if not event['message']['text'].find('@') > -1:
                    try:
                        response = a3rtclient.talk(event['message']['text'].replace('\\',''))
                        #response = a3rtclient.talk(event['message']['text'])
                    except Exception:
                        logger.debug('A3RT API Error. Could not invoke A3RT api.')
                        #raise falcon.HTTPError(falcon.HTTP_503,'A3RT API Error. ','Could not invoke A3RT api.')
                    logger.debug(response['results'][0]['reply'])
                    sys_utt = response['results'][0]['reply']
                    logger.debug('A3RT_res: {}'.format(sys_utt))
                    send_content = {
                        'replyToken': event['replyToken'],
                        'messages': [
                            {
                                'type': 'text',
                                'text': sys_utt
                            }
                        ]
                    }
                    send_content = json.dumps(send_content)
                    logger.debug('send_content: {}'.format(send_content))
                    res = requests.post(REPLY_ENDPOINT, data=send_content, headers=self.header)
                    logger.debug('res: {} {}'.format(res.status_code, res.reason))
                    resp.body = json.dumps('OK')

api = falcon.API()
api.add_route('/callback', CallbackResource())
