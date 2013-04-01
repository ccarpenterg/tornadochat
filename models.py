from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, create_engine, event, Enum
from sqlalchemy.orm import relationship, backref

import time

from secret import *
from util import get_timestamp

Base = declarative_base()

class Channel(Base):
    __tablename__ = 'channels'

    id = Column(Integer, primary_key=True)

class Chat(Base):
    __tablename__ = 'chats'

    id = Column(Integer, primary_key=True)
    json = Column(String(1024), nullable=False)
    timestamp = Column(BigInteger, nullable=False)
    channel_id = Column(Integer, ForeignKey('channels.id'))

    def toDict(self):
        chat = {
            'id': self.uuid,
            'html': self.html
            }
        return chat

engine = create_engine('postgresql://@localhost/chat')

Base.metadata.create_all(engine)

