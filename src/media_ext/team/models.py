from team import models as team_models
from ..extension import media

@media.OrderModel
class ReadBase(team_models.OrderBase):
    class Meta:
        proxy = True


@media.ProductModel
class ArticleBase(team_models.ProductBase):
    class Meta:
        proxy = True


@media.ClientModel
class Reader(team_models.ClientBase):
    class Meta:
        proxy = True

    def get_purchase_behaviors(self):

        from orderly.models import DataSource

        if self.team.has_child:
            teams = self.team.get_children()
            orderbase_qs = PurchaseBase.objects.filter(team__in=teams, removed=False).order_by('-datetime')

        else:
            orderbase_qs = PurchaseBase.objects.filter(team=self.team, removed=False).order_by('-datetime')

        datasource_dict = {}

        behaviors = []

        # # orderbases
        qs = orderbase_qs.filter(clientbase=self).only('id', 'datetime', 'status_key', 'total_price')

        for orderbase in qs.all():

            if orderbase.datasource_id in datasource_dict:
                datasource = datasource_dict[orderbase.datasource_id]
            else:

                _ = DataSource.objects.filter(id=orderbase.datasource_id).only('id').first()

                datasource = {
                    'name': _.get_family_root_name(),
                    'url': _.get_detail_url(),
                }

                datasource_dict[orderbase.datasource_id] = datasource

            obj = {
                'datetime': orderbase.datetime,
                'trigger_by': 'client',
                'action': orderbase.status_key,
                'value': orderbase.total_price,
                'data': {
                    'action': orderbase.status_key,
                    'datasource': datasource,
                    'orderbase': {'url': orderbase.get_detail_url(), 'external_id': orderbase.external_id},
                    'orderproducts': list(orderbase.orderproduct_set.exclude(productbase__internal_product=True).values('external_id', 'productbase__uuid', 'name', 'spec', 'price', 'quantity', 'refound', 'append')),
                },
            }

            behaviors.append(obj)

        return behaviors
