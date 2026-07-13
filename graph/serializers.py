from rest_framework import serializers
from web.serializers import EntitySerializer, RelationSerializer

class GraphRequestSerializer(serializers.Serializer):
    text = serializers.CharField()
    url = serializers.CharField()

    def validate(self, attrs):
        url = attrs.get('url')
        text = attrs.get('text')

        if not url or not text:
            raise serializers.ValidationError('Graph request is invalid')
        
        attrs['msg'] = {
            'url': url,
            'text': text,
        }

        return attrs    


class GraphResponseSerializer(serializers.Serializer):
    nodes = EntitySerializer(many=True)
    links = RelationSerializer(many=True)
