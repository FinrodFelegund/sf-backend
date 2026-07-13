from rest_framework.routers import DefaultRouter
from web.views import EntityViewSet

api_router = DefaultRouter()
api_router.register(r'web/entities', EntityViewSet, basename='entities')

web_urlpatterns = []