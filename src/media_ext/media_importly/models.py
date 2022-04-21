from uuid import uuid4

from django.db import models
from django.contrib.postgres.fields import JSONField, ArrayField

from datahub.models import DataSource
from team.models import Team

from core.models import BaseModel, ValueTaggable
from importly.models import RawModel

from ..media_media.models import ArticleBase, ReadBase, ReadEvent


class Article(RawModel):

    class Meta:
        indexes = [
            models.Index(fields=['team', ]),
            models.Index(fields=['datasource', ]),
            models.Index(fields=['title', ]),

            models.Index(fields=['team', 'datasource']),
            models.Index(fields=['team', 'title']),
        ]

    external_id = models.TextField(blank=False)

    team = models.ForeignKey(Team, blank=False, on_delete=models.CASCADE)
    uuid = models.UUIDField(default=uuid4, unique=True)

    datetime = models.DateTimeField(blank=True, null=True)

    author = models.TextField(blank=False)
    title = models.TextField(blank=False)
    content = models.TextField(blank=False)
    path = models.CharField(max_length=256)

    status = models.CharField(max_length=64, default=str)

    removed = models.BooleanField(default=False)

    datasource = models.ForeignKey(DataSource, blank=False, on_delete=models.CASCADE)

    attributions = JSONField(default=dict)

    categories = ArrayField(JSONField(default=dict), default=list)

    articlebase = models.ForeignKey(ArticleBase, blank=True, null=True, on_delete=models.CASCADE)


class Read(RawModel):
    class Meta:
        indexes = [
            models.Index(fields=['team', ]),
            models.Index(fields=['datasource', ]),
            models.Index(fields=['title', ]),

            models.Index(fields=['team', 'datasource']),
            models.Index(fields=['team', 'title']),
        ]

    external_id = models.TextField(blank=False)

    uid = models.TextField(blank=False)
    cid = models.TextField(blank=False)
    team = models.ForeignKey(Team, blank=False, on_delete=models.CASCADE)

    datetime = models.DateTimeField(blank=True, null=True)

    # for articlebase
    title = models.TextField(blank=False)
    path = models.TextField(blank=False)

    proceed = models.BooleanField(default=False)

    removed = models.BooleanField(default=False)

    datasource = models.ForeignKey(DataSource, blank=False, on_delete=models.CASCADE)

    readbase = models.ForeignKey(ReadBase, blank=True, null=True, on_delete=models.CASCADE)
    readevent = models.ForeignKey(ReadEvent, blank=True, null=True, on_delete=models.CASCADE)

    attributions = JSONField(default=dict)
