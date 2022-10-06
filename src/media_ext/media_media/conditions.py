from typing import Any, Tuple

from django.db.models.query import Q
from django.db.models import QuerySet, Count, Avg, F

from filtration.conditions import Condition, RangeCondition, DateRangeCondition, SelectCondition, ChoiceCondition
from filtration.registries import condition
from filtration.exceptions import UseIdList

from tag_assigner.models import ValueTag

from cerem.tasks import aggregate_from_cerem


@condition
class ArticleCount(RangeCondition):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.range(0, 20)
        self.config(postfix='篇')

    def filter(self, client_qs: QuerySet, article_count_range: Any) -> Tuple[QuerySet, Q]:
        return client_qs, Q(media_info__article_count__range=article_count_range)


@condition
class AverageReadPercentage(RangeCondition):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.range(0, 100)
        self.config(postfix='%')

    def filter(self, client_qs: QuerySet, avg_read_percentage_range: Any) -> Tuple[QuerySet, Q]:
        val_min, val_max = avg_read_percentage_range
        progress_range = (val_min / 100, val_max / 100)
        return client_qs, Q(media_info__avg_reading_progress__range=progress_range)

@condition
class ArticleTagCondition(SelectCondition):
    def filter(self, client_qs: QuerySet, choices: Any) -> Tuple[QuerySet, Q]:

        q = Q(value_tag_ids__contains=choices)

        return client_qs, q

    def lazy_init(self, team, *args, **kwargs):
        articles = list(team.articlebase_set.values_list('value_tag_ids', flat=True))
        value_tag_ids = []
        for article_tag_ids in articles:
            value_tag_ids += article_tag_ids
        data = list(ValueTag.objects.filter(id__in=value_tag_ids).values('id', text=F('name')))

        self.choice(*data)
