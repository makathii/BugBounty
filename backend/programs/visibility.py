"""Which programs a researcher can see (as opposed to which they can submit reports to)."""
from .models import Program


def accessible_private_program_ids(user):
    """Ids of private programs ``user`` has been let into (accepted invitation / approved application)."""
    invited = Program.objects.filter(
        scope_type='private', invitations__researcher=user, invitations__status='accepted'
    ).values_list('id', flat=True)
    applied = Program.objects.filter(
        scope_type='private', applications__researcher=user, applications__status='approved'
    ).values_list('id', flat=True)
    return set(invited) | set(applied)


def researcher_visible_programs(user):
    """
    Everything a researcher may *see*:

    - public and VDP programs;
    - private programs they have access to (accepted invitation / approved application);
    - private programs that take applications (so there is something to apply to);
    - private programs they have a pending invitation to (so they can accept it).

    Seeing is not access: a private program's targets and guidelines stay hidden until access is
    granted (see ProgramDetailSerializer), and reports are only accepted from people with access.
    """
    qs = Program.objects.all()
    public = qs.filter(scope_type__in=['public', 'vdp'], status='active')
    private = qs.filter(scope_type='private', status='active')
    invited = private.filter(invitations__researcher=user, invitations__status='accepted')
    applied = private.filter(applications__researcher=user, applications__status='approved')
    discoverable = private.filter(requires_application=True)
    pending_invite = private.filter(invitations__researcher=user, invitations__status='pending')
    return (public | invited | applied | discoverable | pending_invite).distinct()
