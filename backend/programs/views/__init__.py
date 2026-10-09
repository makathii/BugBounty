"""
programs API views, one module per resource.

  programs       ProgramViewSet (+ join / activate / pause / close / stats)
  scopes         ScopeViewSet
  invitations    ProgramInvitationViewSet
  applications   ProgramApplicationViewSet
  favorites      ProgramFavoriteViewSet
  notifications  ProgramNotificationViewSet
  lists          researcher / company / public program lists
  dashboard      ProgramDashboardView (company + per-program dashboards)
  companies      CompanyViewSet
  root           API index

Everything is re-exported so ``from programs.views import ...`` keeps working.
"""

from .applications import ProgramApplicationViewSet
from .companies import CompanyViewSet
from .dashboard import ProgramDashboardView
from .favorites import ProgramFavoriteViewSet
from .invitations import ProgramInvitationViewSet
from .lists import CompanyProgramListView, PublicProgramListView, ResearcherProgramListView
from .notifications import ProgramNotificationViewSet
from .programs import ProgramViewSet, with_favorites_total
from .root import program_api_root
from .scopes import ScopeViewSet


__all__ = [
    'ProgramApplicationViewSet', 'CompanyViewSet', 'ProgramDashboardView',
    'ProgramFavoriteViewSet', 'ProgramInvitationViewSet',
    'CompanyProgramListView', 'PublicProgramListView', 'ResearcherProgramListView',
    'ProgramNotificationViewSet', 'ProgramViewSet', 'with_favorites_total',
    'program_api_root', 'ScopeViewSet',
]
