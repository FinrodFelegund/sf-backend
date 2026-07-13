from rest_framework import serializers

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
    entities = serializers.JSONField()

    def validate(self, attrs):
        ents = attrs['entites']
        sents = attrs['sentences']

        if not ents or not sents:
            raise serializers.ValidationError('Graph response is invalid')
        
        return attrs
