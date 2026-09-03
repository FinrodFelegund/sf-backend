import json
import re

from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.models import ChatHistory
from chat.serializers import (
    ChatHistoryLookupSerializer,
    ChatHistorySerializer,
    ChatRequestSerializer,
)
from shared.llm.citation import CITATION_SENTINEL
from shared.llm.openai import get_openai_client
from web.models import Website
from web.services.service import get_or_refresh_website

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
            self._stream_answer(chat_history, website.content, history_for_llm, data),
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
    
    def _stream_answer(self, chat_history, page_text, history_for_llm, data):
        client = get_openai_client()
        messages = client.build_chat_prompt(page_text, history_for_llm, data['content'])

        buffer = ''
        answer_parts = []
        sources_raw = ''
        in_sources = False
        hold = len(CITATION_SENTINEL) - 1

        try:
            for chunk in client.stream(messages=messages):
                if in_sources:
                    sources_raw += chunk
                    continue
                
                buffer += chunk
                idx = buffer.find(CITATION_SENTINEL)

                if idx != -1:
                    emit = buffer[:idx]
                    sources_raw = buffer[idx + len(CITATION_SENTINEL):]
                    in_sources = True
                    buffer = ''
                else:
                    emit = buffer[:-hold] if len(buffer) > hold else ''
                    buffer = buffer[len(emit):]

                if emit:
                    answer_parts.append(emit)
                    yield f'data: {json.dumps({"content": emit})}\n\n'

            if not in_sources and buffer:
                answer_parts.append(buffer)
                yield f'data: {json.dumps({'content': buffer})}\n\n'

        except Exception as e:
            raise RuntimeError(str(e))
        finally:
            answer = ''.join(answer_parts).rstrip()
            citations = self._verify_citations(sources_raw, page_text)

            if answer:
                chat_history.messages.append({
                    'role': 'assistant',
                    'content': answer,
                    'timestamp': data['timestamp'],
                    'citations': citations,
                })
                chat_history.save(update_fields=['messages', 'updated_at'])
            
            yield f'data: {json.dumps({'citations': citations})}\n\n'
            yield 'data: [DONE]\n\n'

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r'\s+', '', text).strip().lower()

    @classmethod
    def _verify_citations(cls, raw: str, page_text: str, limit: int = 5):
        raw = raw.strip()
        start, end = raw.find('['), raw.find(']')
        if start == -1 or end == -1 or end < start:
            return []

        try:
            quotes = json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            return []

        if not isinstance(quotes, list):
            return []

        haystack = cls._normalize(page_text)
        verified, seen = [], set()

        for quote in quotes:
            if not isinstance(quote, str):
                continue
            quote = quote.strip()
            norm = cls._normalize(quote)

            if len(norm) < 15 or norm in seen or norm not in haystack:
                continue

            seen.add(norm)
            verified.append(quote)
            if len(verified) >= limit:
                break

        return verified