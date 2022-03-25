from uuid import uuid4

from django.db import models
from django.contrib.postgres.fields import JSONField, ArrayField

from orderly.models import DataSource

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
    class Meta:
        indexes = [
            models.Index(fields=['team', ]),
            models.Index(fields=['datasource', ]),
            models.Index(fields=['title', ]),

            models.Index(fields=['team', 'datasource']),
            models.Index(fields=['team', 'title']),
        ]

    team = models.ForeignKey(Team, blank=False, on_delete=models.CASCADE)
    uuid = models.UUIDField(default=uuid4, unique=True)

    tags = ArrayField(models.CharField(max_length=512))
    author = models.CharField(max_length=128)
    title = models.CharField(max_length=128)
    content = models.TextField(blank=False)

    removed = models.BooleanField(default=False)

    datasource = models.ForeignKey(DataSource, blank=False, default=1, on_delete=models.CASCADE)

    attributions = JSONField(default=dict)

@media_ext.ClientModel
class Reader(ClientBase):
    class Meta:
        proxy = True
