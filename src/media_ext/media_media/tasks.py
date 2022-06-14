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

from cerem.tasks import insert_to_cerem, aggregate_from_cerem

from ..media_importly.importers import ReadImporter, Read
from ..media_media.models import ReadBase
from ..media_media.datahub import DataTypeSyncReadingData

from ..extension import media_ext


@media_ext.periodic_task()
def sync_reading_data(period_from=None, period_to=None, **kwargs):
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
        readbases = []
        readbase_map = {}
        def create_readbase(event):
            cid = event['cid']
            path = event['path']
            key_pair = (cid, path)
            readbase = event.copy()
            readbase['events'] = []
            readbase['progress'] = 0
            readbase_map[key_pair] = readbase
            readbases.append(readbase)

            result = re.match(pattern, path)

            if result:
                articlebase_id = location_rule_map[result.group(0)]
                readbase['articlebase_id'] = articlebase_id

            return readbase

        def append_readevent(readbase, event):
            readbase['events'].append(
                {
                    'datetime': event['datetime'],
                    'action': event['action'],
                    'params': event['params']
                }
            )
            if 'percentage' in event['params']:
                readbase['progress'] = max(readbase['progress'], event['params']['percentage'] / 100)

        for row in data:
            event = {
                'datetime': row[kafka_headers.DATETIME],
                'title': row[kafka_headers.TITLE],
                'uid': row[kafka_headers.USER],
                'cid': row[kafka_headers.CID],
                'path': row[kafka_headers.PATH],
                'action': row[kafka_headers.ACTION],
                'params': row[kafka_headers.PARAMS],
            }
            cid = event['cid']
            path = event['path']
            key_pair = (cid, path)

            if event['action'] != 'proceed':
                readbase = create_readbase(event) # not proceed -> new ReadBase

            elif all(key_pair) and key_pair in readbase_map: # belongs to existing ReadBase -> proceed
                readbase = readbase_map[key_pair]

            else: # is proceed but cannot find its ReadBase -> new ReadBase
                readbase = create_readbase(event)

            append_readevent(readbase, event)
            insert_to_cerem(team.id, 'readbases', readbases)


@media_ext.periodic_task()
def find_reader(*args, **kwargs):
    for team in Team.objects.all():
        pipeline = [
            {
                '$match': {
                    'clientbase_id': None
                }
            }, {
                '$lookup': {
                    'from': 'clientbases',
                    'localField': 'cid',
                    'foreignField': 'cids',
                    'as': 'clientbases'
                }
            }, {
                '$unwind': {
                    'path': '$clientbases'
                }
            }, {
                '$set': {
                    'clientbase_id': '$clientbases.id'
                }
            },
            {
                '$project': {
                    'clientbases': 0
                }
            },
            {
                '$merge':
                {
                    'into': 'readbases',
                    'on': '_id',
                    'whenMatched': 'replace',
                    'whenNotMatched': 'insert'
                }
            }
        ]
        aggregate_from_cerem(team.id, 'readbases', pipeline)
