from rest_framework.routers import DefaultRouter

from web.views import EntityViewSet, RelationViewSet, WebsiteViewSet

api_router = DefaultRouter()
api_router.register(r'web/entities', EntityViewSet, basename='entities')
api_router.register(r'web/relations', RelationViewSet, basename='relations')
api_router.register(r'web/websites', WebsiteViewSet, basename='websites')

web_urlpatterns = []