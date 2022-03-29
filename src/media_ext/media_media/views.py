import datetime

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView, View, TemplateView, UpdateView, CreateView
from django.shortcuts import get_object_or_404, redirect, reverse
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone, translation
from django.conf import settings

from core import views as core
from core.utils import TeamAuthPermission, ForestTimer, array_to_dict, make_datetimeStart_datetimeEnd, querydict_to_dict, sort_list_by_key, str_to_hex, bulk_create, bulk_update

from tag_assigner.models import TagAssigner, ValueTag

from team.views import TeamMixin

from .models import ArticleBase

from ..extension import media_ext

media_router = media_ext.router('media/')

@media_ext.sidebar_item('team')
class MediaList:
    name = '媒體資料'
    icon = 'icon-newspaper'

    class ArticleList:
        name = '文章列表'
        menu_name = 'articles'
        url = '/media/articlelist/'


@media_router.view('articlelist/', name='article-list')
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
            status = get_object_or_404(OrderInternalStatus, key=status)
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

        # source_list = self.team.get_datasource_family_root_group(enabled=True, data_type=[DataSource.DATA_TYPE_ORDER])
        # self.source_list = list(map(lambda x: {'uuid': str(x.uuid), 'name': x.get_name_by_localization()}, source_list))

        # # enabled_source_list
        # enabled_source_list = self.request.GET.getlist('enabled_source_list[]', [])
        # if len(enabled_source_list) == 0:
        #     self.enabled_source_list = list(map(lambda x: x['uuid'], self.source_list))
        # else:
        #     self.enabled_source_list = enabled_source_list
        self.source_list = []
        self.enabled_source_list = []

        # get status_list
        # self.status_list = OrderInternalStatus.objects.order_by('order_by').all()
        self.status_list = []
        # get status
        # enabled_status_list = self.request.GET.getlist('enabled_status_list[]', [])
        # if len(enabled_status_list) == 0:
        #     self.enabled_status_list = [OrderBase.STATUS_CONFIRMED, OrderBase.STATUS_KEEP, OrderBase.STATUS_ABANDONED]
        # else:
        #     self.enabled_status_list = enabled_status_list
        self.enabled_status_list = []
        # get product_changed
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

        self.order_type = self.request.GET.get('order_type', 'amount')

        return super().get(request, *args, **kwargs)


class OrderDetailView(
        core.LoginRequiredMixin, core.TeamRequiredMixin,
        core.SetDefaultBreadCrumbMixin, core.SetDefaultPageContent,
        core.GetGuidanceMixin,
        TeamMixin,
        TemplateView):

    template_name = 'team/orders/detail.html'

    MENU = 'team'
    SIDEBAR_MENU = 'orders'
    TAB_MENU = 'detail'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['page_title'] = f'文章資料 : {self.orderbase.external_id}'

        context['page_sub_title'] = '{}: {}'.format(
            translation.gettext('數據更新時間'),
            self.team.get_last_calculation_datetime().strftime('%Y-%m-%d'),
        )

        context['panel_title'] = f'{self.orderbase.external_id} (${self.orderbase.total_price})'

        context['datasource'] = self.datasource
        context['orderbase'] = self.orderbase
        context['records_count'] = self.orderproducts.count()

        return context

    def get(self, request, *args, **kwargs):

        uniq_id = kwargs.get('uniq_id', None)

        if uniq_id is None:
            return HttpResponseForbidden()

        # orderbase
        if self.team.has_child:
            orderbase_qs = OrderBase.objects.select_related('clientbase').filter(team__in=self.team.get_children())
        else:
            orderbase_qs = OrderBase.objects.select_related('clientbase').filter(team=self.team)

        orderbase = orderbase_qs.filter(uniq_id=uniq_id, removed=False).first()

        if orderbase is None:
            return HttpResponseForbidden()

        try:
            datasource = DataSource.objects.only('id').get(id=orderbase.datasource_id)
        except Exception:
            return HttpResponseForbidden()

        # orderproducts
        orderproducts = orderbase.orderproduct_set.select_related('productbase').order_by('productbase__internal_product', 'refound', '-append', 'c_at')

        self.datasource = datasource
        self.orderbase = orderbase
        self.orderproducts = orderproducts

        return super().get(request, *args, **kwargs)

    def remove_tag(request, *args, **kwargs):

        data = request.POST

        team = Team.objects.get(id=request.session.get('team_id', None))

        order_id = data.get('order_id', None)
        datasource_id = data.get('datasource_id', None)

        datasource = DataSource.objects.filter(uuid=datasource_id).only('id', 'name').first()

        if datasource is None:
            return JsonResponse({'result': False})

        orderbase = team.orderbase_set.filter(datasource_id=datasource.id, external_id=order_id, removed=False).only('id', 'name').first()

        if orderbase is None:
            return JsonResponse({'result': False})

        tag_id = data.get('tag_id', None)
        if tag_id is None:
            return JsonResponse({'result': False})

        try:
            tag = ValueTag.objects.get(uuid=tag_id, team_id=team.id, tag_type=ValueTag.MANUAL)
        except ValueTag.DoesNotExist:
            return JsonResponse({'result': False})

        TagAssigner.remove_tag(tag=tag, target=orderbase)

        return JsonResponse({'result': True})
