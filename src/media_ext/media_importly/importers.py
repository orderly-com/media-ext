import datetime
from dateutil import parser

from django.conf import settings
from django.db.models import Min

from importly.importers import DataImporter
from importly.formatters import (
    Formatted, format_datetime
)

from datahub.data_flows import handle_data

from ..media_media.datahub import channels, DataTypeArticle, DataTypeRead
from ..media_media.models import ArticleBase, ArticleCategory

from .formatters import format_dict
from .models import Article


class ArticleImporter(DataImporter):

    data_type = DataTypeArticle

    class DataTransfer:
        class ArticleTransfer:
            model = Article

            external_id = Formatted(str, 'id')

            author = Formatted(str, 'author')
            title = Formatted(str, 'title')
            content = Formatted(str, 'content')
            path = Formatted(str, 'path')

            status = Formatted(str, 'status')

            datetime = Formatted(format_datetime, 'datetime')

            attributions = Formatted(dict, 'attributions')

            categories = Formatted(list, 'categories')

    def process_raw_records(self):
        articlebases_to_create = []
        articlebases_to_update = set()
        articlebase_map = {}

        article_reverse_link_map = {}

        for articlebase in self.team.articlebase_set.values('id', 'external_id'):
            articlebase_map[articlebase['external_id']] = ArticleBase(id=articlebase['id'])

        for article in self.datalist.article_set.values(
            'id', 'external_id', 'title', 'path',
            'content', 'attributions', 'datetime', 'author', 'status'
        ):
            if article['external_id'] in articlebase_map:
                articlebase = articlebase_map.get(article['external_id'])
                articlebases_to_update.add(articlebase)

            else:
                articlebase = ArticleBase(external_id=article['external_id'], team=self.team, datasource=self.datasource)
                articlebases_to_create.append(articlebase)

            article['location_rule'] = article['path']

            article = handle_data(article, channels.ARTICLE_TO_ARTICLEBASE)

            articlebase.title = article['title']
            articlebase.content = article['content']
            articlebase.attributions = article['attributions']
            articlebase.datetime = article['datetime']
            articlebase.author = article['author']
            articlebase.status = article['status']
            articlebase.path = article['path']
            articlebase.location_rule = article['location_rule']

            article_reverse_link_map[article['id']] = articlebase

        ArticleBase.objects.bulk_create(articlebases_to_create, batch_size=settings.BATCH_SIZE_M)
        update_fields = ['title', 'content', 'attributions', 'datetime', 'author', 'status', 'path', 'location_rule']
        ArticleBase.objects.bulk_update(articlebases_to_update, update_fields, batch_size=settings.BATCH_SIZE_M)

        articles_to_create = [
            Article(
                id=articlebase_id, articlebase_id=articlebase.id
            ) for articlebase_id, articlebase in article_reverse_link_map.items()
        ]

        Article.objects.bulk_update(articles_to_create, ['articlebase_id'], batch_size=settings.BATCH_SIZE_M)

        category_map = {}
        for category in self.team.articlecategory_set.values('id', 'name', 'external_id'):
            category_map[category['external_id']] = ArticleCategory(id=category['id'], name=category['name'])

        for article in self.datalist.article_set.only('articlebase', 'categories'):
            for category in article.categories:
                article_category, created = self.team.articlecategory_set.get_or_create(external_id=category['id'])
                if article_category.name != category['name']:
                    article_category.name = category['name']
                    article_category.save(update_fields=['name'])

                article.articlebase.categories.add(article_category)
