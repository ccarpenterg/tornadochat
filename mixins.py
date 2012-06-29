import logging
from hashlib import md5

def create_hash(value):
    m = md5()
    m.update(value)
    return m.hexdigest()

class MessageMixin(object):
    waiters = set()
    cache = []
    cache_size = 200

    def wait_for_messages(self, callback, cursor=None):
        cls = MessageMixin
        if cursor:
            index = 0
            for i in xrange(len(cls.cache)):
                index = len(cls.cache) - i - 1
                if cls.cache[index]["id"] == cursor: break
            recent = cls.cache[index + 1:]
            if recent:
                callback(recent)
                return
        cls.waiters.add(callback)

    def cancel_wait(self, callback):
        cls = MessageMixin
        cls.waiters.remove(callback)

    def new_messages(self, messages):
        cls = MessageMixin
        logging.info("Sending new message to %r listeners", len(cls.waiters))
        for callback in cls.waiters:
            try:
                callback(messages)
            except:
                logging.error("Error in waiter callback", exc_info=True)
        cls.waiters = set()
        cls.cache.extend(messages)
        if len(cls.cache) > self.cache_size:
            cls.cache = cls.cache[-self.cache_size:]

class ChannelMixin(object):
    channels = dict()
    cache_size = 200

    def create_channel(self, name):
        cls = ChannelMixin
        channel = create_hash(name)
        cls.channels[channel] = dict()
        cls.channels[channel]['name'] = name
        cls.channels[channel]['waiters'] = set()
        cls.channels[channel]['cache'] = []
        cls.channels[channel]['cache_size'] = 200
        return channel

    def wait_for_messages(self, callback, channel, cursor=None):
        cls = ChannelMixin
        if cursor:
            index = 0
            for i in xrange(len(cls.channels[channel]['cache'])):
                index = len(cls.channels[channel]['cache']) - i - 1
                if cls.channels[channel]['cache'][index]["id"] == cursor: break
            recent = cls.channels[channel]['cache'][index + 1:]
            if recent:
                callback(recent)
                return
        cls.channels[channel]['waiters'].add(callback)

    def cancel_wait(self, callback, channel):
        cls = ChannelMixin
        cls.channels[channel]['waiters'].remove(callback)

    def new_messages(self, channel, messages):
        cls = ChannelMixin
        logging.info("Sending new message to %r listeners", len(cls.waiters))
        for callback in cls.channels[channel]['waiters']:
            try:
                callback(messages)
            except:
                logging.error("Error in waiter callback", exc_info=True)
        cls.channels[channel]['waiters'] = set()
        cls.channels[channel]['cache'].extend(messages)
        if len(cls.channels[channel]['cache']) > self.cache_size:
            cls.channels[channel]['cache'] = cls.channels[channel]['cache'][-self.cache_size:]

