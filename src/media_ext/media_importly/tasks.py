from django.conf import settings
from django.core.exceptions import ValidationError

from datahub.models import DataSource
from importly.exceptions import EssentialDataMissing
from importly.models import DataList

from config.celery import app
from team.models import Team

from .importers import ArticleImporter

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

    importer = ArticleImporter(team, datasource)

    datalist = importer.create_datalist(rows)
    datalist.set_step(DataList.STEP_CREATE_RAW_RECORDS)

    importer.data_to_raw_records()
    datalist.set_step(DataList.STEP_PROCESS_RAW_RECORDS)

    importer.process_raw_records()
    datalist.set_step(DataList.STEP_DONE)
