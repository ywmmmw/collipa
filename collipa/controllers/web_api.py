# coding: utf-8

import logging
import tornado.web
import tornado.escape

from ._base import BaseHandler
from pony import orm

from collipa.models import User
from collipa.extensions import rd


class GetUserNameHandler(BaseHandler):
    @orm.db_session
    def get(self):
        users = User.select()
        user_json = []
        for user in users:
            user_json.append({"value": user.name, "label": user.nickname})
        return self.write(user_json)


class MentionHandler(BaseHandler):
    @orm.db_session
    def get(self):
        word = self.get_argument('word', None)
        if not word:
            return self.write({
                'status': 'error',
                'message': '没有关键字'
            })
        user_list = User.mention(word)
        user_json = []
        for user in user_list:
            user_json.append({
                'id': user.id,
                'name': user.name,
                'nickname': user.nickname,
                'url': user.url,
                'avatar': user.get_avatar()
            })
        return self.write({
            'status': 'success',
            'user_list': user_json
        })
