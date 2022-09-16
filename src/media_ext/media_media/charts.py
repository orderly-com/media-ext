import datetime
import itertools
import statistics
from dateutil import relativedelta

from django.utils import timezone
from django.db.models.functions import TruncDate, ExtractMonth, ExtractYear, Cast
from django.db.models import Count, Func, Max, Min, IntegerField

from charts.exceptions import NoData
from charts.registries import chart_category
from charts.drawers import PieChart, BarChart, LineChart, HorizontalBarChart, DataCard
from filtration.conditions import DateRangeCondition, ModeCondition
from orderly_core.team.charts import client_behavior_charts
from cerem.tasks import clickhouse_client
from cerem.utils import F

@client_behavior_charts.chart(name='關鍵字文章標籤點閱次數')
class TopArticleTags(HorizontalBarChart):

    MODE_ALL_CLIENTS = 'all'
    MODE_MEMBER_ONLY = 'member'

    def __init__(self):
        super().__init__()
        self.add_options(
            mode=ModeCondition('').choice(
                {'text': '全部', 'id': self.MODE_ALL_CLIENTS},
                {'text': '純會員', 'id': self.MODE_MEMBER_ONLY}
            ).default(self.MODE_ALL_CLIENTS)
        )

    def explain_x(self):
        return '文章標籤'

    def explain_y(self):
        return '點閱數'

    def draw(self):
        mode = self.options.get('mode')
        display_count = self.options.get('display_count', 10)
        tag_map = {}

        for article in self.team.articlebase_set.filter(removed=False).all():
            if mode == self.MODE_ALL_CLIENTS:
                count = article.readbase_set.count()
            else:
                count = article.readbase_set.filter(F('clientbase_id') != None).count()
            for tag_id in article.value_tag_ids:
                tag_map[tag_id] = tag_map.get(tag_id, 0)
                tag_map[tag_id] += 1

        top_tag_ids = sorted(tag_map, key=tag_map.get)[:display_count]
        self.set_labels(
            list(
                self.team.valuetag_set.filter(id__in=top_tag_ids).values_list('name', flat=True)
            )
        )
        self.create_label(name='點閱數', data=list(map(tag_map.get, top_tag_ids)))


@client_behavior_charts.chart(name='人均點閱次數')
class AvgReadCountPerVisit(DataCard):

    MODE_ALL_CLIENTS = 'all'
    MODE_MEMBER_ONLY = 'member'

    def __init__(self):
        self.add_options(
            mode=ModeCondition('').choice(
                {'text': '全部', 'id': self.MODE_ALL_CLIENTS},
                {'text': '純會員', 'id': self.MODE_MEMBER_ONLY}
            ).default(self.MODE_ALL_CLIENTS)
        )

    def draw(self):
        mode = self.options.get('mode')
        read_article_count_data = [] # 1, 2, 5, 3
        for clientbase in self.team.clientbase_set.only('id'):
            data = clientbase.media_info.readbase_set.values('datetime', 'articlebase_id')
            if not data:
                continue
            previous_time = data[0]['datetime']
            articles = set()
            for item in sorted(data, key=lambda item: item['datetime']):
                if (item['datetime'] - previous_time).total_seconds > 7200:
                    read_article_count_data.append(len(articles))
                    articles = set()
                else:
                    articles.add(item['articlebase_id'])
                previous_time = item['datetime']
        if not read_article_count_data:
            raise NoData('數據不足')
        self.create_label(name='人均點閱次數', data=statistics.mean(read_article_count_data))
