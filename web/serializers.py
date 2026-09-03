from rest_framework import serializers


class EntitySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    caption = serializers.CharField()
    label = serializers.CharField()

class SiteEntitySerializer(serializers.Serializer):
    node = EntitySerializer()
    website = serializers.DictField()

class MergeEntitySerializer(serializers.Serializer):
    source_id = serializers.CharField()
    target_id = serializers.CharField()


class RelationSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    sentences = serializers.ListField(
        child=serializers.DictField(), required=False, default=list
    )
    relation_type = serializers.CharField()
    source = EntitySerializer()
    target = EntitySerializer()

class RelationInputSerializer(serializers.Serializer):
    source = serializers.CharField()
    target = serializers.CharField()
    relation_type = serializers.CharField()


class WebsiteSerializer(serializers.Serializer):
    id = serializers.CharField()
    url = serializers.CharField()
    title = serializers.CharField(allow_blank=True)
    entity_count = serializers.IntegerField()
    updated_at = serializers.DateTimeField()



