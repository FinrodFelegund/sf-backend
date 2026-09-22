import math
from collections import defaultdict

from django.db import DataError, IntegrityError, transaction
from django.db.models import Count, Q, QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from web.models import (
    Entity,
    Origin,
    Relation,
    RelationType,
    Sentence,
    Website,
    WebsiteEntity,
)
from web.serializers import (
    EntityDetailSerializer,
    EntitySerializer,
    MergeEntitySerializer,
    RelationSerializer,
    SiteEntitySerializer,
    WebsiteSerializer,
)

# Create your views here.

_DETAIL_SENTENCES_PER_SOURCE = 3

class WebsiteViewSet(ReadOnlyModelViewSet):
    serializer_class = WebsiteSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return (
            Website.objects
            .filter(user=self.request.user)
            .annotate(entity_count=Count('entities', distinct=True))
            .order_by('updated_at')
        )

    @extend_schema(responses=WebsiteSerializer(many=True))
    def list(self, request, *args, **kwargs):
        return Response([
            {
                'id': str(site.id),
                'url': site.url,
                'title': site.title,
                'entity_count': site.entity_count,
                'updated_at': site.updated_at,
            }
            for site in self.get_queryset()
        ])

    @extend_schema(responses=None)
    def destroy(self, request, *args, **kwargs):
        website = self.get_object()
        website_id = str(website.id)

        entity_ids = set(
            WebsiteEntity.objects
            .filter(website=website)
            .values_list('entity_id', flat=True)
        )

        relation_ids = set(
            Relation.objects
            .filter(user=request.user, websites=website)
            .values_list('id', flat=True)
        )

        with transaction.atomic():
            website.delete()

            orphan_relations = list(
                Relation.objects
                .filter(user=request.user, id__in=relation_ids)
                .annotate(site_count=Count('websites', distinct=True))
                .filter(site_count=0)
                .values_list('id', flat=True)
            )

            Relation.objects.filter(id__in=orphan_relations).delete()

            removed_entities = 0
            candidates = set(entity_ids)
            while candidates:
                orphans = list(
                    Entity.objects
                    .filter(user=request.user, id__in=candidates)
                    .annotate(
                        site_count=Count('websites', distinct=True),
                        alias_count=Count('aliases', distinct=True),
                    )
                    .filter(site_count=0, alias_count=0)
                    .values_list('id', flat=True)
                )

                if not orphans:
                    break
                Entity.objects.filter(id__in=orphans).delete()
                removed_entities += len(orphans)
                candidates -= set(orphans)

        return Response(
            {
                'website': website_id,
                'entities_removed': removed_entities,
                'relations_removed': len(orphan_relations)
            },
            status=status.HTTP_200_OK,
        )

def relation_payload(relation):
    return {
        'id': str(relation.id),
        'source': str(relation.entity1_id),
        'target': str(relation.entity2_id),
        'relation_type': relation.relation_type.label if relation.relation_type else None,
        'sentences': [{'id': str(s.id), 'text': s.text} for s in relation.sentences.all()],
    }


class EntityViewSet(GenericViewSet):
    serializer_class = SiteEntitySerializer
    permission_classes = (IsAuthenticated,)


    def get_queryset(self):
        return Entity.objects.filter(user=self.request.user).canonical()
    
    def create(self, request, *args, **kwargs):

        serializer = SiteEntitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entity = serializer.validated_data['node']
        website = serializer.validated_data['website']

        website = Website.objects.filter(user=request.user, url=website['url']).first()
        if website is None:
            return Response(
                {'detail': 'Unknown website for this user'},
                status=status.HTTP_404_NOT_FOUND,
            )

        entity, created = Entity.objects.get_or_create(
            user=request.user, 
            entity_name=entity['caption'],
            entity_type=entity['label'],
        )


        WebsiteEntity.objects.get_or_create(
                website=website,
                entity=entity,
                defaults={'origin': Origin.MANUAL}
            )

        matching = Sentence.objects.filter(
            website=website,
            text__icontains=f' {entity.entity_name} ',
        )

        entity.sentences.add(*matching)

        return Response(
            {'id': entity.id, 'caption': entity.entity_name, 'label': entity.entity_type},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
        
    def partial_update(self, request, *args, **kwargs):
        entity = self.get_object()
        serializer = EntitySerializer(entity, request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if 'caption' in data:
            entity.entity_name = data['caption']
        
        if 'label' in data:
            entity.entity_type = data['label']

        try:
            entity.save()
        except IntegrityError:
            return Response(
                {'detail': 'An entity with this name and type already exists'},
                status=status.HTTP_409_CONFLICT,
            )
        except DataError:
            return Response(
                {
                    'detail': 'Caption or type is too long',
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({'id': entity.id, 'caption': entity.entity_name, 'label': entity.entity_type},)

    def destroy(self, request, *args, **kwargs):
        entity = self.get_object()
        url = request.query_params.get('url', '').strip()

        if not url:
            return Response(
                {'detail': 'url is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        website = Website.objects.filter(user=request.user, url=url).first()
        if website is None:
            return Response(
                {'detail': 'Unknow website for this user'},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        site_sentences = Sentence.objects.filter(website=website)
        WebsiteEntity.objects.filter(website=website, entity=entity).delete()
        entity.sentences.remove(*site_sentences)

        removed_relations = []
        relations = (
            Relation.objects
                .filter(user=request.user, websites=website)
                .filter(Q(entity1=entity) | Q(entity2=entity))
        )

        for relation in relations:
            relation.websites.remove(website)
            relation.sentences.remove(*site_sentences)
            removed_relations.append(str(relation.id))

            if not relation.websites.exists():
                relation.delete()
        
        entity_id = str(entity.id)
        if not entity.websites.exists():
            entity.delete()

        return Response(
            {'entity': entity_id, 'relations': removed_relations},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['post'], url_path='merge')
    def merge(self, request):
        serializer = MergeEntitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source_id = serializer.validated_data['source_id']
        target_id = serializer.validated_data['target_id']

        by_id = {
            entity.id: entity
            for entity in Entity.objects.filter(user=request.user, id__in=[source_id, target_id])
        }
        source, target = by_id.get(source_id), by_id.get(target_id)

        target = target.resolve()

        if source.id == target.id:
            return Response(
                {'detail': 'source and target must be distinct'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if source is None or target is None:
            return Response(
                {'detail': 'source and target not found or not owned by user'},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        removed_relations = []
        updated_relations = []
        relations = (
            Relation.objects
                .filter(user=request.user)
                .filter(Q(entity1=source) | Q(entity2=source))
        )

        with transaction.atomic():
            for relation in relations:
                other = relation.entity2 if relation.entity1_id == source.id else relation.entity1

                if other.id == target.id:
                    removed_relations.append(relation_payload(relation))
                    relation.delete()
                    continue

                duplicate = (
                    Relation.objects
                        .filter(user=request.user, relation_type=relation.relation_type) #all relations of the user with the relation type
                        .filter(Q(entity1=target, entity2=other) | Q(entity1=other, entity2=target))
                        .exclude(id=relation.id)
                        .first()
                )

                if duplicate is not None:
                    duplicate.websites.add(*relation.websites.all())
                    duplicate.sentences.add(*relation.sentences.all())
                    removed_relations.append(relation_payload(relation))
                    relation.delete()
                    updated_relations.append(relation_payload(duplicate))
                else:
                    if relation.entity1_id == source.id:
                        relation.entity1 = target
                    else:
                        relation.entity2 = target
                    relation.save()
                    relation.refresh_from_db()
                    updated_relations.append(relation_payload(relation))
                
            target.sentences.add(*source.sentences.all())
            source.sentences.clear()

            for membership in WebsiteEntity.objects.filter(entity=source):
                WebsiteEntity.objects.get_or_create(
                    website=membership.website,
                    entity=target,
                    defaults={'origin': membership.origin},
                )
                membership.delete()

            Entity.objects.filter(master=source).update(master=target)
            source.master = target
            source.save(update_fields=['master', 'updated_at'])

        return Response(
            {
                'merged': {'id': str(target.id), 'caption': target.entity_name, 'label': target.entity_type},
                'deleted_relations': removed_relations,
                'updated_relations': updated_relations,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        responses=EntityDetailSerializer,
        description='For node detail panel'
    )
    @action(detail=True, methods=['get'], url_path='detail', url_name='detail')
    def entity_detail(self, request, pk=None):
        entity = self.get_object()

        # --- Relations tab -------------------------------------------------
        relations = (
            Relation.objects
            .filter(user=request.user)
            .filter(Q(entity1=entity) | Q(entity2=entity))
            .select_related('relation_type', 'entity1', 'entity2')
            .annotate(evidence=Count('sentences', distinct=True))
        )

        rows = []
        for relation in relations:
            neighbour = relation.entity2 if relation.entity1_id == entity.id else relation.entity1
            rows.append({
                'id': str(relation.id),
                'relation_type': relation.relation_type.label if relation.relation_type else None,
                'neighbour': {
                    'id': str(neighbour.id),
                    'caption': neighbour.entity_name,
                    'label': neighbour.entity_type,
                },
                'count': relation.evidence,
            })

        # legacy models/Relation.js:257-268 — log-scaled, so one heavily evidenced
        # relation doesn't flatten every other bar to nothing
        def weight(count):
            return math.log(count) + 1 if count > 0 else 0

        top = max((weight(row['count']) for row in rows), default=0)
        for row in rows:
            row['score'] = round(100 / top * weight(row['count'])) if top else 0

        rows.sort(key=lambda row: (-row['count'], row['neighbour']['caption'].lower()))

        # --- Sources tab ---------------------------------------------------
        by_website = defaultdict(list)
        for sentence in (
            entity.sentences
            .filter(website__user=request.user)
            .order_by('website_id', 'created_at')
        ):
            by_website[sentence.website_id].append(sentence)

        memberships = (
            WebsiteEntity.objects
            .filter(entity=entity, website__user=request.user)
            .select_related('website')
            .order_by('-website__updated_at')
        )

        sources = []
        for membership in memberships:
            site = membership.website
            found = by_website.get(site.id, [])
            sources.append({
                'id': str(site.id),
                'url': site.url,
                'title': site.title or '',
                'updated_at': site.updated_at,
                'occurrences': membership.count,
                'sentence_count': len(found),
                'sentences': [
                    {'id': str(s.id), 'text': s.text}
                    for s in found[:_DETAIL_SENTENCES_PER_SOURCE]
                ],
            })

        return Response({
            'entity': {
                'id': str(entity.id),
                'caption': entity.entity_name,
                'label': entity.entity_type,
                'website_count': len(sources),
                'occurrence_count': sum(source['occurrences'] for source in sources),
                'aliases': [
                    {'id': str(alias.id), 'caption': alias.entity_name, 'label': alias.entity_type}
                    for alias in entity.aliases.all()
                ],
            },
            'relations': rows,
            'sources': sources,
        })

    @action(detail=True, methods=['post'], url_path='unmerge')
    def unmerge_alias(self, request, pk=None):
        canonical = self.get_object()
        alias_id = request.data.get('alias_id')

        alias = Entity.objects.filter(user=request.user, master=canonical, id=alias_id).first()
        if alias is None:
            return Response({'detail': 'alias not found'}, status=status.HTTP_404_NOT_FOUND)

        alias.master = None
        alias.save(update_fields=['master', 'updated_at'])

        return Response({'id': str(alias.id), 'caption': alias.entity_name, 'label': alias.entity_type})

        

class RelationViewSet(GenericViewSet):
    serializer_class = RelationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Relation.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = RelationSerializer(data=request.data)
        url = request.query_params.get('url', '').strip()
        serializer.is_valid(raise_exception=True)
        link = serializer.validated_data

        website = Website.objects.filter(user=request.user, url=url).first()
        if website is None:
            return Response(
                {'detail': 'Unknown website for this user'},
                status=status.HTTP_404_NOT_FOUND,
            )

        entities = Entity.objects.filter(
            user=request.user, id__in=[link['source'].get('id'), link['target'].get('id')]
        )

        by_id = {str(e.id): e.resolve() for e in entities}
        first, second = by_id.get(str(link['source'].get('id'))), by_id.get(str(link['target'].get('id')))

        if first is None or second is None or first.id == second.id:
            return Response(
                {'detail': 'source and target must be two distinct entities you own'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        relation_type, _ = RelationType.objects.get_or_create(
            user=request.user, label=link['relation_type']
        )

        if first.id > second.id:
            first, second = second, first

        relation, created = Relation.objects.get_or_create(
            user=request.user,
            entity1=first,
            entity2=second,
            relation_type=relation_type,
            defaults={'origin': Origin.MANUAL},
        )

        for item in link['sentences']:
            text = item.get('text', '').strip()
            if text:
                sentence,_ = Sentence.objects.get_or_create(website=website, text=text)
                relation.sentences.add(sentence)
        relation.websites.add(website)

        return Response(
            {
                'id': str(relation.id),
                'source': str(first.id),
                'target': str(second.id),
                'relation_type': relation_type.label,
                'sentences': [{'id': str(s.id), 'text': s.text} for s in relation.sentences.all()],
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    def partial_update(self, request, *args, **kwargs):
        relation = self.get_object()
        url = request.query_params.get('url', '').strip()
        if not url:
            return Response(
                {'detail': 'url is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )


        serializer = RelationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        link = serializer.validated_data

        website = Website.objects.filter(user=request.user, url=url).first()
        if website is None:
            return Response(
                {'detail': 'Unknown website for this user'},
                status=status.HTTP_404_NOT_FOUND,
            )

        label = link.get('relation_type', '')
        if not label:
            return Response(
                {'detail': 'relation type is missing'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        relation_type, _ = RelationType.objects.get_or_create(
            user=request.user, label=label,
        )

        if relation.relation_type_id == relation_type.id:
            return Response(
                {
                    'updated_relations': [relation_payload(relation)],
                    'deleted_relations': [],
                },
                status=status.HTTP_200_OK,
            )
        
        site_sentences = list(relation.sentences.filter(website=website))
        existing = (
            Relation.objects.filter(
                user=request.user,
                entity1=relation.entity1,
                entity2=relation.entity2,
                relation_type=relation_type,
            )
            .exclude(id=relation.id)
            .first()
        )

        updated_relations = []
        deleted_relations = []
        with transaction.atomic():
            single_site = relation.websites.count()

            if single_site and existing is None:
                #relation exists only for this website
                relation.relation_type = relation_type
                relation.save()
                updated_relations.append(relation_payload(relation))

            elif single_site:
                #relation exists only for this website, but there already is a relation with same type
                existing.websites.add(*relation.websites.all())
                existing.sentences.add(*relation.sentences.all())
                deleted_relations.append(str(relation.id))
                relation.delete()
                updated_relations.append(relation_payload(existing))

            else:
                #relation spans multiplr websites
                relation.websites.remove(website)
                relation.sentences.remove(*site_sentences)
                updated_relations.append(relation_payload(relation))

                if existing is None:
                    split = Relation.objects.create(
                        user=request.user,
                        entity1=relation.entity1,
                        entity2=relation.entity2,
                        relation_type=relation_type,
                        origin=relation.origin,
                    )

                    split.websites.add(website)
                    split.sentences.add(*site_sentences)
                    updated_relations.append(relation_payload(split))
                else:
                    existing.websites.add(website)
                    existing.sentences.add(*site_sentences)
                    updated_relations.append(relation_payload(existing))

        return Response(
            {
                'updated_relations': updated_relations,
                'deleted_relations': deleted_relations,
            },
            status=status.HTTP_200_OK,
        )



