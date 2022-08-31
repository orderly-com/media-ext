from importly.importers import FileImporter

from ..media_media.datahub import DataTypeArticle
from ..media_importly.importers import ArticleImporter

from ..extension import media_ext


@media_ext.datasource('文章公版')
class ArticleFileImporter(FileImporter):
    data_importer = ArticleImporter

    @staticmethod
    def get_required_headers():
        return ['文章編號']

    @staticmethod
    def get_headers_array():
        return ['文章編號', '作者', '文章標題', '文章內容', '網址', '狀態', '發布日期', 'TagA']

    def process_dataset(self):
        pass
