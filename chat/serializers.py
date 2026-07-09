from rest_framework import serializers
from chat.models import ChatHistory

class ChatRequestSerializer(serializers.Serializer):
    chat_message_id = serializers.IntegerField(required=False, allow_null=True)
    text = serializers.CharField()
    url = serializers.CharField()
    role = serializers.CharField()
    content = serializers.CharField()
    timestamp = serializers.CharField()

    def to_internal_value(self, data):
        if 'chat_message_id' not in data:
            data['chat_message_id'] = data['message']['chat_message_id']
        if 'role' not in data:
            data['role'] = data['message']['role']
        if 'content' not in data:
            data['content'] = data['message']['content']
        if 'timestamp' not in data:
            data['timestamp'] = data['message']['timestamp']
        del data['message']
        return super(ChatRequestSerializer, self).to_internal_value(data)

        

class ChatHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatHistory
        fields = ['id', 'website', 'title', 'messages', 'created_at', 'updated_at']
        read_only_fields = ['website', 'messages', 'created_at', 'updated_at']

class ChatHistoryLookupSerializer(serializers.Serializer):
    url = serializers.CharField()

        