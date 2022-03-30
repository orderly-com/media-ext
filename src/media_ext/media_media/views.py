import datetime
import urllib

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView, View, TemplateView, UpdateView, CreateView
from django.shortcuts import get_object_or_404, redirect, reverse
from django.db.models import Count, Max, Q, F, Sum, Value
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone, translation
from django.conf import settings

from core import views as core
from core.utils import TeamAuthPermission, ForestTimer, array_to_dict, make_datetimeStart_datetimeEnd, querydict_to_dict, sort_list_by_key, str_to_hex, bulk_create, bulk_update

from team.views import TeamMixin

from .models import ArticleBase

from ..extension import media_ext

media_router = media_ext.router('media/', name='media')

@media_ext.sidebar_item('team')
class MediaList:
    name = '媒體資料'
    icon = 'icon-newspaper'

    class ArticleList:
        name = '文章列表'
        menu_name = 'articles'
        url = '/media/articles/'


@media_router.view('articles/', name='articles')
class ArticleListView(
        core.LoginRequiredMixin, core.TeamRequiredMixin,
        core.SetDefaultBreadCrumbMixin, core.SetDefaultPageContent,
        core.GetGuidanceMixin,
        core.CheckTeamAuthPermissionRequiredMixin,
        TeamMixin,
        ListView):

    model = ArticleBase
    context_object_name = 'articlebases'
    template_name = 'team/articles/list.html'
    team_auth_permission = TeamAuthPermission.ORDER_LIST_VIEW

    MENU = 'team'
    SIDEBAR_MENU = 'articles'

    def get_queryset(self):

        qs = super().get_queryset()

        date_start, date_end, diff_days = make_datetimeStart_datetimeEnd(
            self.date_start,
            self.date_end,
            None
        )
        qs = qs.filter(removed=False, datetime__range=[date_start, date_end])

        if self.search_keys != '':

            search_keys = urllib.parse.unquote(self.search_keys)

            if len(search_keys) > 50:  # limit to len 50
                search_keys = ''

            search_keys = search_keys.replace('，', ',').replace(' , ', ',').replace(', ', ',').replace(' ,', ',')  # replace space

            search_keys = search_keys.split(',')
            search_keys = [key for key in search_keys if key]
            conditions = Q()
            for word in search_keys:
                conditions = conditions | Q(external_id__icontains=word)

            qs = qs.filter(conditions)

        if self.enabled_status_list:
            qs = qs.filter(status__in=self.enabled_status_list)

        if self.article_type == 'author':
            order_by = '-author'
        elif self.article_type == 'datetime':
            order_by = '-datetime'
        else:
            order_by = '-datetime'

        qs = qs.order_by(order_by, '-id')

        self.articlebase_count = qs.count()


        page = self.request.GET.get('page', 1)
        paginator = Paginator(qs, settings.PAGE_SIZE_SM)
        try:
            qs = paginator.page(page)
        except PageNotAnInteger:
            qs = paginator.page(1)
        except EmptyPage:
            qs = paginator.page(paginator.num_pages)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status = self.request.GET.get('status', '')
        source_uuid = self.request.GET.get('source', '')

        if source_uuid != '':
            ds = get_object_or_404(DataSource, uuid=source_uuid)
            context['panel_title'] = '文章列表: ' + ds.localization['zh_tw']
        elif status != '':
            status = get_object_or_404(articleInternalStatus, key=status)
            context['panel_title'] = '文章列表: ' + status.localization['zh_tw']
        else:
            context['panel_title'] = '文章列表'

        context['page_title'] = '文章列表'

        context['page_sub_title'] = '{}: {}'.format(
            translation.gettext('數據更新時間'),
            self.team.get_last_calculation_datetime().strftime('%Y-%m-%d'),
        )

        context['articlebase_count'] = self.articlebase_count

        # status
        context['status_list'] = self.status_list
        context['enabled_status_list'] = self.enabled_status_list

        # product_changed
        context['product_changed'] = self.product_changed

        # source
        context['source_list'] = self.source_list
        context['enabled_source_list'] = self.enabled_source_list

        # date_start & date_end
        context['date_start'] = self.date_start
        context['date_end'] = self.date_end

        # search_keys
        context['search_keys'] = self.search_keys

        # context['IS_CAN_EDIT_DATA'] = self.team.is_can_edit_data(self.request.user)

        return context

    def get(self, request, *args, **kwargs):

        self.source_list = self.team.datasource_set.all()
        self.enabled_source_list = self.request.GET.getlist('enabled_source_list[]', [])
        self.article_type = self.request.GET.get('article_type', 'datetime')
        self.status_list = [
            {
                'key': choice[0],
                'name': choice[1]
            } for choice in ArticleBase.STATE_CHOICES
        ]

        self.enabled_status_list = self.request.GET.getlist('enabled_status_list[]', [])

        search_keys = self.request.GET.get('search_keys', '')
        self.search_keys = search_keys.strip()

        product_changed = self.request.GET.get('product_changed', 0)
        try:
            self.product_changed = int(product_changed)
        except Exception:
            self.product_changed = 0

        # date_start
        date_start = self.request.GET.get('date_start', '')
        if date_start == '':
            self.date_start = (timezone.now() - datetime.timedelta(days=179)).strftime('%Y-%m-%d')
        else:
            self.date_start = date_start

        # date_end
        date_end = self.request.GET.get('date_end', '')
        if date_end == '':
            self.date_end = timezone.now().strftime('%Y-%m-%d')
        else:
            self.date_end = date_end

        # search_keys
        search_keys = self.request.GET.get('search_keys', '')
        self.search_keys = search_keys.replace(' ', '')

        self.article_type = self.request.GET.get('article_type', 'amount')

        return super().get(request, *args, **kwargs)


@media_router.view('articles/<uuid>/', name='article-detail')
class ArticleDetailView(
        core.LoginRequiredMixin, core.TeamRequiredMixin,
        core.SetDefaultBreadCrumbMixin, core.SetDefaultPageContent,
        core.GetGuidanceMixin,
        TeamMixin,
        TemplateView):

    template_name = 'team/articles/detail.html'

    MENU = 'team'
    SIDEBAR_MENU = 'articles'
    TAB_MENU = 'detail'
    team_auth_permission = TeamAuthPermission.ORDER_LIST_VIEW

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['page_title'] = f'文章資料 : {self.articlebase.external_id}'

        context['page_sub_title'] = '{}: {}'.format(
            translation.gettext('數據更新時間'),
            self.team.get_last_calculation_datetime().strftime('%Y-%m-%d'),
        )

        context['panel_title'] = f'{self.articlebase.external_id} ({self.articlebase.get_pure_text_count()} 字)'

        context['datasource'] = self.datasource
        context['articlebase'] = self.articlebase
        context['records_count'] = self.readbases.count()

        return context

    def get(self, request, *args, **kwargs):

        uuid = kwargs.get('uuid', None)

        if uuid is None:
            return HttpResponseForbidden()

        articlebase = self.team.articlebase_set.filter(uuid=uuid, removed=False).first()

        if articlebase is None:
            return HttpResponseForbidden()

        self.datasource = articlebase.datasource
        self.articlebase = articlebase
        self.readbases = articlebase.readbase_set.filter(removed=False)

        return super().get(request, *args, **kwargs)


@media_router.view('articles/<uuid>/records/', name='article-records')
class ArticleDetailRecordsView(
        core.LoginRequiredMixin, core.TeamRequiredMixin,
        core.SetDefaultBreadCrumbMixin, core.SetDefaultPageContent,
        core.GetGuidanceMixin,
        TeamMixin,
        TemplateView):

    template_name = 'team/articles/records.html'

    MENU = 'team'
    SIDEBAR_MENU = 'articles'
    TAB_MENU = 'records'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['page_title'] = f'文章資料 : {self.articlebase.external_id}'

        context['page_sub_title'] = '{}: {}'.format(
            translation.gettext('數據更新時間'),
            self.team.get_last_calculation_datetime().strftime('%Y-%m-%d'),
        )

        context['panel_title'] = f'{self.articlebase.external_id} ({self.articlebase.get_pure_text_count()} 字)'

        context['articlebase'] = self.articlebase
        context['readbases'] = self.readbases
        context['records_count'] = self.readbases.count()

        return context

    def get(self, request, uuid, *args, **kwargs):

        articlebase = self.team.articlebase_set.filter(uuid=uuid).first()

        if articlebase is None:
            return HttpResponseForbidden()

        # readbases
        readbases = articlebase.readbase_set.order_by('datetime')

        self.articlebase = articlebase
        self.readbases = readbases

        return super().get(request, *args, **kwargs)

