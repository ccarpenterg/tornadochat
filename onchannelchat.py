#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging
import tornado.auth
import tornado.httpserver
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import os.path
import uuid, datetime, time

from models import *
from sqlalchemy.orm import scoped_session, sessionmaker

from mixins import ChannelMixin
from util import SuperDict

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
define("id", help="server id or name", type=str)

CACHE_SIZE = 200

db = scoped_session(sessionmaker(bind=engine))

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/auth/login", AuthLoginHandler),
            (r"/auth/logout", AuthLogoutHandler),
            (r"/chat/([0-9]+)", ChatHandler),
            (r"/create", ChannelNewHandler),
            (r"/join", JoinChannelHandler),
            (r"/a/message/new", MessageNewHandler),
            (r"/a/message/updates", MessageUpdatesHandler),
        ]
        settings = dict(
            cookie_secret="43oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            login_url="/auth/login",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            autoescape="xhtml_escape",
        )
        tornado.web.Application.__init__(self, handlers, **settings)

        self.db = db

class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db

    def get_current_user(self):
        user_json = self.get_secure_cookie("user")
        if not user_json: return None
        return tornado.escape.json_decode(user_json)

class MainHandler(BaseHandler, ChannelMixin):
    @tornado.web.authenticated
    def get(self):
        channel = Channel()
        self.db.add(channel)
        self.db.commit()
        self.set_channel(channel.id)
        self.redirect('/chat/%d' % channel.id)
        return

class ChatHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, channel):
        self.set_secure_cookie("channel", channel)
        self.render("index.html", messages=ChannelMixin.store.lrange('channel:cache:%s:pid:%s' % (channel, ChannelMixin.pid), 0, -1))

class ChannelNewHandler(BaseHandler, ChannelMixin):
    @tornado.web.authenticated
    def get(self):
        self.render("create_channel.html")

    @tornado.web.authenticated
    def post(self):
        name = self.get_argument("name")
        self.set_channel(name)
        self.set_secure_cookie("channel", name)
        channel = Channel()
        channel.name = name
        self.db.add(channel)
        self.db.commit()
        self.redirect("/")

class JoinChannelHandler(BaseHandler, ChannelMixin):
    @tornado.web.authenticated
    def get(self):
        self.render("join_channel.html", channels=ChannelMixin.channels.keys())

    @tornado.web.authenticated
    def post(self):
        self.clear_cookie("channel")
        channel = self.get_argument("channel")
        self.set_secure_cookie("channel", channel)
        self.redirect("/")

class MessageNewHandler(BaseHandler, ChannelMixin):
    @tornado.web.authenticated
    def post(self):
        message = {
            "id": str(uuid.uuid4()),
            "from": self.current_user["first_name"],
            "body": self.get_argument("body"),
        }
        message["html"] = self.render_string("message.html", message=message)
        if self.get_argument("next", None):
            self.redirect(self.get_argument("next"))
        else:
            channel = self.get_secure_cookie("channel")
            chat = Chat()
            chat.json = tornado.escape.json_encode(message)
            chat.timestamp = int(time.time()*10**6)
            chat.channel_id = int(channel)
            self.db.add(chat)
            self.db.commit()
            self.write(message)

class Updater(ChannelMixin):
    def __init__(self, start):
        self.start = start        

    @property
    def db(self):
        return db

    def poll(self):
        timestamp = self.timestamp or self.start
        query = self.db.query(Chat).filter(Chat.timestamp > timestamp).order_by(Chat.timestamp)
        messages = SuperDict([])
        for chat in query:
            messages[chat.channel_id].append(tornado.escape.json_decode(chat.json))
        if query.count() > 0: 
            self.timestamp = query[-1].timestamp
            self.new_messages(messages)
        tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(0.00001), self.poll)

class MessageUpdatesHandler(BaseHandler, ChannelMixin):
    @tornado.web.authenticated
    @tornado.web.asynchronous
    def post(self):
        channel = self.get_secure_cookie("channel")
        cursor = self.get_argument("cursor", None)
        self.wait_for_messages(self.on_new_messages,
                               int(channel),
                               cursor=cursor)

    def on_new_messages(self, messages):
        # Closed client connection
        if self.request.connection.stream.closed():
            return
        self.finish(dict(messages=messages))

    def on_connection_close(self):
        channel = self.get_secure_cookie("channel")
        self.cancel_wait(self.on_new_messages, int(channel))


class AuthLoginHandler(BaseHandler, tornado.auth.GoogleMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect(ax_attrs=["name"])

    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, "Google auth failed")
        self.set_secure_cookie("user", tornado.escape.json_encode(user))
        self.redirect(self.get_argument("next"))


class AuthLogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.write("You are now logged out")


def main():
    tornado.options.parse_command_line()
    ChannelMixin.pid = options.id
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    updater = Updater(int(time.time()*10**6))
    tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(0.00001), updater.poll)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
