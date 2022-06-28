from typing import Any, Tuple

from django.db.models.query import Q
from django.db.models import QuerySet, Count, Avg, F

from filtration.conditions import Condition, RangeCondition, DateRangeCondition, SelectCondition, ChoiceCondition
from filtration.models import condition
from filtration.exceptions import UseIdList

from tag_assigner.models import ValueTag

from cerem.tasks import aggregate_from_cerem


@condition
class ArticleCount(RangeCondition):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.range(0, 20)
        self.config(postfix='篇')

    def filter(self, client_qs: QuerySet, article_count_range: Any) -> Tuple[QuerySet, Q]:
        val_min, val_max = article_count_range
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
                }
            }, {
                '$addFields': {
                    'article_count': {
                        '$size': '$articles'
                    }
                }
            }, {
                '$match': {
                    'article_count': {
                        '$gte': val_min,
                        '$lte': val_max
                    }
                }
            }, {
                '$project': {
                    '_id': 1,
                }
            }
        ]
        result = aggregate_from_cerem(self.team.id, 'readbases', pipeline)
        id_list = set([item['_id'] for item in result])

        if val_min == 0: # find clients having no records
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
                        '_id': None,
                        'clients': {
                            '$addToSet': '$clientbase_id'
                        },
                    }
                }
            ]
            result = aggregate_from_cerem(self.team.id, 'readbases', pipeline)
            no_record_ids = result[0]['clients']
            original_pool = set(client_qs.values_list('id', flat=True))
            id_list = id_list.union(original_pool) - set(no_record_ids)

        raise UseIdList(id_list)


@condition
class AverageReadPercentage(RangeCondition):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.range(0, 100)
        self.config(postfix='%')

    def filter(self, client_qs: QuerySet, avg_read_percentage_range: Any) -> Tuple[QuerySet, Q]:
        val_min, val_max = avg_read_percentage_range
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
                    'avg_progress': {
                        '$avg': '$progress'
                    },
                }
            }, {
                '$match': {
                    'avg_progress': {
                        '$gte': val_min,
                        '$lte': val_max
                    }
                }
            }, {
                '$project': {
                    '_id': 1,
                }
            }
        ]
        result = aggregate_from_cerem(self.team.id, 'readbases', pipeline)
        id_list = [item['_id'] for item in result]

        if val_min == 0: # find clients having no records
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
                        '_id': None,
                        'clients': {
                            '$addToSet': '$clientbase_id'
                        },
                    }
                }
            ]
            result = aggregate_from_cerem(self.team.id, 'readbases', pipeline)
            no_record_ids = result[0]['clients']
            original_pool = set(client_qs.values_list('id', flat=True))
            id_list = id_list.union(original_pool) - set(no_record_ids)

        raise UseIdList(id_list)


@condition
class ArticleTagCondition(SelectCondition):
    def filter(self, client_qs: QuerySet, choices: Any) -> Tuple[QuerySet, Q]:

        q = Q(value_tag_ids__contains=choices)

        return client_qs, q

    def real_time_init(self, team, *args, **kwargs):
        articles = list(team.articlebase_set.values_list('value_tag_ids', flat=True))
        value_tag_ids = []
        for article_tag_ids in articles:
            value_tag_ids += article_tag_ids
        data = list(ValueTag.objects.filter(id__in=value_tag_ids).values('id', text=F('name')))

        self.choice(*data)
