import logging, redis
import tornado.escape
from util import SuperDict

class ChannelMixin(object):
    store = redis.Redis(host='localhost', port=6379, db=0)
    channels = SuperDict(dict())
    cache_size = 200
    timestamp = None

    def set_channel(self, channel):
        cls = ChannelMixin
        cls.channels[channel] = SuperDict(dict())
        cls.channels[channel]['waiters'] = set()

    def wait_for_messages(self, callback, channel, cursor=None):
        cls = ChannelMixin
        if cursor:
            cache = cls.store.lrange('channel:cache:%s:pid:%s' % (channel, cls.pid), 0, -1)
            index = 0
            for i in xrange(len(cache)):
                index = len(cache) - i - 1
                if tornado.escape.json_decode(cache[index])["id"] == cursor: break
            recent = cache[index + 1:]
            messages = []
            for chat in recent:
                messages.append(tornado.escape.json_decode(chat))
            if recent:
                callback(messages)
                return
        #cls.channels[channel]['waiters'].add(callback)
        cls.channels[channel].setdefault('waiters', set()).add(callback)

    def cancel_wait(self, callback, channel):
        cls = ChannelMixin
        cls.channels[channel]['waiters'].remove(callback)

    def new_messages(self, messages):
        cls = ChannelMixin
        incumbents = set(cls.channels.keys())
        channels = incumbents & set(messages.keys())
        listeners = sum(map(lambda key: len(cls.channels[key]['waiters']), cls.channels.keys()))
        logging.info("Sending new message to %r listeners", listeners)
        for channel in channels:
            logging.info("Sending %s new messages to channel %s", len(messages[channel]), channel)
            for callback in cls.channels[channel]['waiters']:
                try:
                    callback(messages[channel])
                except:
                    logging.error("Error in waiter callback", exc_info=True)
        for channel in channels:
            cls.channels[channel]['waiters'] = set()
        for channel in messages.keys():
            for chat in messages[channel]:
                cls.store.rpush('channel:cache:%s:pid:%s' % (channel, cls.pid), tornado.escape.json_encode(chat))

    def build_cache(self, messages):
        cls = ChannelMixin
        for channel in messages.keys():
            logging.info("Building cache for channel %s", channel)
            cls.store.delete('channel:cache:%s' % channel)
            for chat in messages[channel]:
                cls.store.rpush('channel:cache:%s' % channel, tornado.escape.json_encode(chat))

