from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import  IsAuthenticated
from web.serializers import SiteEntitySerializer, EntitySerializer, SiteRelationSerializer, RelationSerializer
from web.models import Website, Sentence, WebsiteEntity, Entity, Relation, RelationType
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError

# Create your views here.

class EntityViewSet(ModelViewSet):
    serializer_class = SiteEntitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Entity.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        serializer = SiteEntitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entity = serializer.validated_data['entity']
        website = serializer.validated_data['website']

        entity, created = Entity.objects.get_or_create(
            user=request.user, 
            entity_name=entity['caption'],
            entity_type=entity['label'],
        )

        website = Website.objects.filter(user=request.user, url=website['url']).first()
        if website:
            WebsiteEntity.objects.get_or_create(
                website=website,
                entity=entity,
                defaults={'count': 1}
            )

            matching = Sentence.objects.filter(
                website=website,
                text__icontains=f" {entity.entity_name} "
            )

            entity.sentences.add(*matching)

            return Response(
                {'id': entity.id, 'caption': entity.entity_name, 'label': entity.entity_type},
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )
        
    def partial_update(self, request, *args, **kwargs):
        entity = self.get_object()
        serializer = EntitySerializer(request.data)
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
        
        return Response({'id': entity.id, 'caption': entity.entity_name, 'label': entity.entity_type},)




