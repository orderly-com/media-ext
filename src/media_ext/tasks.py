from cerem.tasks import fetch_tracking_data

from .extension import media_ext

@media_ext.calculation_function()
def sync_reading_data(*args, **kwargs):
    data = fetch_tracking_data()
    pass
