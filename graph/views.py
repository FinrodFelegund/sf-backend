from rest_framework.views import APIView
from rest_framework.permissions import  IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from graph.serializers import GraphRequestSerializer
from rest_framework import status

from shared.webscrapping.scrapper import Scrapper
from shared.entityrecognition.ner import NERPipeline
from web.models import Website

# Create your views here.

class GraphViewSet(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=GraphRequestSerializer,
        responses=GraphRequestSerializer,
        description='Request to create a new graph object for a specific website'
    )
    def post(self, request):
        serializer = GraphRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.validated_data['msg']

        url = message['url']
        scrapper = Scrapper(message['text'])
        text = scrapper()
        website, created = Website.objects.get_or_create(url=url, content=text)
        pipe = NERPipeline(text)
        output = pipe()

        print(output)
       


        return Response(
            {
                'msg': GraphRequestSerializer(message).data
            },
            status=status.HTTP_200_OK,
        )

