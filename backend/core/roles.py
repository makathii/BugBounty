"""
Role lookup helpers.

Roles are Django ``Group`` names. Looking them up with
``user.groups.filter(...).exists()`` costs one query per check, and a single
request used to make several. ``get_roles`` loads the names once and memoizes
them on the *request* (not the user), so a long-lived user object whose groups
change between requests never serves stale roles.
"""

ADMIN = 'Admin'
TRIAGER = 'Triager'
PROGRAM_OWNER = 'ProgramOwner'
RESEARCHER = 'Researcher'

_CACHE_ATTR = '_cached_role_names'


def get_roles(request):
    """Return the set of group names for ``request.user`` (one query per request)."""
    cached = getattr(request, _CACHE_ATTR, None)
    if cached is not None:
        return cached
    user = getattr(request, 'user', None)
    if user is None or not getattr(user, 'is_authenticated', False):
        roles = frozenset()
    else:
        roles = frozenset(user.groups.values_list('name', flat=True))
    try:
        setattr(request, _CACHE_ATTR, roles)
    except AttributeError:
        pass
    return roles


def has_any_role(request, *names):
    return not get_roles(request).isdisjoint(names)


def is_admin_or_triager(request):
    return has_any_role(request, ADMIN, TRIAGER)
