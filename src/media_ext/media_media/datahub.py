import re

from datahub.models import DataType, data_type

from ..extension import media_ext


class DataTypeRead(DataType):
    key = 'read'


@data_type
class DataTypeArticle(DataType):
    key = 'article'
    name = '文章'
    color = 'blue'

    @staticmethod
    def get_datetime_min(datalist):
        aggregation = datalist.article_set.aggregate(min_datetime=Min('datetime'))
        return aggregation['min_datetime']

    @staticmethod
    def get_datetime_max(datalist):
        aggregation = datalist.article_set.aggregate(max_datetime=Max('datetime'))
        return aggregation['max_datetime']


class DataTypeSyncReadingData(DataType):
    key = 'sync_reading_data'


class channels:
    ARTICLE_IMPORT = 'article_import'
    ARTICLE_TO_ARTICLEBASE = 'article_to_articlebase'


@media_ext.read_match_policy(level=0)
def match_read_event(rule, read):
    return bool(re.match(rule, read['path']))
