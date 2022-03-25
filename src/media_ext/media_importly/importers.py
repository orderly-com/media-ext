from django.conf import settings

from importly.importers import DataImporter
from importly.formatters import (
    Formatted, format_datetime
)

from ..media_media.models import ArticleBase, ArticleCategory
from .models import Article

class ArticleDataTransfer:
    class ArticleTransfer:
        model = Article

        external_id = Formatted(str, 'id')

        author = Formatted(str, 'author')
        title = Formatted(str, 'title')
        content = Formatted(str, 'content')

        # status = Formatted(str, 'status')

        datetime = Formatted(format_datetime, 'datetime')

        attributions = Formatted(dict, 'attributions')

        categories = Formatted(list, 'categories')


class ArticleImporter(DataImporter):
    def process_raw_records(self):
        articlebases_to_create = []
        articlebases_to_update = set()
        articlebase_map = {}

        article_reverse_link_map = {}

        for articlebase in self.team.articlebase_set.values('id', 'external_id'):
            articlebase_map[articlebase['external_id']] = ArticleBase(id=articlebase['id'])

        for article in self.datalist.article_set.values(
            'id', 'external_id', 'title',
            'content', 'attributions', 'datetime', 'author'
        ):
            if article['external_id'] in articlebase_map:
                articlebase = articlebase_map.get(article['external_id'])
                articlebases_to_update.add(articlebase)

            else:
                articlebase = ArticleBase(external_id=article['external_id'])
                articlebases_to_create.append(articlebase)

            articlebase.title = article['title']
            articlebase.content = article['content']
            articlebase.attributions = article['attributions']
            articlebase.datetime = article['datetime']
            articlebase.author = article['author']

            article_reverse_link_map[article['id']] = articlebase

        ArticleBase.objects.bulk_create(articlebases_to_create, batch_size=settings.BATCH_SIZE_M)
        update_fields = ['title', 'content', 'attributions', 'datetime', 'author']
        ArticleBase.objects.bulk_update(articlebases_to_update, update_fields, batch_size=settings.BATCH_SIZE_M)

        articles_to_create = [
            Article(
                id=article_id, articlebase_id=articlebase.id
            ) for article_id, articlebase in article_reverse_link_map
        ]

        Article.objects.bulk_update(articles_to_create, ['articlebase_id'], batch_size=settings.BATCH_SIZE_M)

        Through = ArticleBase.categories.through
        article_category_links_to_create = []
        for article in self.datalist.article_set.values('id', 'categories'):
            for category in article['categories']:
                article_category_links_to_create.append(
                    Through(article_id=article['id'], articlecategory_id=category)
                )

        Through.objects.bulk_create(article_category_links_to_create, batch_size=settings.BATCH_SIZE_M, ignore_conflicts=True)
