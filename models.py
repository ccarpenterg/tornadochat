from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, create_engine, event, Enum
from sqlalchemy.orm import relationship, backref

from secret import *

from util import hash

Base = declarative_base()

class Channel(Base):
    __tablename__ = 'channels'

    id = Column(Integer, primary_key=True)
    name = Column(String(32))
    hash_value = Column(String(32), nullable=True)

class Conversation(Base):
    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True)
    user = Column(String(64), nullable=True)
    chat = Column(String(1024), nullable=True)
    timestamp = Column(Integer, nullable=True)
    channel_id = Column(Integer, ForeignKey('channels.id'))

engine = create_engine('postgresql://' + USER + ':' + PASSWORD + '@localhost/slg')

Base.metadata.create_all(engine)

