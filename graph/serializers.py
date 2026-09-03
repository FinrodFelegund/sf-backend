from rest_framework import serializers
from web.serializers import EntitySerializer, RelationSerializer

class GraphRequestSerializer(serializers.Serializer):
    text = serializers.CharField(required=False, allow_blank=True, default='')
    url = serializers.CharField()

    def validate(self, attrs):
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

class GraphQuerySerializer(serializers.Serializer):
    url = serializers.CharField(required=False, allow_blank=True, default='')
    text = serializers.CharField(required=False, allow_blank=True, default='')

class GraphFocusQuerySerializer(serializers.Serializer):
    focus = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        raw = (attrs.get('focus') or '').strip()
        ids = []

        for part in raw.replace(';', ',').split(','):
            part = part.strip()
            if not part:
                continue
            try:
                ids.append(int(part))
            except ValueError as exc:
                raise serializers.ValidationError(
                    {'focus': f'invalid website id: {part}'}
                ) from exc

        attrs['focus_ids'] = ids
        return attrs