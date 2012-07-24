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
            cache = cls.store.lrange('channel:cache:%s' % channel, 0, -1)
            index = 0
            for i in xrange(len(cache)):
                index = len(cache) - i - 1
                if tornado.escape.json_decode(cache[index])["id"] == cursor: break
            recent = cache[index + 1:]
            if recent:
                callback(recent)
                return
        #cls.channels[channel]['waiters'].add(callback)
        cls.channels[channel].setdefault('waiters', set()).add(callback)

    def cancel_wait(self, callback, channel):
        cls = ChannelMixin
        cls.channels[channel]['waiters'].remove(callback)

    def new_messages(self, messages):
        cls = ChannelMixin
        listeners = sum(map(lambda key: len(cls.channels[key]['waiters']), cls.channels.keys()))
        logging.info("Sending new message to %r listeners", listeners)
        for channel in messages.keys():
            for callback in cls.channels[channel]['waiters']:
                try:
                    callback(messages[channel])
                except:
                    logging.error("Error in waiter callback", exc_info=True)
        for channel in messages.keys():
            cls.channels[channel]['waiters'] = set()
            for msg in messages[channel]:
                cls.store.rpush('channel:cache:%s' % channel, tornado.escape.json_encode(msg))
            if cls.store.llen('channel:cache:%s' % channel) > cls.cache_size:
                cls.store.ltrim('channel:cache%s' % channel, -cls.cache_size, -1)

