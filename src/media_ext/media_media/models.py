from django.urls import reverse
import html2text
from uuid import uuid4

from django.db import models
from django.contrib.postgres.fields import JSONField, ArrayField

from datahub.models import DataSource

from core.models import BaseModel, ValueTaggable
from team.models import Team, OrderBase, ProductBase, ClientBase, client_info_model
from tag_assigner.utils import api_taggable

from cerem.utils import TeamMongoDB, F, Sum

from ..extension import media_ext


class PageBase(BaseModel):
    pass


class ArticleCategory(BaseModel):
    class Meta:

        indexes = [
            models.Index(fields=['team', ]),
            models.Index(fields=['name', ]),

            models.Index(fields=['team', 'name']),
        ]

    team = models.ForeignKey(Team, blank=False, on_delete=models.CASCADE)

    external_id = models.TextField(blank=False)
    uuid = models.UUIDField(default=uuid4, unique=True)

    name = models.TextField(blank=False)
    removed = models.BooleanField(default=False)


@media_ext.ProductModel
@api_taggable(type_id='article')
class ArticleBase(ProductBase):
    class Meta:
        indexes = [
            models.Index(fields=['datasource', ]),
            models.Index(fields=['title', ]),

            models.Index(fields=['team', 'datasource']),
            models.Index(fields=['team', 'title']),
        ]

    def __getattr__(self, attr):
        if attr == 'readbase_set':
            return TeamMongoDB(self.team).readbases.filter(articlebase_id=self.id)

    datetime = models.DateTimeField(blank=True, null=True)

    author = models.TextField(blank=False)
    title = models.TextField(blank=False)
    path = models.TextField(blank=False)
    content = models.TextField(blank=False)

    location_rule = models.CharField(max_length=256)

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


@client_info_model
class MediaInfo(BaseModel):

    clientbase = models.OneToOneField(ClientBase, related_name='media_info', blank=False, on_delete=models.CASCADE)

    def __getattr__(self, attr):
        if attr == 'readbase_set':
            return TeamMongoDB(self.clientbase.team).readbases.filter(clientbase_id=self.clientbase_id)

    def get_sum_of_total_read(self):
        qs = self.clientbase.media_info.readbase_set

        data = qs.aggregate(total_progress=Sum('progress'))
        total_progress = data.get('total_progress', 0)
        if total_progress is None:
            total_progress = 0

        return total_progress

    def get_count_of_total_article(self):
        return self.clientbase.media_info.readbase_set.filter(F('articlebase_id') != None).values('path').count()

    def get_avg_of_each_read(self):
        qs = self.clientbase.media_info.readbase_set.filter(F('articlebase_id') != None)
        if not qs.count():
            return 0

        data = qs.aggregate(total_progress=Sum('progress'))
        total_progress = data.get('total_progress', 0)

        return total_progress / qs.count()

    def get_times_of_read(self):
        return self.clientbase.media_info.readbase_set.filter(F('articlebase_id') != None).count()

    def first_read(self):
        first_readbase = self.clientbase.media_info.readbase_set.filter(F('articlebase_id') != None).order_by('datetime').first()
        if first_readbase:
            return first_readbase.datetime
        else:
            return None

    def last_read(self):
        last_readbase = self.clientbase.media_info.readbase_set.filter(F('articlebase_id') != None).order_by('datetime').last()
        if last_readbase:
            return last_readbase.datetime
        else:
            return None
