from django.urls import reverse
import html2text
from uuid import uuid4

from django.db import models
from django.contrib.postgres.fields import JSONField, ArrayField

from datahub.models import DataSource

from team.models import Team, OrderBase, ProductBase, ClientBase
from core.models import BaseModel

from ..extension import media_ext


@media_ext.ProductModel
class PageBase(ProductBase):
    pass


class ArticleCategory(BaseModel):
    class Meta:

        indexes = [
            models.Index(fields=['team', ]),
            models.Index(fields=['name', ]),

            models.Index(fields=['team', 'name']),
        ]

    team = models.ForeignKey(Team, blank=False, on_delete=models.CASCADE)

    external_id = models.CharField(max_length=128)
    uuid = models.UUIDField(default=uuid4, unique=True)

    name = models.CharField(max_length=128)
    removed = models.BooleanField(default=False)


class ArticleBase(BaseModel):
    class Meta:
        indexes = [
            models.Index(fields=['team', ]),
            models.Index(fields=['datasource', ]),
            models.Index(fields=['title', ]),

            models.Index(fields=['team', 'datasource']),
            models.Index(fields=['team', 'title']),
        ]

    external_id = models.CharField(max_length=128)

    team = models.ForeignKey(Team, blank=False, on_delete=models.CASCADE)
    uuid = models.UUIDField(default=uuid4, unique=True)

    datetime = models.DateTimeField(blank=True, null=True)

    author = models.CharField(max_length=128)
    title = models.CharField(max_length=128)
    content = models.TextField(blank=False)

    STATE_DRAFT = 'draft'
    STATE_PUBLISHED = 'published'
    STATE_PRIVATE = 'private'
    STATE_UNSET = 'unset'

    # discard soon
    STATE_CHOICES = (
        (STATE_DRAFT, '草稿'),
        (STATE_PUBLISHED, '已發布'),
        (STATE_PRIVATE, '未公開'),
        (STATE_UNSET, '未知'),
    )
    status = models.CharField(max_length=64, choices=STATE_CHOICES, default='draft')

    removed = models.BooleanField(default=False)

    datasource = models.ForeignKey(DataSource, blank=False, default=1, on_delete=models.CASCADE)

    attributions = JSONField(default=dict)
    categories = models.ManyToManyField(ArticleCategory, blank=True)

    def get_pure_text_count(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self.content, features="html.parser")

        # kill all script and style elements
        for script in soup(["script", "style"]):
            script.extract()    # rip it out

        # get text
        text = soup.get_text()

        # break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return len(text)

    def get_latest_reader(self):
        clientbase = None
        readbase = self.readbase_set.order_by('-c_at').first()
        if readbase:
            clientbase = readbase.clientbase

        return clientbase

    def get_detail_url(self):
        return reverse('media:article-detail', kwargs={'uuid': self.uuid})

    def get_records_url(self):
        return reverse('media:article-records', kwargs={'uuid': self.uuid})


@media_ext.ClientModel
class Reader(ClientBase):
    class Meta:
        proxy = True


@media_ext.OrderModel
class ReadBase(OrderBase):
    articlebase = models.ForeignKey(ArticleBase, blank=False, on_delete=models.CASCADE)