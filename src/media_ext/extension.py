from extension.extension import Extension

from django.db.models import Count, Min, Sum, Max, F, Func, Value, CharField, Q
from django.db.models.functions import Extract

class MediaExtension(Extension):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.read_match_function = lambda: False
        self.read_match_policy_level = -1

    def read_match_policy(self, level=0):

        def registry(function):
            if level > self.read_match_policy_level:
                self.read_match_function = function
                self.read_match_policy_level = level
            return function

        return registry

    def get_clientbase_behaviors(self, clientbase):
        behaviors = []

        read_qs = (clientbase.readbase_set.filter(removed=False)
            .values('datetime__date', 'articlebase__title', 'articlebase__path')
            .annotate(from_datetime=Min('datetime'), to_datetime=Max('datetime'))
        ).order_by('from_datetime')

        for item in read_qs:
            from_datetime = item['from_datetime']
            to_datetime = item['to_datetime']
            value = item['articlebase__title']
            path = item['articlebase__path']
            if not value:
                value = '--'

            if path:
                value = f'<a class="text-info" href="{path}">{value}</a>'


            obj = {
                'datetime': from_datetime,
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
