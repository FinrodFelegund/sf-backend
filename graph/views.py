from rest_framework.views import APIView
from rest_framework.permissions import  IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import extend_schema
from graph.serializers import GraphRequestSerializer, GraphResponseSerializer

from django.http import StreamingHttpResponse

from shared.webscrapping.scrapper import Scrapper
from shared.entityrecognition.ner import NERPipeline
from shared.relationextraction.relation_extraction import RelationExtraction
from web.models import Website, Sentence, Entity, WebsiteEntity, Relation, RelationType
from django.db.models import Prefetch

import json
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

            nodes.append({'id': str(ent.id), 'label': ent.entity_type, 'caption': ent.entity_name})

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
                yield f'data: {json.dumps({'type': 'links', 'links': links})}\n\n'

        except Exception as e:
            raise RuntimeError(str(e))
        
        finally:
            yield 'data: [DONE]\n\n'

    @extend_schema(
        request=GraphRequestSerializer,
        description='Retrieve a graph for the given website, if it exsits'
    )
    def get(self, request):
        print(request.query_params.dict())
        serializer = GraphRequestSerializer(data=request.query_params.dict())
        serializer.is_valid(raise_exception=True)
        msg = serializer.validated_data['msg']
        url = msg['url']
        
        
        try:
            website = Website.objects.get(url=url, user=request.user)
        except Website.DoesNotExist:
            return Response({'nodes': [], 'links': []})
        
        nodes = [
            {
                'id': str(ent.id),
                'label': ent.entity_type,
                'caption': ent.entity_name
             }
            for ent in Entity.objects.filter(websites=website, user=request.user)
        ]

        website_sentences = Sentence.objects.filter(website=website)
        relations = (
            Relation.objects
            .filter(user=request.user, sentences__website=website)
            .distinct()
            .select_related('relation_type', 'entity1', 'entity2')
            .prefetch_related(Prefetch('sentences', queryset=website_sentences, to_attr='website_sentences'))
        )

        links = [
            {
                'source': str(rel.entity1.id),
                'target': str(rel.entity2.id),
                'relation_type': rel.relation_type.label,
                'sentences': [
                    {
                        'id': (str(s.id)), 'text': s.text
                    }
                    for s in rel.website_sentences
                ]
            }
            for rel in relations
        ]

        return Response({'nodes': nodes, 'links': links})
