import datetime

from django.conf import settings
from django.db.models import Min

from importly.importers import DataImporter
from importly.formatters import (
    Formatted, format_datetime
)

from datahub.data_flows import handle_data

from ..extension import media_ext

from ..media_media.datahub import channels
from ..media_media.models import ArticleBase, ArticleCategory, ReadBase, ReadEvent
from .models import Article, Read

class ArticleDataTransfer:
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


class ArticleImporter(DataImporter):
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

            article['location_rule'] = rf'^{article["path"]}'

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


class ReadDataTransfer:
    class ReadTransfer:
        model = Read

        title = Formatted(str, 'title')
        path = Formatted(str, 'path')
        uid = Formatted(str, 'uid')
        cid = Formatted(str, 'cid')
        proceed = Formatted(lambda at: str(at) == 'proceed', 'action')

        datetime = Formatted(format_datetime, 'datetime')

        attributions = Formatted(dict, 'attributions')


class ReadImporter(DataImporter):
    def process_raw_records(self):
        '''
            A complete read behavior (ReadBase) is built by:
            view, proceed, proceed, ... with same cid and path
            So a ReadBase is basically a view event, and its readevents are just proceed events
        '''
        period_from = self.datalist.read_set.aggregate(min_datetime=Min('datetime')).get('min_datetime')
        if period_from:
            readbases = list(
                self.team.readbase_set
                    .filter(datetime__range=[period_from - datetime.timedelta(hours=1), period_from])
                    .values('cid', 'datetime', 'id', 'path')
            )
        else:
            readbases = []

        readbases_to_create = [] # new readbases
        readbases_to_update = [] # update read_rate
        readevents_to_create = [] # new readevents
        reads_to_update = [] # update read.readbase and read.readevent

        readbase_map = {} # cid, path: readbase_dict
        for readbase_data in readbases:
            readbase = ReadBase(**readbase_data)
            readbase_map[readbase['cid', 'path']] = readbase
            readbases_to_update.append(readbase)

        def pre_create_readevent(read_data, readbase=None):
            if readbase is None:
                readbase = ReadBase(
                    team=self.team, datasource=self.datasource,
                    uid=read_data['uid'], cid=read_data['cid'],
                    datetime=read_data['datetime'], path=read_data['path']
                )
                readbase_map[readbase.cid, readbase.path] = readbase
                readbases_to_create.append(readbase)

            try:
                progress = float(read_data['attributions']['percentage']) / 100
            except:
                progress = None

            if not readbase.uid:
                readbase.uid = read_data['uid']

            readevent = ReadEvent(
                readbase=readbase,
                datetime=read_data['datetime'],
                progress=progress,
                team=self.team
            )

            if readevent.progress:
                readbase.read_rate = max(readbase.read_rate, readevent.progress)

            readevents_to_create.append(readevent)

            read = Read(
                id = read_data['id'],
                readevent=readevent,
                readbase=readbase
            )
            reads_to_update.append(read)

        for read in self.datalist.read_set.values('proceed', 'datetime', 'cid', 'path', 'attributions', 'id', 'uid').order_by('datetime'):
            cid = read['cid']
            path = read['path']
            key_pair = (cid, path)

            if read['proceed'] is False:
                pre_create_readevent(read) # not proceed -> new ReadBase

            elif all(key_pair) and key_pair in readbase_map: # belongs to existing ReadBase -> proceed
                pre_create_readevent(read, readbase_map[cid])

            else: # is proceed but cannot find its ReadBase -> new ReadBase
                pre_create_readevent(read)

        ReadBase.objects.bulk_create(readbases_to_create, batch_size=settings.BATCH_SIZE_M)
        ReadBase.objects.bulk_update(readbases_to_update, ['read_rate'], batch_size=settings.BATCH_SIZE_M)

        ReadEvent.objects.bulk_create(readevents_to_create, batch_size=settings.BATCH_SIZE_M)

        for read in reads_to_update:
            read.readbase_id = read.readbase.id
            read.readevent_id = read.readevent.id

        Read.objects.bulk_update(reads_to_update, ['readbase_id', 'readevent_id'], batch_size=settings.BATCH_SIZE_M)
