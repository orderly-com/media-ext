from extension.extension import Extension

from django.db.models import Count, Min, Sum, Max, F, Func, Value, CharField, Q
from django.db.models.functions import Extract


class MediaExtension(Extension):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.read_match_function = lambda: False
        self.read_match_policy_level = -1

    def define_mongodb_collections(self):
        return {
            'readbases':
            {
                'indexes': ['cid', 'progress', 'clientbase_id', 'productbase_id'],
                'schema': {
                    'datetime': {'type': 'datetime'},
                    'events.datetime': {'type': 'datetime'}
                }
            },
        }

    def read_match_policy(self, level=0):

        def registry(function):
            if level > self.read_match_policy_level:
                self.read_match_function = function
                self.read_match_policy_level = level
            return function

        return registry

    def get_clientbase_behaviors(self, clientbase):
        behaviors = []
        read_qs = clientbase.media_info.readbase_set.values('datetime', 'title', 'path').order_by('datetime')

        for item in read_qs:
            value = item['title']
            rate = item['rate']
            path = item['path']
            if not value:
                value = '--'

            if path:
                value = f'<a class="text-info" href="{path}">{value}</a> ({rate*100}%)'


            obj = {
                'datetime': item['datetime'],
                'trigger_by': 'client',
                'action': '閱讀',
                'value': '',
                'data': value
            }
            behaviors.append(obj)
        return behaviors



media_ext = MediaExtension()

media_ext.client_info_panel_templates = [
    'team/clients/_media_info.html'
]
