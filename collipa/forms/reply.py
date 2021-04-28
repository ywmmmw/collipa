# coding: utf-8

from ._base import BaseForm
from collipa.libs.tforms import validators
from collipa.libs.tforms.fields import TextAreaField
from collipa.libs.tforms.validators import ValidationError
from collipa.helpers import strip_tags, strip_xss_tags
from collipa.libs import ghdiff

from collipa.models import Reply, History


class ReplyForm(BaseForm):
    content = TextAreaField(
        '内容', [
            validators.Required(),
            validators.Length(min=3, max=1000000),
        ],
    )

    def validate_content(self, field):
        """ 为了照顾一图流
        """
        if field.data.find('<img class="upload-reply-image"') == -1 and\
           field.data.find('<embed type="application') == -1:
            data = strip_tags(field.data)
            if len(data) < 3:
                raise ValidationError('内容至少 3 字符')

    @property
    def result(self):
        msg = '评论创建失败'
        for field in self:
            if field.errors:
                if field.name == 'content':
                    msg = '内容至少 3 字节'
        result = {'status': 'error', 'message': msg}
        return result

    def save(self, user, topic, reply=None):
        data = self.data
        content = str(data.get('content'))
        data.update({'user_id': user.id, 'topic_id': topic.id,
                     'content': strip_xss_tags(content)})
        if reply:
            category = 'edit'
            pre_content = reply.content
            cur_content = data.get('content')
            changed = 0
            if pre_content != cur_content:
                diff_content = ghdiff.diff(pre_content, cur_content, css=None)
                changed = 1
            if changed == 1:
                reply.content = cur_content
                History(user_id=user.id, content=diff_content,
                        reply_id=reply.id).save()
            else:
                return reply
        else:
            category = 'create'
            reply = Reply(**data)
        return reply.save(category=category)
