#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import StringIO
import json
import logging
import random
import urllib
import urllib2
import re

# for sending images
from PIL import Image
import multipart

# standard app engine imports
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import webapp2

TOKEN = '112350249:AAFCcMtHwQ4Ft6VlJqjI8sOD3masB3CFauc'

BASE_URL = 'https://api.telegram.org/bot' + TOKEN + '/'


# ================================

class EnableStatus(ndb.Model):
    # key name: str(chat_id)
    enabled = ndb.BooleanProperty(indexed=False, default=False)


# ================================

def setEnabled(chat_id, yes):
    es = EnableStatus.get_or_insert(str(chat_id))
    es.enabled = yes
    es.put()

def getEnabled(chat_id):
    es = EnableStatus.get_by_id(str(chat_id))
    if es:
        return es.enabled
    return False


# ================================

class MeHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getMe'))))


class GetUpdatesHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getUpdates'))))


class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        url = self.request.get('url')
        if url:
            self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'setWebhook', urllib.urlencode({'url': url})))))


class WebhookHandler(webapp2.RequestHandler):

    def GetPodcastDescription(self, number):
        response = urllib2.urlopen('http://www.radio-t.com/archives/')
        html = response.read()
        ind = html.find("podcast-" + number + "/")
        if ind>0:
            podcastUrl = html[ind-14:ind+8 + len(number)]
            response = urllib2.urlopen("http://www.radio-t.com" + podcastUrl)
            html = response.read().split("<ul>")[1].split("</ul>")[0].decode('utf-8').replace("<li>","").replace("</li>","")
            return re.sub(r'<.*?>','', html)
        else:
            return ""

    def GetLatest(self):
        response = urllib2.urlopen('http://www.radio-t.com')
        html = response.read()
        ind = html.find("http://cdn.radio-t.com/rt_podcast")
        number = html[ind+33:ind+36]
        return self.GetPodcast("/get " + number)
    
    def GetPodcast(self, command):
        number = command.replace("/get","").strip()
        try:
            title = u"Радио-Т " + number
            url = u"Запись подкаста: \nhttp://cdn.radio-t.com/rt_podcast" + number + ".mp3"
            desc = self.GetPodcastDescription(str(number))
            if desc != "":
                return title + "\n" + desc +  "\n" + url
            else:
                return "Not found :("
        except Exception:
            return "Not found :("    

    def post(self):
        urlfetch.set_default_fetch_deadline(60)
        body = json.loads(self.request.body)
        logging.info('request body:')
        logging.info(body)
        self.response.write(json.dumps(body))

        update_id = body['update_id']
        message = body['message']
        message_id = message.get('message_id')
        date = message.get('date')
        text = message.get('text')
        fr = message.get('from')
        chat = message['chat']
        chat_id = chat['id']

        if not text:
            logging.info('no text')
            return

        def reply(msg=None, img=None):
            if msg:
                resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
                    'chat_id': str(chat_id),
                    'text': msg.encode('utf-8'),
                    'disable_web_page_preview': 'true',
                    'reply_to_message_id': str(message_id),
                })).read()
            elif img:
                resp = multipart.post_multipart(BASE_URL + 'sendPhoto', [
                    ('chat_id', str(chat_id)),
                    ('reply_to_message_id', str(message_id)),
                ], [
                    ('photo', 'image.jpg', img),
                ])
            else:
                logging.error('no msg or img specified')
                resp = None

            logging.info('send response:')
            logging.info(resp)

        if text.startswith('/'):
            help = u"Радио-Т - это еженедельный HiTech подкаст на русском языке. \n\n Авторы и приглашенные гости импровизируют на околокомпьютерные темы. Как правило, не залезая в глубокие дебри, однако иногда нас заносит ;) \n\n Вся необходимая информация: \n /help \n\n Для получения записей подкаста:\n /get {номер подкаста} \n\n Для получения последнего подкаста:\n /latest"
            if text == '/start':
                reply(help)
                setEnabled(chat_id, True)
            elif text == '/stop':
                setEnabled(chat_id, False)
            elif text == '/help':
                reply(help)
            elif 'get' in text:
                reply(self.GetPodcast(text))
            elif text == '/latest':
                reply(self.GetLatest())


app = webapp2.WSGIApplication([
    ('/me', MeHandler),
    ('/updates', GetUpdatesHandler),
    ('/set_webhook', SetWebhookHandler),
    ('/webhook', WebhookHandler),
], debug=True)
