"""
URL configuration for storyfinder project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from rest_framework.routers import DefaultRouter
from user.urls import api_router as user_api_router
from user.urls import auth_urlpatterns
from graph.urls import api_router as graph_api_router
from graph.urls import graph_urlpatterns
from chat.urls import api_router as chat_api_router
from chat.urls import chat_urlpatterns
from drf_spectacular.views import SpectacularAPIView

api_router = DefaultRouter()

api_routers = [
    user_api_router,
    graph_api_router,
    chat_api_router,
]


for router in api_routers:
    api_router.registry.extend(router.registry)


api_router.urls.extend(
    [
        path('schema/', SpectacularAPIView.as_view(), name='schema')
    ]
)

admin.site.site_header = 'Storyfinder Backend - Admin'
admin.site.site_title = 'Storyfinder Backend - Admin'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    path('api/v1/', include(api_router.urls)),
    path('api/v1/', include(auth_urlpatterns)),
    path('api/v1/', include(graph_urlpatterns)),
    path('api/v1/', include(chat_urlpatterns))
]
