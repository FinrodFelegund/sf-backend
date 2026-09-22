from rest_framework import serializers

from web.models import Entity

ENTITY_NAME_MAX = 255
RELATION_LABEL_MAX = 255
SENTENCE_MAX = 2000



class EntitySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    caption = serializers.CharField(max_length=ENTITY_NAME_MAX)
    label = serializers.ChoiceField(choices=Entity.EntityType.choices)

class EntityCreateSerializer(serializers.Serializer):
    caption = serializers.CharField(max_length=ENTITY_NAME_MAX)
    label = serializers.ChoiceField(choices=Entity.EntityType.choices)

class WebsiteRefSerializer(serializers.Serializer):
    url = serializers.CharField(max_length=2000)

class SiteEntitySerializer(serializers.Serializer):
    node = EntityCreateSerializer()
    website = WebsiteRefSerializer()

class MergeEntitySerializer(serializers.Serializer):
    source_id = serializers.IntegerField()
    target_id = serializers.IntegerField()

    def validate(self, attrs):
        if attrs['source_id'] == attrs['target_id']:
            raise serializers.ValidationError('source and target must be distinct')
        return attrs

class RelationSentenceSerializer(serializers.Serializer):
    id = serializers.CharField(required=False, allow_null=True)
    text = serializers.CharField(
        max_length=SENTENCE_MAX, required=False, allow_blank=True, default=''
    )
    website = serializers.CharField(required=False, allow_blank=True)

class RelationSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    sentences = RelationSentenceSerializer(many=True, required=False, default=list)
    relation_type = serializers.CharField(max_length=RELATION_LABEL_MAX)
    source = EntitySerializer()
    target = EntitySerializer()

    def validate_relation_type(self, value):
        return value.strip().lower()

class RelationInputSerializer(serializers.Serializer):
    source = serializers.CharField()
    target = serializers.CharField()
    relation_type = serializers.CharField(max_length=RELATION_LABEL_MAX)


class WebsiteSerializer(serializers.Serializer):
    id = serializers.CharField()
    url = serializers.CharField()
    title = serializers.CharField(allow_blank=True)
    entity_count = serializers.IntegerField()
    updated_at = serializers.DateTimeField()

class EntityNeighbourSerializer(serializers.Serializer):
    id = serializers.CharField()
    caption = serializers.CharField()
    label = serializers.CharField()

class EntityRelationSerializer(serializers.Serializer):
    id = serializers.CharField()
    relation_type = serializers.CharField(allow_null=True)
    neighbour = EntityNeighbourSerializer()
    count = serializers.IntegerField()
    score = serializers.IntegerField()


class EntitySourceSerializer(serializers.Serializer):
    id = serializers.CharField()
    url = serializers.CharField()
    title = serializers.CharField(allow_blank=True)
    updated_at = serializers.DateTimeField()
    occurrences = serializers.IntegerField()
    sentence_count = serializers.IntegerField()
    sentences = RelationSentenceSerializer(many=True)


class EntityDetailHeadSerializer(EntityNeighbourSerializer):
    website_count = serializers.IntegerField()
    occurrence_count = serializers.IntegerField()


class EntityDetailSerializer(serializers.Serializer):
    entity = EntityDetailHeadSerializer()
    relations = EntityRelationSerializer(many=True)
    sources = EntitySourceSerializer(many=True)



