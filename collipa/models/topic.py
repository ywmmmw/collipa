# coding: utf-8

import time
from pony import orm
from ._base import db, BaseModel
from collipa import config
import collipa.models


class Topic(db.Entity, BaseModel):
    user_id = orm.Required(int)
    node_id = orm.Required(int)

    title = orm.Required(str)
    content = orm.Required(orm.LongUnicode)

    hits = orm.Required(int, default=0)
    role = orm.Required(str, 10, default='topic')
    compute_count = orm.Required(int, default=config.topic_compute_count)

    reply_count = orm.Required(int, default=0)
    thank_count = orm.Required(int, default=0)
    up_count = orm.Required(int, default=0)
    down_count = orm.Required(int, default=0)
    report_count = orm.Required(int, default=0)
    collect_count = orm.Required(int, default=0)
    follow_count = orm.Required(int, default=0)

    created_at = orm.Required(int, default=int(time.time()))
    updated_at = orm.Required(int, default=int(time.time()))
    active = orm.Required(int, default=int(time.time()))

    last_reply_date = orm.Required(int, default=int(time.time()))

    topic_id = orm.Optional(int)

    def __str__(self):
        return self.title

    def __repr__(self):
        return '<Topic: %s>' % self.id

    @property
    def url(self):
        return '/topic/%s' % self.id

    @property
    def url_sharp(self):
        return '/topic/%s#reply%s' % (self.id, self.reply_count)

    @property
    def last_reply(self):
        reply = collipa.models.Reply.select(lambda rv: rv.topic_id == self.id).order_by(lambda:
                                                                           orm.desc(rv.created_at)).first()
        return reply

    @property
    def replies(self):
        replies = collipa.models.Reply.select(lambda rv: rv.topic_id == self.id).order_by(lambda:
                                                                             orm.desc(rv.created_at))
        return replies

    def get_replies(self, page=1, category='all', order_by='created_at', limit=None):
        if category == 'all':
            replies = collipa.models.Reply.select(lambda rv: rv.topic_id == self.id)
        else:
            if category == 'hot':
                replies = collipa.models.Reply.select(lambda rv: rv.topic_id == self.id)
                limit = 10
                order_by = 'smart'
            elif category == 'author':
                replies = orm.select(rv for rv in collipa.models.Reply if rv.topic_id == self.id and rv.user_id == self.user_id)
            else:
                replies = orm.select(rv for rv in collipa.models.Reply if rv.topic_id == self.id and rv.role == category)

        if order_by == 'smart':
            replies = replies.order_by(lambda: orm.desc((rv.collect_count +
                                                            rv.thank_count) * 10 +
                                                           (rv.up_count -
                                                            rv.down_count) * 5))
        else:
            replies = replies.order_by(lambda: rv.created_at)

        if limit:
            return replies[:limit]
        elif page:
            return replies[(page - 1) * config.reply_paged: page * config.reply_paged]
        else:
            return replies

    def compute_role(self):
        up_count = self.up_count
        down_count = self.down_count
        max_count = max(up_count, down_count)
        delta = abs(up_count - down_count)
        ratio = max_count / delta

        if ratio < 2 and max_count == down_count:
            self.role = 'down'
        else:
            self.role = 'up'
        if ratio > 6:
            self.role = 'dispute'
        if self.role == 'up' and self.reply_count > 20 and\
           self.reply_hits > 60:
            self.role = 'hot'

            if not collipa.models.Bill.get(user_id=self.author.id,
                              role='topic-hot',
                              topic_id=self.id):
                self.author.income(coin=config.topic_hot_coin,
                                   role='topic-hot',
                                   topic_id=self.id)
                bank = collipa.models.Bank.get_one()
                bank.spend(coin=config.topic_hot_coin,
                           role='topic-hot',
                           topic_id=self.id)
        if self.report_count > 12 and self.up_count < 5:
            self.role = 'report'

            if not collipa.models.Bill.get(user_id=self.author.id,
                              role='topic-report',
                              topic_id=self.id):
                self.author.spend(coin=config.topic_report_coin,
                                  role='topic-report',
                                  topic_id=self.id)
                bank = collipa.models.Bank.get_one()
                bank.income(coin=config.topic_report_coin,
                            role='topic-report',
                            topic_id=self.id)

        try:
            orm.commit()
        except:
            pass

    def save(self, category='create', user=None):
        bank = collipa.models.Bank.get_one()
        now = int(time.time())

        if category == 'create':
            self.created_at = now
            self.last_reply_date = now

            self.node.topic_count += 1
            self.author.topic_count += 1

            self.author.spend(coin=config.topic_create_coin,
                              role="topic-create",
                              topic_id=self.id)
            bank.income(coin=config.topic_create_coin,
                        role="topic-create",
                        topic_id=self.id,
                        spender_id=self.author.id)

        if category == 'edit' and not user:
            self.author.spend(coin=config.topic_edit_coin,
                              role='topic-edit',
                              topic_id=self.id)
            bank.income(coin=config.topic_edit_coin,
                        role='topic-edit',
                        topic_id=self.id,
                        spender_id=self.author.id)

        if not user:
            user = self.author

        self.updated_at = now
        self.active = now

        self.node.active = now
        user.active = now

        return super(Topic, self).save()

    def move(self, user=None, node=None):
        if not node:
            return self
        if self.node_id == node.id:
            return self

        old_node = collipa.models.Node.get(self.node_id)
        old_node.topic_count -= 1
        self.node_id = node.id
        node.topic_count += 1

        if not user:
            user = self.author

        now = int(time.time())
        user.active = now
        self.node.active = now

        try:
            orm.commit()
        except:
            pass

    def delete(self, user=None):
        self.node.topic_count -= 1
        self.author.topic_count -= 1
        for th in collipa.models.Thank.select(lambda rv: rv.topic_id == self.id):
            th.delete()
        for up in collipa.models.Up.select(lambda rv: rv.topic_id == self.id):
            up.delete()
        for dw in collipa.models.Down.select(lambda rv: rv.topic_id == self.id):
            dw.delete()
        for rp in collipa.models.Report.select(lambda rv: rv.topic_id == self.id):
            rp.delete()
        for img in collipa.models.Image.select(lambda rv: rv.topic_id == self.id):
            # 不能直接删除 img
            img.topic_id = 0
        for reply in self.replies:
            reply.delete()

        if not user:
            user = self.author
        user.active = int(time.time())

        super(Topic, self).delete()

    def get_uppers(self, after_date=None, before_date=None):
        if after_date:
            user_ids = orm.select(rv.user_id for rv in collipa.models.Up
                                  if rv.topic_id == self.id and rv.created_at > after_date)
        elif before_date:
            user_ids = orm.select(rv.user_id for rv in collipa.models.Up
                                  if rv.topic_id == self.id and rv.created_at < before_date)
        else:
            user_ids = orm.select(rv.user_id for rv in collipa.models.Up
                                  if rv.topic_id == self.id)
        users = []
        if user_ids:
            user_ids = user_ids.order_by(lambda: orm.desc(rv.created_at))

            users = orm.select(rv for rv in collipa.models.User
                               if rv.id in user_ids)
        return users

    def get_thankers(self, after_date=None, before_date=None):
        if after_date:
            user_ids = orm.select(rv.user_id for rv in collipa.models.Thank
                                  if rv.topic_id == self.id and rv.created_at > after_date)
        elif before_date:
            user_ids = orm.select(rv.user_id for rv in collipa.models.Thank
                                  if rv.topic_id == self.id and rv.created_at < before_date)
        else:
            user_ids = orm.select(rv.user_id for rv in collipa.models.Thank
                                  if rv.topic_id == self.id)
        users = []
        if user_ids:
            user_ids = user_ids.order_by(lambda: orm.desc(rv.created_at))

            users = orm.select(rv for rv in collipa.models.User
                               if rv.id in user_ids)
        return users

    def get_replyers(self, after_date=None, before_date=None):
        if after_date:
            user_ids = orm.select(rv.user_id for rv in collipa.models.Reply
                                  if rv.topic_id == self.id and
                                  rv.user_id != self.user_id and
                                  rv.created_at > after_date)
        elif before_date:
            user_ids = orm.select(rv.user_id for rv in collipa.models.Reply
                                  if rv.topic_id == self.id and
                                  rv.user_id != self.user_id and
                                  rv.created_at < before_date)
        else:
            user_ids = orm.select(rv.user_id for rv in collipa.models.Reply
                                  if rv.topic_id == self.id and
                                  rv.user_id != self.user_id)
        users = []
        if user_ids:
            user_ids = user_ids.order_by(lambda: orm.desc(rv.created_at))

            users = orm.select(rv for rv in collipa.models.User if rv.id in user_ids)
        return users

    @property
    def histories(self):
        histories = collipa.models.History.select(lambda rv: rv.topic_id == self.id).order_by(lambda:
                                                                                              orm.desc(rv.created_at))
        return histories

    def get_histories(self, page=1):
        histories = collipa.models.History.select(lambda rv: rv.topic_id == self.id).order_by(lambda:
                                                                                              orm.desc(rv.created_at))
        return histories[(page - 1) * config.paged: page * config.paged]

    @property
    def history_count(self):
        return orm.count(self.histories)

    def put_notifier(self):
        content, users = self.get_compiled_content_mention_users(self.content)
        self.content = content
        for user in users:
            if user.id != self.user_id:
                collipa.models.Notification(topic_id=self.id, receiver_id=user.id,
                                            role='mention').save()
        return self
