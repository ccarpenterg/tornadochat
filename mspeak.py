import tornado.options
import tornado.template
import tornado.escape
import uuid
import time
import sys
from tornado.options import define, options

from models import *
from sqlalchemy.orm import scoped_session, sessionmaker

db = scoped_session(sessionmaker(bind=engine))

sys.path.append("/home/ccarpenterg/dev/tornadochat/templates/")
loader = tornado.template.Loader("/home/ccarpenterg/dev/tornadochat/templates/")

define("channel", default=1, help="the channel to broadcast", type=int)
define("nickname", default="Master", help="the nickname", type=str)
define("msg", type=str)

if __name__ == '__main__':

    tornado.options.parse_command_line()

    message = {
        "id": str(uuid.uuid4()),
        "from": options.nickname,
        "body": options.msg,
    }

    message['html'] = tornado.template.Template(
        '<div class="message" id="m{{ message["id"] }}"><b>{{ message["from"] }}: </b>{{ message["body"] }}</div>'
    ).generate(message=message)

    for i in range(8):
        message = {
            "id": str(uuid.uuid4()),
            "from": options.nickname,
            "body": options.msg + ' ' + str(i),
        }

        message['html'] = tornado.template.Template(
            '<div class="message" id="m{{ message["id"] }}"><b>{{ message["from"] }}: </b>{{ message["body"] }}</div>'
        ).generate(message=message)

        chat = Chat()
        chat.json = tornado.escape.json_encode(message)
        chat.timestamp = int(time.time()*10**6)
        chat.channel_id = options.channel
        db.add(chat)
        db.commit()
