from django import template
from django.template.defaultfilters import stringfilter

from .models import ArticleBase

register = template.Library()

@register.filter
@stringfilter
def article_status_display(status: str):
    status_dict = {
        ArticleBase.STATE_DRAFT: '草稿',
        ArticleBase.STATE_PUBLISHED: '已發布',
        ArticleBase.STATE_PRIVATE: '私人',
        ArticleBase.STATE_UNSET: '未知',
    }
    return status_dict.get(status, '未知')
