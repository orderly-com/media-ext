from uuid import uuid4

from django.db import models
from django.contrib.postgres.fields import JSONField, ArrayField

from datahub.models import DataSource
from team.models import Team

from core.models import BaseModel, ValueTaggable


class Article(BaseModel):
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

    author = models.CharField(max_length=128)
    title = models.CharField(max_length=128)
    content = models.TextField(blank=False)

    removed = models.BooleanField(default=False)

    datasource = models.ForeignKey(DataSource, blank=False, default=1, on_delete=models.CASCADE)

    attributions = JSONField(default=dict)
