from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

from ..models import ArticleBase

register = template.Library()

@register.filter
@stringfilter
def article_status_display(status: str):
    display_dict = {
        ArticleBase.STATE_DRAFT: '草稿',
        ArticleBase.STATE_PUBLISHED: '已發布',
        ArticleBase.STATE_PRIVATE: '私人',
        ArticleBase.STATE_UNSET: '未知',
    }
    class_dict = {
        ArticleBase.STATE_DRAFT: 'text-muted',
        ArticleBase.STATE_PUBLISHED: 'text-info',
        ArticleBase.STATE_PRIVATE: 'text-muted',
        ArticleBase.STATE_UNSET: 'text-muted',
    }
    display_text = display_dict.get(status, '未知')
    display_class = class_dict.get(status, 'text-muted')
    return mark_safe(f'<span class="{display_class}">{display_text}</span>')
