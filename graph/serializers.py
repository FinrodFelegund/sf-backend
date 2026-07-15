from rest_framework import serializers
from web.serializers import EntitySerializer, RelationSerializer

class GraphRequestSerializer(serializers.Serializer):
    text = serializers.CharField(required=False, allow_blank=True, default='')
    url = serializers.CharField()

    def validate(self, attrs):
        print("In graph request serializer")
        url = attrs.get('url', "")
        text = attrs.get('text', "")
        if len(url) == 0 and len(text) == 0:
            raise serializers.ValidationError('Graph request is invalid')
        
        attrs['msg'] = {
            'url': url,
            'text': text,
        }

        return attrs


class GraphResponseSerializer(serializers.Serializer):
    nodes = EntitySerializer(many=True)
    links = RelationSerializer(many=True)
