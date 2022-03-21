import extension.extension as cdp_extension

# from .chart_extension.analyzers import DataSourceSalesTrendingAnalyzer

from .team.conditions import (
    RFMScoreR, RFMScoreF, RFMScoreM, PurchaseCount, PurchaseAmount, ProductCategoryCondition, ProductCondition
)
from .team.models import PurchaseBase, PurchaserBase, SkuBase

class Extension(cdp_extension.Extension):
    def __init__(self):
        super().__init__()

        self.register_filter_tab(
            'rfm',
            {'zh_tw': 'RFM'},
            [RFMScoreR('(R) 時間分數'), RFMScoreF('(F) 頻率分數'), RFMScoreM('(M) 消費分數')],
            icon='icon-height'
        )

        self.register_filter_tab(
            'order',
            {'zh_tw': '購買行為篩選'},
            [PurchaseCount('購買次數'), PurchaseAmount('購買金額'), ProductCategoryCondition('購買商品類別'), ProductCondition('購買商品')],
            icon='icon-cart2'
        )

        self.register_order_model(PurchaseBase)

        self.register_client_model(PurchaserBase)

        self.register_product_model(SkuBase)

        # self.register_chart_tab(
        #     'overview',
        #     {'zh_tw': '總覽'},
        #     [DataSourceSalesTrendingAnalyzer('通路銷售趨勢')]
        # )

    def get_clientbase_behaviors(self, clientbase):
        try:
            behaviors = []
            purchaser = PurchaserBase.objects.get(id=clientbase.id)

            behaviors += purchaser.get_purchase_behaviors()

            return behaviors
        except:
            return []

    def get_localization():
        return {
            'zh_tw': '電商 / 零售'
        }

    def get_filter_tab_localization():
        return {
            'zh_tw': ''
        }

    def setup():
        pass
