from rest_framework import serializers

class GraphRequestSerializer(serializers.Serializer):
    url = serializers.CharField()
    text = serializers.CharField()

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
