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
        articles = (
            self.team.articlebase_set
            .filter(removed=False)
            .values('id', 'user_read_count', 'clientbase_read_count', 'value_tag_ids')
        )
        for article in articles:
            if mode == self.MODE_ALL_CLIENTS:
                count = article['user_read_count']
            else:
                count = article['clientbase_read_count']
            for tag_id in article['value_tag_ids']:
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
    def draw(self):
        query = f"select avg(article_count) from (select count(pt) as article_count, cid, toStartOfHour(t) from events where at='view' AND tc='{self.team.integration.team_code}' group by cid, toStartOfHour(t)) as visits"
        data = clickhouse_client.execute(query)[0][0]
        self.create_label(name='人均點閱次數', data=f'{data:.1f}次')


@client_behavior_charts.chart(name='會員人均點閱次數')
class MemberAvgReadCountPerVisit(DataCard):

    def draw(self):
        query = f"select avg(article_count) from (select count(pt) as article_count, cid, toStartOfHour(t) from events where at='view' AND uid != '' and tc='{self.team.integration.team_code}' group by cid, toStartOfHour(t)) as visits"
        data = clickhouse_client.execute(query)[0][0]
        self.create_label(name='會員人均點閱次數', data=f'{data:.1f}次')
