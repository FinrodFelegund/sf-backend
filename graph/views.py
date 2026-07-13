from rest_framework.views import APIView
from rest_framework.permissions import  IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from graph.serializers import GraphRequestSerializer, GraphResponseSerializer

from django.http import StreamingHttpResponse

from shared.webscrapping.scrapper import Scrapper
from shared.entityrecognition.ner import NERPipeline
from shared.relationextraction.relation_extraction import RelationExtraction
from web.models import Website, Sentence, Entity, WebsiteEntity, Relation, RelationType

import json
# Create your views here.

class GraphViewSet(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=GraphRequestSerializer,
        responses=GraphRequestSerializer,
        description='Request to create a new graph object for a specific website'
    )


    def _extract_from_text(self):
        pass

    def __extract_from_db(self):
        pass

    def post(self, request):
        serializer = GraphRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.validated_data['msg']


        url = message['url']
        scrapper = Scrapper(message['text'])
        text = scrapper()
        website, created = Website.objects.get_or_create(url=url, user=request.user)
        pipe = NERPipeline(text)
        output = pipe()
        sents = []
        nodes = []

        sentences, entities = output['sentences'], output['entities']
        for sentence in sentences:
            index = sentence['index']
            tokens = sentence['tokens']
            text = sentence['text']
            sent, created = Sentence.objects.get_or_create(website=website, text=text)
            if created:
                sent.save()
            
            sents.append(sent)


        for _, entity in entities.items():
            label = entity['label']
            caption = entity['caption']
            count = entity['count']
            sent_idxs = entity['sent_idx']

            ent, created = Entity.objects.get_or_create(user=request.user, entity_name=caption, entity_type=label)
            if created:
                ent.save()
            
            
            ent.websites.add(website)
            for i in sent_idxs:
                sent = sents[i]
                ent.sentences.add(sent)

            nodes.append({'id': ent.id, 'label': ent.entity_type, 'caption': ent.entity_name})

            website_ent, created = WebsiteEntity.objects.get_or_create(website=website, entity=ent)
            if created:
                website_ent.save()

        extractor = RelationExtraction(user=request.user, website=website)
        response = StreamingHttpResponse(
            self._stream_graph(nodes, extractor),
            content_type='text/event-stream'
        )

        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
    
    @staticmethod
    def _stream_graph(nodes, extractor):
        yield f'data: {json.dumps({'type': 'nodes', 'nodes': nodes})}\n\n'

        try:
            for links in extractor.stream():
                yield f'data: {json.dumps({'type': 'links', 'links': links})}'

        except Exception as e:
            yield f'data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n'
        
        finally:
            yield 'data: [DONE]\n\n'
