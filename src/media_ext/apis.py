import orjson

from django.http import JsonResponse
from django.conf import settings

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework import status

from external_app.models import ExternalAppApiKey
from .tasks import process_clientlist

from .media_ext.extension import media_ext


@media_ext.api('/article/')
class ImportArticleList(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):

        signature = kwargs.get('signature')
        api_key = request.headers.get('X-API-Key')

        if not any([signature, api_key]):
            return JsonResponse({'result': False, 'msg': {'title': 'Value Missing', 'text': 'Signature or api_key is missing.'}}, status=status.HTTP_400_BAD_REQUEST)

        team = ExternalAppApiKey.get_team(signature, api_key)

        if not team:
            return JsonResponse({'result': False, 'msg': {'title': 'Not Valid', 'text': 'api_key is not valid or is expired.'}}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            data = orjson.loads(request.body.decode('utf-8'))
        except:
            return JsonResponse({'result': False, 'msg': {'title': 'Data is Valid', 'text': 'Data is not valid or is not well formated.'}}, status=status.HTTP_406_NOT_ACCEPTABLE)

        if 'datasource' not in data:
            return JsonResponse({'result': False, 'msg': {'title': 'Data is Valid', 'text': 'Datasource is missing.'}}, status=status.HTTP_406_NOT_ACCEPTABLE)

        if 'data' not in data:
            return JsonResponse({'result': False, 'msg': {'title': 'Data is Valid', 'text': 'Data is missing.'}}, status=status.HTTP_406_NOT_ACCEPTABLE)

        if len(data['data']) > settings.API_BATCH_SIZE_L:
            return JsonResponse({'result': False, 'msg': {'title': 'Data is Valid', 'text': f'Max row of data per request is {settings.API_BATCH_SIZE_L}.'}}, status=status.HTTP_406_NOT_ACCEPTABLE)

        if settings.DEBUG is True:
            process_clientlist(team_slug=team.slug, data=data)
        else:
            process_clientlist.delay(team_slug=team.slug, data=data)

        return JsonResponse({'result': True, 'msg': {'title': 'OK', 'text': 'Client data is recived'}}, status=status.HTTP_200_OK)

        # {
        #   "datasource": "360388fc-9172-4288-bf1f-ca41ea4fed7f",
        #   "data": [
        #     {
        #       "id": "C9999aa",
        #       "title": "文章一",
        #       "content": "<html></html>",
        #       "attributions": [
        #         {
        #           "name": "FF",
        #           "value": "ff"
        #         },
        #         {
        #           "name": "XX",
        #           "value": "xx"
        #         }
        #       ]
        #     }
        #   ]
        # }
