from rest_framework import serializers

from chat.models import ChatHistory

CONTENT_MAX = 8000
URL_MAX = 2000

class ChatMessageSerializer(serializers.Serializer):
    chat_message_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    role = serializers.ChoiceField(choices=['user', 'assistant'])
    content = serializers.CharField(max_length=CONTENT_MAX)
    timestamp = serializers.CharField()

class ChatRequestSerializer(serializers.Serializer):
    chat_history_id = serializers.IntegerField(required=False, allow_null=True)
    url = serializers.CharField(max_length=URL_MAX)
    text = serializers.CharField(allow_blank=True)
    message = ChatMessageSerializer()

    def validate(self, attrs):
        message = attrs.pop('message')
        attrs['chat_message_id'] = message.get('chat_message_id')
        attrs['role'] = message['role']
        attrs['content'] = message['content']
        attrs['timestamp'] = message['timestamp']
        return attrs

class ChatHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatHistory
        fields = ['id', 'website', 'title', 'messages', 'created_at', 'updated_at']
        read_only_fields = ['website', 'messages', 'created_at', 'updated_at']

class ChatHistoryLookupSerializer(serializers.Serializer):
    url = serializers.CharField()

        