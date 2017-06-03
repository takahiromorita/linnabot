import json
import os
import sys
from logging import DEBUG, StreamHandler, getLogger

import requests

import doco.client
import falcon

import psycopg2
#import urlparse
import urllib
import time
import datetime

# logger
logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)

REPLY_ENDPOINT = 'https://api.line.me/v2/bot/message/reply'
DOCOMO_DL_ENDPOINT = 'https://api.apigw.smt.docomo.ne.jp/dialogue/v2/dialogue'
DOCOMO_REFRESH_TOKEN = 'https://api.smt.docomo.ne.jp/cgi12/token'
DOCOMO_QA_ENDPOINT = 'https://api.apigw.smt.docomo.ne.jp/knowledgeQA/v1/ask'
DOCOMO_API_KEY = os.environ.get('DOCOMO_API_KEY', '507146495762386f546830682e65707967736c744647394e436f4b5a63706650304e476649352e47613139')
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', 'yh0SCsdQtIQR6+UTVPKZfZF/fF4Yna1wpBnjyyUbYCgcY9sqgQf27nNDF9RVlsllCChQ7ZGwTcKz2EN4Tkyt0KAkBHJ658xzmeFg4nreiPwtFrFIL19g4+ZDskA570n9gIVOH6fenXTnyFKPdvMy9gdB04t89/1O/w1cDnyilFU=')


class CallbackResource(object):
    # line
    header = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer {}'.format(LINE_CHANNEL_ACCESS_TOKEN)
    }

    # docomo
    user = {'t':30}  # 20:kansai character
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
                    # time
                    ts = time.time()
                    timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # postgers
                    urllib.parse.uses_netloc.append("postgres")
                    url = urllib.parse.urlparse(os.environ["DATABASE_URL"])
                    conn = psycopg2.connect(
                        database=url.path[1:],
                        user=url.username,
                        password=url.password,
                        host=url.hostname,
                        port=url.port
                    )
                    
                    if event['message']['text'].find('教えて') > -1:
                        params={'q':event['message']['text'], 'APIKEY':DOCOMO_API_KEY}
                        r = requests.get(DOCOMO_QA_ENDPOINT, params=params)
                        docomo_res = json.loads(r.text)
                        sys_utt = docomo_res['answers'][0]['answerText']
                        logger.debug('test_aaaaa: {}'.format(sys_utt))
                        cur = conn.cursor()
                        cur.execute("SELECT * FROM contexttb ORDER BY id DESC LIMIT 1")
                        sys_context = cur.fetchone()[1]
                        cur = conn.cursor()
                        cur.execute("INSERT INTO contexttb (context, date) VALUES (%s, %s)",[sys_context,timestamp])
                        conn.commit()
                    else:
                        cur = conn.cursor()
                        cur.execute("SELECT * FROM contexttb ORDER BY id DESC LIMIT 1")
                        sys_context = cur.fetchone()[1]
                        #logger.debug('db_test: {}'.format(cur.fetchone()[1]))
                        #delta = timestamp - cur.fetchone()[2]
                        #logger.debug('delta: {}'.format(delta))
                        #user_utt = event['message']['text']
                        cur = conn.cursor()
                        cur.execute("SELECT * FROM tokentb ORDER BY id DESC LIMIT 1")
                        docomo_access_token = cur.fetchone()[1]
                        logger.debug('dialogue_test: {}'.format(docomo_access_token))
                        params={'APIKEY':DOCOMO_API_KEY}
                        header = {
                            'Content-Type': 'application/json; charset=UTF-8',
                            'Authorization': 'Bearer {}'.format(docomo_access_token)
                        }
                        content = {
                            'utt': event['message']['text'],
                            'context': '{}'.format(sys_context)
                        }
                        r = requests.post(DOCOMO_DL_ENDPOINT, params=params, data=json.dumps(content), headers=header)
                        logger.debug('dialogue_test: {}'.format(r.status_code))
                        if r.status_code == 403:
                            cur = conn.cursor()
                            cur.execute("SELECT * FROM tokentb ORDER BY id DESC LIMIT 1")
                            logger.debug('dialogue_test: {}'.format(cur.fetchone()[2]))
                            #params={'grant_type':'refresh_token','refresh_token':'oYDeGLZu71N5HbGkFGC8LdXqj7Z6txMXYJ8EyThgK9NZ'}
                            payload = "grant_type=refresh_token&refresh_token=oYDeGLZu71N5HbGkFGC8LdXqj7Z6txMXYJ8EyThgK9NZ"
                            logger.debug('dialogue_t')
                            header = {
                                'Content-Type': 'application/x-www-form-urlencoded',
                                'Authorization': 'Basic aG01WTJrcHcwYlkxRU1oWHBDTVhwZzNIYXd2VFhSUnlYUjV5ZjVlT1lvc1A6UVNGO19ibnxEWEMxMzJkSXpyIjQ='
                            }
                            #r = requests.post(DOCOMO_REFRESH_TOKEN, params=params, headers=header)
                            r = requests.post(DOCOMO_REFRESH_TOKEN, data=payload, headers=header)
                            logger.debug('dialogue_testttt: {}'.format(r.text))
                            docomo_res = json.loads(r.text)
                            accesstoken = docomo_res['access_token']
                            refreshtoken = docomo_res['refresh_token']
                            cur = conn.cursor()
                            cur.execute("INSERT INTO tokentb (accesstoken, refreshtoken) VALUES (%s, %s)",[accesstoken,refreshtoken])
                            header = {
                                'Content-Type': 'application/json; charset=UTF-8',
                                'Authorization': 'Bearer {}'.format(accesstoken)
                            }
                            content = {
                                'utt': event['message']['text'],
                                'context': ''
                            }
                            r = requests.post(DOCOMO_DL_ENDPOINT, params=params, data=json.dumps(content), headers=header)
                        docomo_res = json.loads(r.text)
                        #docomo_res = self.docomo_client.send(utt=user_utt, apiname='Dialogue', mode='dialog', context='{}'.format(cur.fetchone()[1]))
                        sys_context = docomo_res['context']
                        sys_utt = docomo_res['utt']
                        cur = conn.cursor()
                        cur.execute("INSERT INTO contexttb (context, date) VALUES (%s, %s)",[sys_context,timestamp])
                        conn.commit()
                    
                    cur.close()
                    conn.close()

                except Exception:
                    raise falcon.HTTPError(falcon.HTTP_503,
                                           'Docomo API Error. ',
                                           'Could not invoke docomo api.')

                logger.debug('docomo_res: {}'.format(docomo_res))
                #sys_utt = docomo_res['utt']

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
