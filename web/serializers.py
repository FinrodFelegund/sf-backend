from rest_framework import serializers


class EntitySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    caption = serializers.CharField()

class SiteEntitySerializer(serializers.Serializer):
    entity = EntitySerializer()
    website = serializers.DictField()


class RelationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    sentence = serializers.CharField()
    relation_type = serializers.CharField()
    entity1 = serializers.IntegerField()
    entity2 = serializers.IntegerField()

class SiteRelationSerializer(serializers.Serializer):
    relation = RelationSerializer()
    website = serializers.DictField()