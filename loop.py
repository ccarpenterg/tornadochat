import tornado.ioloop
import tornado.escape
import logging
import redis

from sqlalchemy.orm import scoped_session, sessionmaker
from models import *

db = scoped_session(sessionmaker(bind=engine))
store = redis.Redis(host='localhost', port=6379, db=0)
CACHE_SIZE = 200

class Cache(object):
    def __init__(self, start):
        self.start = start

    @property
    def db(self):
        return db

    @property
    def store(self):
        return store

    def update(self):
        timestamp = self.timestamp or self.start
        channels = self.db.query(Chat).filter(Chat.timestamp > timestamp).distinct('channel_id')
        logging.info("Updating cache on %d for %d channels", timestamp, channels.count())
        messages = SuperDict([])
        for channel in channels:
            self.store.delete('channel:cache:%s' % channel)
            for chat in self.db.query(Chat).filter(Chat.channel_id == channel.channel_id).order_by(Chat.timestamp).limit(CACHE_SIZE):
                self.store.rpush('channel:cache:%s' % channel, tornado.escape.json_encode(chat))
        tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(0.00001), self.update)

if __name__ == '__main__':
    cache = Cache(int(time.time()*10**6))
    tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(0.00001), cache.update)
    tornado.ioloop.IOLoop.instance().start()
    
