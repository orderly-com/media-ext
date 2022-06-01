import re
import gc
import datetime

from django.conf import settings
from django.utils import timezone

from cerem.tasks import fetch_site_tracking_data
from cerem.utils import kafka_headers

from datahub.models import DataSync
from team.models import Team
from tag_assigner.models import TagAssigner, ValueTag

from core.utils import batch_list

from ..media_importly.importers import ReadImporter, Read
from ..media_media.models import ReadBase
from ..media_media.datahub import DataTypeSyncReadingData

from ..extension import media_ext


@media_ext.periodic_task()
def sync_reading_data(period_from=None, period_to=None, **kwargs):
    for team in Team.objects.all():
        params = {
            'actions': ['view', 'proceed']
        }
        datasource, created = team.datasource_set.get_or_create(name='system')
        last_sync = team.datasync_set.filter(data_type=DataTypeSyncReadingData).order_by('-datetime').first()

        if period_from:
            params['from_datetime'] = period_from

        elif last_sync:
            params['from_datetime'] = last_sync.datetime

        datasync = DataSync.generate_next_object(team, data_type=DataTypeSyncReadingData)
        params['to_datetime'] = datasync.datetime

        if period_to:
            params['to_datetime'] = period_to
            datasync.datetime = period_to
            datasync.save()

        data = fetch_site_tracking_data(team, **params)
        data = [
            {
                'datetime': row[kafka_headers.DATETIME],
                'title': row[kafka_headers.TITLE],
                'uid': row[kafka_headers.USER],
                'cid': row[kafka_headers.CID],
                'path': row[kafka_headers.PATH],
                'action': row[kafka_headers.ACTION],
                'attributions': row[kafka_headers.PARAMS],
            } for row in data
        ]

        importer = ReadImporter(team, datasource)

        importer.create_datalist(data)

        importer.data_to_raw_records()

        importer.process_raw_records()


@media_ext.periodic_task()
def find_reader(*args, **kwargs):
    for team in Team.objects.all():
        clientbase_uid_map = {}
        for bridge in team.clientbase_set.filter(removed=False).values('id', 'external_id'):
            clientbase_uid_map[bridge['external_id']] = bridge['id']
        readbase_qs = (team.readbase_set.filter(removed=False, clientbase__isnull=True)
            .exclude(uid='')
            .values('id', 'uid', 'articlebase__value_tag_ids')
        )
        for readbase_batch in batch_list(readbase_qs, settings.BATCH_SIZE_M):
            readbases_to_update = []
            for readbase in readbase_batch:
                clientbase_id = clientbase_uid_map.get(readbase['uid'], None)
                if clientbase_id:
                    readbases_to_update.append(
                        ReadBase(
                            id=readbase['id'],
                            clientbase_id=clientbase_id
                        )
                    )
            ReadBase.objects.bulk_update(readbases_to_update, ['clientbase_id'], batch_size=settings.BATCH_SIZE_M)
            gc.collect()


@media_ext.periodic_task()
def find_article(period_from=None, period_to=None):
    if period_to is None:
        period_to = timezone.now()

    if period_from is None:
        period_from = period_to - datetime.timedelta(days=30)

    for team in Team.objects.all():
        articlebases = list(
            team.articlebase_set.filter(removed=False).values('id', 'location_rule')
        )
        pattern = ''

        location_rule_map = {}
        location_rules = []
        for articlebase in articlebases:
            location_rule_map[articlebase['location_rule']] = articlebase['id']
            location_rules.append(articlebase['location_rule'])

        pattern = '|'.join(location_rules)

        readbase_qs = team.readbase_set.filter(articlebase__isnull=True, datetime__gte=period_from, datetime__lte=period_to, removed=False).values('path', 'title', 'id')

        readbases_to_update = []
        for readbase_data in readbase_qs:
            result = re.match(pattern, readbase_data['path'])
            if result:
                articlebase_id = location_rule_map[result.group(0)]
                readbase = ReadBase(id=readbase_data['id'], articlebase_id=articlebase_id)
                readbases_to_update.append(readbase)

        ReadBase.objects.bulk_update(readbases_to_update, ['articlebase_id'], batch_size=settings.BATCH_SIZE_M)
        del readbases_to_update
        gc.collect()
