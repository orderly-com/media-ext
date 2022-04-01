from django.conf import settings

from cerem.tasks import fetch_site_tracking_data
from cerem.utils import kafka_headers

from datahub.models import DataSync
from team.models import Team
from tag_assigner.models import TagAssigner, ValueTag

from ..media_importly.importers import ReadImporter, ReadDataTransfer
from ..media_media.models import ReadBase

from .datahub import data_types
from ..extension import media_ext


@media_ext.periodic_task()
def sync_reading_data(*args, **kwargs):
    for team in Team.objects.all():
        params = {}
        datasource, created = team.datasource_set.get_or_create(name='system')
        last_sync = team.datasync_set.filter(data_type=data_types.SYNC_READING_DATA).order_by('-datetime').first()
        if last_sync:
            params['from_datetime'] = last_sync.datetime

        datasync = DataSync.generate_next_object(team, data_type=data_types.SYNC_READING_DATA)
        params['to_datetime'] = datasync.datetime

        data = fetch_site_tracking_data(team, **params)
        data = [
            {
                'datetime': row[kafka_headers.DATETIME],
                'title': row[kafka_headers.TITLE],
                'path': row[kafka_headers.PATH],
                'attributions': row[kafka_headers.PARAMS],
            } for row in data
        ]

        importer = ReadImporter(team, datasource)

        importer.create_datalist(data)

        importer.data_to_raw_records(ReadDataTransfer)

        importer.process_raw_records()


@media_ext.periodic_task()
def find_reader(*args, **kwargs):
    for team in Team.objects.all():
        clientbase_uid_map = {}
        for bridge in team.clientbaseuid_set.values('clientbase_id', 'uid'):
            clientbase_uid_map[bridge['uid']] = bridge['clientbase_id']

        readbases_to_update = []

        for readbase in team.readbase_set.filter(removed=False, clientbase__isnull=True).values('id', 'uid'):
            clientbase_id = clientbase_uid_map.get(readbase['uid'], None)
            if clientbase_id:
                readbases_to_update.append(
                    ReadBase(
                        id=readbase['id'],
                        clientbase_id=clientbase_id
                    )
                )
            value_tags = list(ValueTag.objects.filter(id__in=readbase.article.value_tag_ids))
            TagAssigner.bulk_assign_tags(value_tags, team.clientbase_set.get(id=clientbase_id), 'article')

        ReadBase.objects.bulk_update(readbases_to_update, ['clientbase_id'], batch_size=settings.BATCH_SIZE_M)
