"""
programs models, one module per model.

``from programs.models import Program`` etc. keeps working: every model is
imported here so Django registers it under the ``programs`` app.
"""
from .application import ProgramApplication
from .company import Company
from .favorite import ProgramFavorite
from .invitation import ProgramInvitation
from .notification import ProgramNotification
from .program import Program
from .scope import Scope
from .stats import ProgramStats

__all__ = [
    'Company', 'Program', 'Scope', 'ProgramInvitation', 'ProgramApplication',
    'ProgramStats', 'ProgramFavorite', 'ProgramNotification',
]
