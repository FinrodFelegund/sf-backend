from rest_framework import mixins, viewsets, status
from rest_framework.permissions import IsAuthenticated
from django.http import StreamingHttpResponse
from rest_framework.response import Response

from chat.models import ChatHistory
from chat.serializers import ChatHistorySerializer, ChatRequestSerializer, ChatHistoryLookupSerializer
from shared.llm.openai import get_openai_client
from web.services.service import get_or_refresh_website
from web.models import Website

import json
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

# Create your views here.

class ChatHistoryViewSetAPI(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ChatHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ChatHistory.objects.filter(user=self.request.user)

class ChatHistoryViewSet(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChatHistoryLookupSerializer,
        description='Get a users chat history'
    )
    def post(self, request):
        serializer = ChatHistoryLookupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        print(request.data)
        user = request.user
        url = serializer.validated_data['url']

        history = ChatHistory.objects.all().filter(user=user, website__url=url).first()
        if history is None:
            return Response(
                {
                    'messages': []
                },
                status=status.HTTP_200_OK
            )
        return Response(
            {
                'messages': history.messages,
            },
            status=status.HTTP_200_OK
        )


    

class ChatStreamViewSet(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ChatRequestSerializer, description='Ask a question about the website, streamed as SSE')
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        website = get_or_refresh_website(request.user, data['url'], data['text'])
        summary = self._get_or_create_summary(website)
        chat_history, created = ChatHistory.objects.get_or_create(user=request.user, website=website)
        history_for_llm = list(chat_history.messages)
        chat_history.messages.append({'role': 'user', 'content': data['content'], 'timestamp': data['timestamp']})
        chat_history.save(update_fields=['messages', 'updated_at'])

        response = StreamingHttpResponse(
            self._stream_answer(chat_history, summary, history_for_llm, data),
            content_type='text/event-stream'
        )

        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
    
    @staticmethod
    def _get_or_create_summary(website: Website):
        if website.summary:
            return website.summary
        client = get_openai_client()
        messages = client.build_summary_prompt(website=website)
        website.summary = client.response(messages=messages)
        website.save(update_fields=['summary', 'updated_at'])
        return website.summary
    
    @staticmethod
    def _get_or_create_history(user, website, url):
        if url:
            return get_object_or_404(ChatHistory, user=user, website=website)
        
        return ChatHistory.objects.create(user=user, website=website)
    
    def _stream_answer(self, chat_history, summary, history_for_llm, data):
        chunks = []
        client = get_openai_client()
        messages = client.build_chat_prompt(summary, history_for_llm, data['content'])
        try:
            for chunk in client.stream(messages=messages):
                chunks.append(chunk)
                yield f'data: {json.dumps({"content": chunk})}\n\n'
        except Exception as e:
            raise RuntimeError(str(e))
        finally:
            answer = ''.join(chunks)
            if answer:
                chat_history.messages.append({'role': 'assistant', 'content': answer, 'timestamp': data['timestamp']})
                chat_history.save(update_fields=['messages', 'updated_at'])
            yield 'data: [DONE]\n\n'