from typing import Any, Tuple

from django.db.models.query import Q
from django.db.models import QuerySet, Count, Avg

from filtration.conditions import Condition, RangeCondition, DateRangeCondition, SelectCondition, ChoiceCondition
from filtration.models import condition


@condition
class ArticleCount(RangeCondition):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.range(0, 100)
        self.config(postfix='篇')

    def filter(self, client_qs: QuerySet, article_count_range: Any) -> Tuple[QuerySet, Q]:
        client_qs = client_qs.annotate(article_count=Count('readbase__articlebase__id', distinct=True))

        q = Q(article_count__range=article_count_range)
        return client_qs, q


@condition
class AverageReadPercentage(RangeCondition):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.range(0, 100)
        self.config(postfix='%')

    def filter(self, client_qs: QuerySet, avg_read_percentage_range: Any) -> Tuple[QuerySet, Q]:
        percentage_min, percentage_max = avg_read_percentage_range
        progress_range = (percentage_min/100, percentage_max/100)

        client_qs = client_qs.annotate(avg_read_progress=Avg('readbase__read_rate'))

        q = Q(avg_read_progress__range=progress_range)
        return client_qs, q

