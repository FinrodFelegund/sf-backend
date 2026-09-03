import json
import logging

import networkx as nx
from django.db.models import Count, Prefetch
from django.http import StreamingHttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from graph.serializers import GraphQuerySerializer, GraphRequestSerializer, GraphFocusQuerySerializer
from shared.entityrecognition.ner import NERPipeline
from shared.relationextraction.relation_extraction import RelationExtraction
from shared.webscrapping.scrapper import Scrapper
from web.models import Entity, Relation, RelationType, Sentence, Website, WebsiteEntity
from web.services.service import get_or_refresh_website_with_state, tfidf_for_websites

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
        website, content_is_new = get_or_refresh_website_with_state(
            request.user, url, message['text']
        )

        already_built = Entity.objects.filter(websites=website, user=request.user).exists()

        if already_built and not content_is_new:
            return self._sse_response(self._stream_snapshot(request.user, website))

        pipe = NERPipeline(website.content)
        output = pipe()
        sents = []
        nodes = []

        sentences, entities = output['sentences'], output['entities']
        for sentence in sentences:
            sent, created = Sentence.objects.get_or_create(website=website, text=sentence['text'])
            if created:
                sent.save()
            
            sents.append(sent)


        for entity in entities.values():
            label = entity['label']
            caption = entity['caption']
            sent_idxs = entity['sent_idx']

            ent, created = Entity.objects.get_or_create(user=request.user, entity_name=caption, entity_type=label)
            if created:
                ent.save()
            
            
            ent.websites.add(website)
            for i in sent_idxs:
                ent.sentences.add(sents[i])

            nodes.append({'id': str(ent.id), 'label': ent.entity_type, 'caption': ent.entity_name})

            website_ent, created = WebsiteEntity.objects.get_or_create(
                website=website,
                entity=ent,
                defaults={'count': entity['count']}
            
            )
            if not created and website_ent.count != entity['count']:
                website_ent.count = entity['count']
                website_ent.save(update_fields=['count', 'updated_at'])

        

        extractor = RelationExtraction(user=request.user, website=website)
        return self._sse_response(self._stream_graph(request.user, website, nodes, extractor))
    
    @staticmethod
    def _sse_response(generator):
        response = StreamingHttpResponse(generator, content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    @staticmethod
    def _stream_existing(nodes, links):
        yield f'data: {json.dumps({'type': 'nodes', 'nodes': nodes})}\n\n'

        if links:
            yield f'data: {json.dumps({'type': 'links', 'links': links})}\n\n'

        scores = GraphViewSet._score_nodes(nodes, links)
        yield f'data: {json.dumps({'type': 'scores', 'scores': scores})}\n\n'
        yield 'data: [DONE]\n\n'

    @staticmethod
    def _stream_snapshot(user, website):
        nodes, links = GraphViewSet._collect_graph(user, website)
        yield f'data: {json.dumps(
            {
                'type': 'graph',
                'nodes': nodes,
                'links': links,
                'scores': GraphViewSet._score_nodes(nodes, links),
            }
        )}\n\n'

        yield 'data: [DONE]\n\n'


    @staticmethod
    def _stream_graph(user, website, nodes, extractor):
        yield f'data: {json.dumps({'type': 'nodes', 'nodes': nodes})}\n\n'

        try:
            for links in extractor.stream():
                yield f'data: {json.dumps({'type': 'links', 'links': links})}\n\n'
        except Exception as e:
            raise RuntimeError(str(e))
        
        finally:
            yield from GraphViewSet._stream_snapshot(user, website)

    @extend_schema(
        request=GraphQuerySerializer,
        description='Retrieve the graph for a website, orhte whole user graph'
    )
    def get(self, request):
        serializer = GraphQuerySerializer(data=request.query_params.dict())
        serializer.is_valid(raise_exception=True)
        url = serializer.validated_data['url'].strip()

        website = None
        if url:
            website = Website.objects.filter(url=url, user=request.user).first()
            if website is None:
                return Response({'nodes': [], 'links': [], 'scores': []})
        
        nodes, links = self._collect_graph(request.user, website)

        return Response({
            'nodes': nodes,
            'links': links,
            'scores': self._score_nodes(nodes, links)
        })

    @staticmethod
    def _collect_graph(user, website=None):
        is_global = website is None

        entities = Entity.objects.filter(user=user)
        relations = Relation.objects.filter(user=user).select_related('relation_type')

        if is_global:
            entities = (
                entities
                .annotate(website_count=Count('websites', distinct=True))
                .prefetch_related('websites')
            )
            sentence_qs = Sentence.objects.filter(website__user=user).select_related('website')
        else:
            entities = entities.filter(websites=website)
            relations = relations.filter(websites=website)
            sentence_qs = Sentence.objects.filter(website=website)

        relations = relations.distinct().prefetch_related(
            Prefetch('sentences', queryset=sentence_qs, to_attr='scoped_sentences')
        )

        nodes = []
        for ent in entities.distinct():
            node = {
                'id': str(ent.id),
                'label': ent.entity_type,
                'caption': ent.entity_name,
            }
            if is_global:
                node['website_count'] = ent.website_count
                node['websites'] = [
                    {'id': str(w.id), 'url': w.url}
                    for w in ent.websites.all()
                ]
            nodes.append(node)

        links = []
        for rel in relations:
            sentences = []
            for sentence in rel.scoped_sentences:
                item = {'id': str(sentence.id), 'text': sentence.text}
                if is_global:
                    item['website'] = sentence.website.url
                sentences.append(item)

            links.append({
                'id': str(rel.id),
                'source': str(rel.entity1_id),
                'target': str(rel.entity2_id),
                'relation_type': rel.relation_type.label if rel.relation_type else None,
                'sentences': sentences,
            })

        return nodes, links
    @staticmethod
    def _score_nodes(nodes, links):
        try:
            ranked = nx.pagerank(
                G=nx.Graph([(link['source'], link['target']) for link in links])
            ) if links else {}
        except Exception as e:
            raise RuntimeError(str(e))

        return [
            {'id': node['id'], 'score': ranked.get(node['id'], 0.0)}
            for node in nodes
        ]

class GraphFocusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[GraphFocusQuerySerializer],
        description='tf-idf weights for the entities of one or more focuesed websites'
    )

    def get(self, request):
        serializer = GraphFocusQuerySerializer(data=request.query_params.dict())
        serializer.is_valid(raise_exception=True)

        owned = list(
            Website.objects
            .filter(user=request.user, id__in=serializer.validated_data['focus_ids'])
            .values_list('id', flat=True)
        )

        return Response(
            {
                'website_ids': [str(i) for i in owned],
                'tfidf': tfidf_for_websites(request.user, owned)
            },
            status=status.HTTP_200_OK,
        )

