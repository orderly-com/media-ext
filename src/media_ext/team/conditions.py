import datetime

from typing import Any, List, Tuple, Optional, Dict
from dateutil.relativedelta import relativedelta

from django.db.models import Subquery, Count, Min, Sum, Max, F
from django.db.models.expressions import OuterRef
from django.db.models.fields import IntegerField
from django.db.models.query import Q
from django.db.models import QuerySet
from django.contrib.postgres.aggregates import ArrayAgg

from team.models import OrderProduct

from core.utils import list_to_dict
from client_filter.conditions import (
    RangeCondition, BooleanCondition, DateRangeCondition, SelectCondition
)

from ..extension import media

from .models import PurchaseBase


@media.condition(tab='reading')
class AverageReadRatio(RangeCondition):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.range(0, 5)
        self.config(postfix=' 分', max_postfix=' +')

    def filter(self, client_qs: QuerySet, rfm_r_range: Any) -> Tuple[QuerySet, Q]:
        q = Q()

        q &= Q(rfm_recency__range=rfm_r_range)

        return client_qs, q
