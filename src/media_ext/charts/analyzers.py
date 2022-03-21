from typing import List, Optional

import datetime
import pandas as pd

from analytics import analyzers

from cerem.utils import PipelineBuilder, wrappers
from cerem.tasks import aggregate_collection
from client_filter.conditions import ChoiceCondition

from ..tasks import COLLECTION_ORDERPRODUCT, COLLECTION_PURCHASEBASE
from ..team.models import PurchaseBase

class PurchaseBasePipelineBuilder(PipelineBuilder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.filter(status_key=PurchaseBase.STATUS_CONFIRMED)


class DataSourceSalesTrendingAnalyzer(analyzers.Analyzer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_options(time_scale=ChoiceCondition('時間單位').choice(day='天', week='週', month='月', year='年'))

    def analyze(
        self, team, date_start: datetime.datetime, date_end: datetime.datetime,
        datasources: Optional[List]=None, *args, **options
    ) -> pd.DataFrame:

        builder = PurchaseBasePipelineBuilder()

        builder.filter(datetime__range=[date_start, date_end], datasource_id__in=datasources)
        builder.group(price_floor=wrappers.Trunc('total_price', place=-2)).annotating()

        data = aggregate_collection(team, COLLECTION_PURCHASEBASE, builder.resolve())
        time_scale = self.options.get('time_scale', 'week')
        df = pd.DataFrame(data)

        if df.empty:
            return df

        return pd.DataFrame()

