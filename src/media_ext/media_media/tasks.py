from cerem.tasks import fetch_site_tracking_data

from datahub.models import DataSync
from team.models import Team

from ..media_importly.importers import ReadImporter, ReadDataTransfer

from .datahub import data_types
from ..extension import media_ext


@media_ext.periodic_task()
def sync_reading_data(team_id, *args, **kwargs):
    params = {}
    team = Team.objects.get(id=team_id)
    datasource = team.datasource_set.get_or_create(name='system')
    last_sync = team.datasync_set.filter(data_type=data_types.SYNC_READING_DATA).order_by('-datetime').first()
    if last_sync:
        params['from_datetime'] = last_sync.datetime

    datasync = DataSync.generate_next_object(team, data_type=data_types.SYNC_READING_DATA)
    params['to_datetime'] = datasync.datetime

    data = fetch_site_tracking_data(team, **params)

    importer = ReadImporter(team, datasource)

    importer.create_datalist(data)

    importer.data_to_raw_records(ReadDataTransfer)

    importer.process_raw_records()
