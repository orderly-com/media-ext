import re

from django.urls import reverse

from datahub.models import DataType, data_type
from .models import ArticleBase

from ..extension import media_ext


class DataTypeRead(DataType):
    key = 'read'


@data_type
class DataTypeArticle(DataType):
    key = 'article'

    @staticmethod
    def get_records_fields_display():
        return [
            ('external_id', '文章編號', '1', 'text-center'),
            ('datetime',    '發布日期', '1', 'text-center'),
            ('title',       '文章標題', '1', 'text-center'),
            ('author',      '作者',     '1', 'text-center'),
            ('external_id', '文章標題', '1', 'text-center'),
        ]

    @staticmethod
    def get_records(datalist):
        external_ids = datalist.article_set.values('external_id')
        articlebase_qs = datalist.team.articlebase_set.filter(external_id__in=external_ids, removed=False)
        records = list(articlebase_qs.values('datetime', 'external_id', 'title', 'author', 'uuid'))
        for record in records:
            if record['datetime']:
                record['datetime'] = record['datetime'].strftime('%Y-%m-%d')
            else:
                record['datetime'] = '-'
            external_id = record['external_id'] or '-'
            url = reverse('media:article-detail', kwargs={'uuid': record['uuid']})
            record['external_id'] = f'<a class="text-info" href="{url}">{external_id}</a>'
            record['title'] = record['title'] or '-'

        return records


class DataTypeSyncReadingData(DataType):
    key = 'sync_reading_data'


class channels:
    ARTICLE_IMPORT = 'article_import'
    ARTICLE_TO_ARTICLEBASE = 'article_to_articlebase'


@media_ext.read_match_policy(level=0)
def match_read_event(rule, read):
    return bool(re.match(rule, read['path']))
