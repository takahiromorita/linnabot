import json
import os
from logging import DEBUG, StreamHandler, getLogger

import requests

import doco.client
import falcon

import psycopg2
conn = psycopg2.connect("dbname=d60eumuvp125t8 host=ec2-174-129-227-116.compute-1.amazonaws.com user=rrzanzdfkiuvot password=888af4acd6219fe826b95173080870c57685f3fa912285b82dbd56d563d34fdb")
cur = conn.cursor()
cur.execute("INSERT INTO contextdb (context, date) VALUES ('aaa', '2017-05-10 00:00:00')")
cur.fetchone()
conn.commit()
cur.close()
conn.close()

# logger
logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)

REPLY_ENDPOINT = 'https://api.line.me/v2/bot/message/reply'
DOCOMO_API_KEY = os.environ.get('DOCOMO_API_KEY', '507146495762386f546830682e65707967736c744647394e436f4b5a63706650304e476649352e47613139')
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', 'yh0SCsdQtIQR6+UTVPKZfZF/fF4Yna1wpBnjyyUbYCgcY9sqgQf27nNDF9RVlsllCChQ7ZGwTcKz2EN4Tkyt0KAkBHJ658xzmeFg4nreiPwtFrFIL19g4+ZDskA570n9gIVOH6fenXTnyFKPdvMy9gdB04t89/1O/w1cDnyilFU=')


class CallbackResource(object):
    # line
    header = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer {}'.format(LINE_CHANNEL_ACCESS_TOKEN)
    }

    # docomo
    user = {'t': 20}  # 20:kansai character
    docomo_client = doco.client.Client(apikey=DOCOMO_API_KEY, user=user)

    def on_post(self, req, resp):

        body = req.stream.read()
        if not body:
            raise falcon.HTTPBadRequest('Empty request body',
                                        'A valid JSON document is required.')

        receive_params = json.loads(body.decode('utf-8'))
        logger.debug('receive_params: {}'.format(receive_params))

        for event in receive_params['events']:

            logger.debug('event: {}'.format(event))

            if event['type'] == 'message':
                try:
                    user_utt = event['message']['text']
                    docomo_res = self.docomo_client.send(
                        utt=user_utt, apiname='Dialogue')

                except Exception:
                    raise falcon.HTTPError(falcon.HTTP_503,
                                           'Docomo API Error. ',
                                           'Could not invoke docomo api.')

                logger.debug('docomo_res: {}'.format(docomo_res))
                sys_utt = docomo_res['utt']

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
