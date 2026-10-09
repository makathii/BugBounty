"""OAuth client login (GitHub / Google / GitLab): provider definitions and the start/callback views."""
from .views import oauth_callback, oauth_start

__all__ = ['oauth_start', 'oauth_callback']
