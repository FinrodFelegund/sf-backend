from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ChatHistoryViewSet, ChatHistoryViewSetAPI, ChatStreamViewSet

api_router = DefaultRouter()
api_router.register(r'chat-history', ChatHistoryViewSetAPI, basename='Chat-History')

chat_urlpatterns = [
    path('chat/stream/', ChatStreamViewSet.as_view(), name='stream'),
    path('chat/history/', ChatHistoryViewSet.as_view(), name='history')
]