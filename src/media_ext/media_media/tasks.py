import json
import re
import gc
import datetime

from django.conf import settings
from django.utils import timezone
from config.celery import app

from cerem.tasks import fetch_site_tracking_data
from cerem.utils import kafka_headers

from datahub.models import DataSync
from team.models import Team
from tag_assigner.models import TagAssigner, ValueTag

from core.utils import run

from cerem.tasks import insert_to_cerem, aggregate_from_cerem

from .datahub import DataTypeSyncReadingData
from .models import MediaInfo, ArticleBase

from ..extension import media_ext

def reading_score(item):
    return item['article_count']


def sync_media_info(team):
    existing_ids = set(MediaInfo.objects.filter(clientbase__team_id=team.id).values_list('clientbase_id', flat=True))
    all_ids = set(team.clientbase_set.filter(removed=False).values_list('id', flat=True))
    ids_to_add_info = all_ids - existing_ids
    info_objects_to_create = [MediaInfo(clientbase_id=client_id) for client_id in ids_to_add_info]
    MediaInfo.objects.bulk_create(info_objects_to_create, batch_size=settings.BATCH_SIZE_M)

    info_qs = MediaInfo.objects.filter(clientbase__team_id=team.id)

    info_map = {}
    for info_id, client_id in MediaInfo.objects.values_list('id', 'clientbase_id'):
        info_map[client_id] = info_id

    info_objects_to_update = []
    pipeline = [
        {
            '$match': {
                'clientbase_id': {
                    '$ne': None
                },
                'articlebase_id': {
                    '$ne': None
                }
            }
        }, {
            '$group': {
                '_id': '$clientbase_id',
                'articles': {
                    '$addToSet': '$articlebase_id'
                },
                'avg_progress': {
                    '$avg': '$progress'
                },
                'last_read_datetime': {
                    '$max': '$datetime'
                },
            }
        }, {
            '$project': {
                '_id': 1,
                'avg_progress': 1,
                'article_count': {'$size': '$articles'},
                'last_read_datetime': 1
            }
        }
    ]
    result = sorted(aggregate_from_cerem(team.id, 'readbases', pipeline), key=reading_score, reverse=True)
    for i, item in enumerate(result):

        client_id = item['_id']
        article_count = item['article_count']
        avg_progress = item['avg_progress']
        last_read_datetime = item['last_read_datetime']
        if client_id not in info_map:
            continue
        info = MediaInfo(
            id=info_map[client_id],
            reading_rank=i+1,
            article_count=article_count,
            avg_reading_progress=avg_progress,
            last_read_datetime=last_read_datetime
        )
        info_objects_to_update.append(info)
    update_fields = ['article_count', 'avg_reading_progress', 'reading_rank', 'last_read_datetime']
    MediaInfo.objects.bulk_update(info_objects_to_update, update_fields, batch_size=settings.BATCH_SIZE_M)


def sync_article_reading_data(team):
    pipeline = [
        {
            '$match': {
                'articlebase_id': {
                    '$ne': None
                }
            }
        }, {
            '$group': {
                '_id': '$articlebase_id',
                'articles': {
                    '$addToSet': '$clientbase_id'
                },
                'user_read_count': {
                    '$sum': 1
                }
            }
        }, {
            '$project': {
                '_id': 1,
                'client_read_count': {'$size': '$articles'},
                'user_read_count': 1,
            }
        }
    ]
    articlebases_to_update = []
    articlebase_ids = list(team.articlebase_set.values_list('id', flat=True))
    for item in aggregate_from_cerem(team.id, 'readbases', pipeline):
        if item['_id'] in articlebase_ids:
            articlebases_to_update.append(
                ArticleBase(
                    id=item['_id'],
                    clientbase_read_count=item['client_read_count'],
                    user_read_count=item['user_read_count']
                )
            )
    update_fields = ['clientbase_read_count', 'user_read_count']
    team.articlebase_set.bulk_update(articlebases_to_update, update_fields, batch_size=settings.BATCH_SIZE_M)


@media_ext.periodic_task()
def sync_reading_data(period_from=None, period_to=None, sync_info_model=True, sync_articles=True, **kwargs):
    for team in Team.objects.all():
        articlebases = list(
            team.articlebase_set.filter(removed=False, location_rule__isnull=False).exclude(location_rule='').values('id', 'location_rule')
        )
        pattern = ''

        location_rule_map = {}
        location_rules = []
        for articlebase in articlebases:
            location_rule_map[articlebase['location_rule']] = articlebase['id']
            location_rules.append(articlebase['location_rule'])

        pattern = '|'.join(location_rules)
        if pattern:

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

            readbases = []
            readbase_map = {}
            def create_readbase(event):
                cid = event['cid']
                path = event['path']
                key_pair = (cid, path)
                try:
                    event['params'] = json.loads(event['params'])
                except:
                    event['params'] = {}
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
                try:
                    event['params'] = json.loads(event['params'])
                except:
                    event['params'] = {}

                readbase['events'].append(
                    {
                        'datetime': event['datetime'],
                        'action': event['action'],
                        'params': event['params']
                    }
                )
                if 'percentage' in event['params']:
                    readbase['progress'] = max(readbase['progress'], event['params']['percentage'] / 100)

            for row in fetch_site_tracking_data(team, **params):
                event = {
                    'datetime': row[kafka_headers.DATETIME],
                    'title': row[kafka_headers.TITLE],
                    'uid': row[kafka_headers.USER],
                    'cid': row[kafka_headers.CID],
                    'path': row[kafka_headers.PATH],
                    'action': row[kafka_headers.ACTION],
                    'params': row[kafka_headers.PARAMS],
                    'target': row[kafka_headers.TARGET],
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
        if sync_info_model:
            sync_media_info(team)
        if sync_articles:
            sync_article_reading_data(team)

@media_ext.periodic_task()
def find_reader(*args, **kwargs):
    for team in Team.objects.all():
        now = timezone.now()
        pipeline = [
            {
                '$match': {
                    'clientbase_id': None,
                    'datetime': {
                        '$gte': now - datetime.timedelta(days=3)
                    }
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
