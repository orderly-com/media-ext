import uuid4

from django.db import models

from team.models import Team, OrderBase, ProductBase, ClientBase
from core.models import BaseModel

from ..extension import media_ext

@media_ext.OrderModel
class ReadBase(OrderBase):
    pass


@media_ext.ProductModel
class PageBase(ProductBase):
    pass


class ArticleBase(BaseModel):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    uuid = models.UUIDField(default=uuid4, unique=True)

    title = models.CharField(max_length=300)
    content = models.TextField(default=str)


@media_ext.ClientModel
class Reader(ClientBase):
    class Meta:
        proxy = True
