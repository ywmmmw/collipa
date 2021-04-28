# coding: utf-8

import time
from pony import orm
from ._base import db, BaseModel
import collipa.models
from collipa.extensions import memcached, mc
from collipa import config
from collipa import helpers


class Album(db.Entity, BaseModel):
    name = orm.Required(str, 400)
    description = orm.Optional(str, 1000)
    user_id = orm.Required(int)
    image_count = orm.Required(int, default=0)

    role = orm.Required(str, 10, default='album')
    compute_count = orm.Required(int, default=config.reply_compute_count)

    thank_count = orm.Required(int, default=0)
    up_count = orm.Required(int, default=0)
    down_count = orm.Required(int, default=0)
    report_count = orm.Required(int, default=0)
    collect_count = orm.Required(int, default=0)

    floor = orm.Required(int, default=1)

    created_at = orm.Required(int, default=int(time.time()))
    updated_at = orm.Required(int, default=int(time.time()))
    active = orm.Required(int, default=int(time.time()))

    def to_simple_dict(self):
        data = {
            'id': self.id,
            'url': self.url,
            'name': self.name,
            'cover': self.cover,
            'description': self.description,
        }

        return data

    def to_dict(self):
        data = {
            'created': self.created,
            'author': self.author.to_simple_dict(),
        }
        data.update(self.to_simple_dict())

        return data

    def __str__(self):
        return self.id

    def __repr__(self):
        return '<Album: %s>' % self.id

    @property
    def cover_cache_key(self):
        return 'album.cover.%d' % self.id

    @property
    def url(self):
        return '/album/%s' % self.id

    def update_cover(self):
        mc.delete(self.cover_cache_key)
        return self.cover

    @property
    def cover_id(self):
        return mc.get(self.cover_cache_key)

    @property
    def cover(self):
        @memcached(self.cover_cache_key)
        def _cover_id():
            images = self.get_images(page=1, limit=1)
            cover_id = config.default_album_cover
            if images:
                cover_id = images[0].id
            return cover_id

        cover = _cover_id()
        # 某一夜，脑残用了 image.id 作为 album 的 cover
        if type(cover) in (int, int):
            image = collipa.models.Image.get(id=cover)
            if image:
                cover = image.path
            else:
                cover = config.default_album_cover
        size = (128, 128)
        return helpers.gen_thumb_url(cover, size)

    @cover.setter
    def cover(self, value):
        if isinstance(value, collipa.models.Image):
            value = value.path
        mc.set(self.cover_cache_key, value)

    def save(self, category='create'):
        now = int(time.time())
        if category == 'create':
            self.created_at = now
            self.author.album_count += 1

        self.updated_at = now
        self.author.active = now
        self.active = now

        return super(Album, self).save()

    def get_uppers(self, after_date=None, before_date=None):
        if after_date:
            user_ids = orm.select(rv.user_id for rv in collipa.models.Up if rv.album_id == self.id and rv.created_at > after_date)
        elif before_date:
            user_ids = orm.select(rv.user_id for rv in collipa.models.Up if rv.album_id == self.id and rv.created_at < before_date)
        else:
            user_ids = orm.select(rv.user_id for rv in collipa.models.Up if rv.album_id == self.id)
        users = []
        if user_ids:
            user_ids = user_ids.order_by(lambda: orm.desc(rv.created_at))

            users = orm.select(rv for rv in collipa.models.User if rv.id in user_ids)
        return users

    def get_thankers(self, after_date=None, before_date=None):
        if after_date:
            user_ids = orm.select(rv.user_id for rv in collipa.models.Thank if rv.album_id == self.id and rv.created_at > after_date)
        elif before_date:
            user_ids = orm.select(rv.user_id for rv in collipa.models.Thank if rv.album_id == self.id and rv.created_at < before_date)
        else:
            user_ids = orm.select(rv.user_id for rv in collipa.models.Thank if rv.album_id == self.id)
        users = []
        if user_ids:
            user_ids = user_ids.order_by(lambda: orm.desc(rv.created_at))

            users = orm.select(rv for rv in collipa.models.User if rv.id in user_ids)
        return users

    def get_images(self, page=1, category='all', order_by='created_at', limit=None, desc=True):
        if category == 'all':
            images = collipa.models.Image.select(lambda rv: rv.album_id == self.id)
        else:
            if category == 'hot':
                images = collipa.models.Image.select(lambda rv: rv.album_id == self.id)
                limit = 10
                order_by = 'smart'
            elif category == 'author':
                images = orm.select(rv for rv in collipa.models.Image if
                                    rv.topic_id == self.id and rv.user_id == self.user_id)
            else:
                images = orm.select(rv for rv in collipa.models.Image if rv.album_id == self.id and rv.role == category)

        if order_by == 'smart':
            images = images.order_by(lambda: orm.desc((rv.collect_count +
                                                          rv.thank_count) * 10 +
                                                         (rv.up_count -
                                                          rv.down_count) * 5))
        else:
            if desc:
                images = images.order_by(lambda: orm.desc(rv.created_at))
            else:
                images = images.order_by(lambda: rv.created_at)

        if limit:
            return images[:limit]
        elif page:
            return images[(page - 1) * config.paged: page * config.paged]
        else:
            return images
