
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from datahub.models import DataSource
from importly.exceptions import EssentialDataMissing
from importly.importers import DataImporter

from config.celery import app
from team.models import Team

from .importers import ArticleDataTransfer

@app.task(time_limit=settings.APP_TASK_TIME_LIMIT_SM)
def process_articlelist(team_slug, data):
    team = Team.objects.get(slug=team_slug)

    datasource = data.get('datasource')

    try:
        datasource = DataSource.objects.filter(uuid=datasource).only('id').first()
    except (DataSource.DoesNotExist, ValidationError):
        raise EssentialDataMissing('datasource')

    try:
        rows = data['data']
    except KeyError:
        raise EssentialDataMissing('data')

    importer = DataImporter(team, datasource)

    datalist = importer.create_datalist(rows)

    importer.data_to_raw_records(ArticleDataTransfer)