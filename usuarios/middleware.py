from django.utils.cache import add_never_cache_headers


class SinCacheMiddleware:
    """Evita que el navegador guarde copias de las páginas del sistema: al
    cerrar sesión y pulsar «Atrás», el navegador vuelve a pedir la página al
    servidor, que redirige al login si ya no hay sesión."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith(("/static/", "/media/")):
            add_never_cache_headers(response)
        return response
