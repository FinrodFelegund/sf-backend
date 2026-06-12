from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import GraphViewSet

api_router = DefaultRouter()

graph_urlpatterns = [
    path('graph/', GraphViewSet.as_view(), name='graph'),
]