"""Custom renderers for FoD api"""

from rest_framework import renderers

class PlainTextRenderer(renderers.BaseRenderer):    # pylint: disable=too-few-public-methods
    """Return the data in plain text"""
    media_type = 'text/plain'
    format = 'txt'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data
