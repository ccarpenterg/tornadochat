import tornado.ioloop
import tornado.escape
import tornado.options
import logging
import redis
import datetime

from sqlalchemy.orm import scoped_session, sessionmaker
from models import *
from util import SuperDict

db = scoped_session(sessionmaker(bind=engine))
store = redis.Redis(host='localhost', port=6379, db=0)
CACHE_SIZE = 200

class Cache(object):
    @property
    def db(self):
        return db

    @property
    def store(self):
        return store

    def update(self):
        channels = self.db.query(Chat).distinct('channel_id')
        logging.info("Updating cache for %d channels", channels.count())
        messages = SuperDict([])
        for channel in channels:
            self.store.delete('channel:cache:%s' % channel)
            for chat in self.db.query(Chat).filter(Chat.channel_id == channel.channel_id).order_by(Chat.timestamp).limit(CACHE_SIZE):
                self.store.rpush('channel:cache:%s' % channel, chat.json)
        tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(0.00001), self.update)

def main():
    tornado.options.parse_command_line()
    cache = Cache()
    print 'starting...'
    tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(0.00001), cache.update)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
    
