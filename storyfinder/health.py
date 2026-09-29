import logging
import urllib.error as urlerror
import urllib.request as urlrequest

from django.conf import settings
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from rest_framework import status

logger = logging.getLogger(__name__)

@csrf_exempt
@never_cache
@require_GET
def liveness(request):
    """Basic check oif process is alive and serving"""
    return JsonResponse({'status': 'ok'}, status=status.HTTP_200_OK)

def check_database():
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception as error:
        return False, f'{type(error).__name__}: {error}'

    return True, 'connected'

def check_spacy():
    import spacy.util

    from shared.entityrecognition.ner import _MODELS_BY_LANG, _load_pipeline

    missing = [name for name in _MODELS_BY_LANG.values() if not spacy.util.is_package(name)]
    if missing:
        return False, f'missing: {", ".join(missing)}'

    warm = _load_pipeline.cache_info().currsize
    return True, f'{warm}/{len(_MODELS_BY_LANG)} pipelines loaded'


def check_llm_gateway():
    """Reachability only — no completion is requested, no tokens are spent."""
    base = (settings.OPENAI_API_BASE_URL or '').rstrip('/')
    api_key = (settings.OPENAI_API_KEY or '').rstrip('/')
    virtual_key = (settings.VIRTUAL_KEY or '').rstrip('/')
    if not base:
        return False, 'OPENAI_API_BASE_URL is not set'

    request = urlrequest.Request(f'{base}/models', method='GET')
    if api_key:
        request.add_header('Authorization', f'Bearer {api_key}')
    if virtual_key:
        request.add_header('x-bf-vk', virtual_key)

    try:
        with urlrequest.urlopen(request, timeout=3) as response:
            return 200 <= response.status < 300, f'HTTP {response.status}'
    except Exception as error:
        return False, f'{type(error).__name__}: {error}'


@csrf_exempt
@never_cache
@require_GET
def readiness(request):
    """Can this process actually do its job? Slow, and never polled by Docker."""
    checks = {}
    ready = True

    for name, check, required in (
        ('database', check_database, True),
        ('spacy', check_spacy, True),
        ('llm_gateway', check_llm_gateway, False),
    ):
        try:
            ok, detail = check()
        except Exception as error:
            ok, detail = False, f'{type(error).__name__}: {error}'

        checks[name] = {'ok': ok, 'detail': detail, 'required': required}
        if required and not ok:
            ready = False

    if not ready:
        logger.warning('Readiness check failed: %s', checks)

    return JsonResponse(
        {'status': 'ready' if ready else 'degraded', 'checks': checks},
        status=200 if ready else 503,
    )