import re

from ..extension import media_ext


class data_types:
    SYNC_READING_DATA = 'sync_reading_data'


class channels:
    ARTICLE_IMPORT = 'article_import'
    ARTICLE_TO_ARTICLEBASE = 'article_to_articlebase'


@media_ext.read_match_policy(level=0)
def match_read_event(rule, read):
    return bool(re.match(rule, read['path']))
