class NoIndexMiddleware:
    """Ask search engines not to index this site (used by the preview and pre-launch hosting)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['X-Robots-Tag'] = 'noindex, nofollow'
        return response
