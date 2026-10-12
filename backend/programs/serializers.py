from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
    Program, Scope, ProgramInvitation, ProgramApplication,
    ProgramStats, ProgramFavorite, ProgramNotification, Company
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------

class CompanySerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Company
        fields = [
            'id', 'user_id', 'username',
            'company_name', 'website', 'description',
            'contact_email', 'industry', 'country',
            'is_verified', 'can_create_program',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user_id', 'username', 'is_verified', 'can_create_program', 'created_at', 'updated_at']


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------

class ScopeSerializer(serializers.ModelSerializer):
    target_type_display = serializers.CharField(source='get_target_type_display', read_only=True)

    class Meta:
        model = Scope
        fields = [
            'id', 'target', 'target_type', 'target_type_display',
            'is_in_scope', 'description', 'notes', 'points_multiplier',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


# ---------------------------------------------------------------------------
# Program
# ---------------------------------------------------------------------------

class ProgramListSerializer(serializers.ModelSerializer):
    company = UserSummarySerializer(read_only=True)
    points_range = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    can_accept_submissions = serializers.ReadOnlyField()
    scope_type_display = serializers.CharField(source='get_scope_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    favorites_count = serializers.SerializerMethodField()
    # Can this user report to the program (as opposed to merely see it)? Cheap enough for lists.
    user_has_access = serializers.SerializerMethodField()

    class Meta:
        model = Program
        fields = [
            'id', 'name', 'slug', 'short_description',
            'scope_type', 'scope_type_display',
            'status', 'status_display',
            'company',
            'min_points', 'max_points', 'points_range',
            'is_active', 'can_accept_submissions',
            'total_reports', 'total_points', 'avg_severity_score',
            'favorites_count', 'user_has_access',
            'created_at', 'published_at',
        ]
        read_only_fields = fields

    def get_user_has_access(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        user = request.user
        if obj.company_id == user.id:
            return True
        if obj.scope_type in ('public', 'vdp'):
            return obj.status == 'active'
        if obj.status != 'active':
            return False
        # private: one lookup per request, not per program
        cache = self.context.setdefault('_private_access_ids', None)
        if cache is None:
            from .visibility import accessible_private_program_ids
            cache = self.context['_private_access_ids'] = accessible_private_program_ids(user)
        return obj.id in cache

    def get_favorites_count(self, obj):
        # Annotated by ProgramViewSet.get_queryset(); fall back for other callers.
        annotated = getattr(obj, 'favorites_total', None)
        return annotated if annotated is not None else obj.favorites.count()


def _is_manager(user, program):
    from .permissions import _can_manage
    return bool(user and user.is_authenticated and _can_manage(user, program))


class ProgramDetailSerializer(serializers.ModelSerializer):
    company = UserSummarySerializer(read_only=True)
    scopes = ScopeSerializer(many=True, read_only=True)
    points_range = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    can_accept_submissions = serializers.ReadOnlyField()
    scope_type_display = serializers.CharField(source='get_scope_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    favorites_count = serializers.SerializerMethodField()
    in_scope_count = serializers.SerializerMethodField()
    out_of_scope_count = serializers.SerializerMethodField()
    user_has_access = serializers.SerializerMethodField()   # ← new
    my_application = serializers.SerializerMethodField()
    my_invitation = serializers.SerializerMethodField()

    class Meta:
        model = Program
        fields = [
            'id', 'name', 'slug', 'description', 'short_description',
            'scope_type', 'scope_type_display',
            'status', 'status_display',
            'company',
            'reward_notes', 'min_points', 'max_points', 'points_range',
            'start_date', 'end_date',
            'allow_anonymous', 'require_ndas', 'invitation_only', 'requires_application',
            'testing_guidelines', 'report_guidelines', 'disclosure_policy',
            'total_reports', 'total_points', 'avg_severity_score',
            'avg_time_to_triage', 'avg_time_to_resolution',
            'scopes', 'in_scope_count', 'out_of_scope_count',
            'is_active', 'can_accept_submissions',
            'user_has_access',                              # ← new
            'my_application', 'my_invitation',
            'favorites_count',
            'created_at', 'updated_at', 'published_at',
        ]
        read_only_fields = fields

    def get_favorites_count(self, obj):
        # Annotated by ProgramViewSet.get_queryset(); fall back for other callers.
        annotated = getattr(obj, 'favorites_total', None)
        return annotated if annotated is not None else obj.favorites.count()

    def get_in_scope_count(self, obj):
        # .all() uses the prefetch cache when present; filter() would re-query.
        return sum(1 for sc in obj.scopes.all() if sc.is_in_scope)

    def get_out_of_scope_count(self, obj):
        return sum(1 for sc in obj.scopes.all() if not sc.is_in_scope)

    def get_user_has_access(self, obj):              # ← new
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        from .permissions import CanAccessProgram
        return CanAccessProgram().has_object_permission(request, None, obj)

    def _mine(self, obj, related):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        # .all() reuses the prefetch cache that ProgramViewSet.get_object() sets up
        for row in getattr(obj, related).all():
            if row.researcher_id == request.user.id:
                return {'id': row.id, 'status': row.status}
        return None

    def get_my_application(self, obj):
        return self._mine(obj, 'applications')

    def get_my_invitation(self, obj):
        return self._mine(obj, 'invitations')

    def to_representation(self, instance):
        """A private program shows its description to people who may apply, but its targets and
        guidelines only to people with access (the company, admins, approved/invited researchers)."""
        data = super().to_representation(instance)
        if instance.scope_type == 'private' and not data.get('user_has_access'):
            request = self.context.get('request')
            if not (request and (_is_manager(request.user, instance))):
                data['scopes'] = []
                data['in_scope_count'] = 0
                data['out_of_scope_count'] = 0
                data['testing_guidelines'] = ''
                data['report_guidelines'] = ''
        return data


class ProgramCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Program
        fields = [
            'id', 'name', 'description', 'short_description', 'scope_type',
            'reward_notes', 'min_points', 'max_points',
            'start_date', 'end_date',
            'allow_anonymous', 'require_ndas', 'invitation_only', 'requires_application',
            'testing_guidelines', 'report_guidelines', 'disclosure_policy',
        ]
        read_only_fields = ['id']

    def validate(self, data):
        min_b = data.get('min_points')
        max_b = data.get('max_points')
        if min_b is not None and max_b is not None and min_b > max_b:
            raise serializers.ValidationError(
                {'max_points': 'Maximum points must be greater than or equal to minimum points.'}
            )
        start = data.get('start_date')
        end = data.get('end_date')
        if start and end and start > end:
            raise serializers.ValidationError(
                {'end_date': 'End date must be after start date.'}
            )
        scope_type = data.get('scope_type', 'public')
        if scope_type != 'private':
            if data.get('invitation_only'):
                raise serializers.ValidationError(
                    {'invitation_only': 'invitation_only can only be set on private programs.'}
                )
            if data.get('requires_application'):
                raise serializers.ValidationError(
                    {'requires_application': 'requires_application can only be set on private programs.'}
                )
        return data


class ProgramUpdateSerializer(ProgramCreateSerializer):
    status = serializers.ChoiceField(choices=Program.STATUS_CHOICES, required=False)

    class Meta(ProgramCreateSerializer.Meta):
        fields = ProgramCreateSerializer.Meta.fields + ['status']
        extra_kwargs = {field: {'required': False} for field in fields}

    def validate_status(self, value):
        instance = self.instance
        if instance is None:
            return value
        invalid_transitions = {
            'closed': ['draft', 'active', 'paused'],
            'draft': ['closed'],
        }
        blocked = invalid_transitions.get(instance.status, [])
        if value in blocked:
            raise serializers.ValidationError(
                f"Cannot transition from '{instance.status}' to '{value}'."
            )
        return value


class PublicProgramSerializer(serializers.ModelSerializer):
    company_username = serializers.CharField(source='company.username', read_only=True)
    points_range = serializers.ReadOnlyField()
    scope_type_display = serializers.CharField(source='get_scope_type_display', read_only=True)

    class Meta:
        model = Program
        fields = [
            'id', 'name', 'slug', 'short_description',
            'scope_type', 'scope_type_display',
            'company_username',
            'min_points', 'max_points', 'points_range',
            'total_reports', 'avg_severity_score',
            'published_at',
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Invitation
# ---------------------------------------------------------------------------

class ProgramInvitationSerializer(serializers.ModelSerializer):
    researcher = UserSummarySerializer(read_only=True)
    invited_by = UserSummarySerializer(read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    # Who to invite: by username (what the UI sends) or, for older clients, by user id.
    username = serializers.CharField(write_only=True, required=False, allow_blank=True)
    researcher_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='researcher', write_only=True, required=False
    )

    class Meta:
        model = ProgramInvitation
        fields = [
            'id', 'program', 'program_name',
            'researcher', 'researcher_id', 'username',
            'invited_by',
            'status', 'status_display',
            'message',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'program', 'program_name',
            'researcher', 'invited_by',
            'status', 'status_display',
            'created_at', 'updated_at',
        ]

    def validate(self, attrs):
        username = (attrs.pop('username', '') or '').strip()
        researcher = attrs.get('researcher')
        if username:
            researcher = User.objects.filter(username__iexact=username).first()
            if researcher is None:
                raise serializers.ValidationError({'username': 'No researcher with that username.'})
        if researcher is None:
            raise serializers.ValidationError({'username': "Enter the researcher's username."})
        if not researcher.is_active or not researcher.groups.filter(name='Researcher').exists():
            raise serializers.ValidationError(
                {'username': 'Invitations can only be sent to active Researcher accounts.'}
            )
        attrs['researcher'] = researcher
        return attrs


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class ProgramApplicationSerializer(serializers.ModelSerializer):
    researcher = UserSummarySerializer(read_only=True)
    reviewed_by = UserSummarySerializer(read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ProgramApplication
        fields = [
            'id', 'program', 'program_name',
            'researcher',
            'status', 'status_display',
            'message', 'experience', 'qualifications',
            'reviewed_by', 'review_notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'program', 'program_name',
            'researcher',
            'status', 'status_display',
            'reviewed_by', 'review_notes',
            'created_at', 'updated_at',
        ]


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class ProgramStatsSerializer(serializers.ModelSerializer):
    total_vulnerabilities = serializers.ReadOnlyField()

    class Meta:
        model = ProgramStats
        fields = [
            'id', 'program', 'date',
            'total_reports', 'new_reports', 'resolved_reports',
            'total_points', 'avg_points',
            'avg_time_to_triage', 'avg_time_to_resolution', 'avg_time_to_award',
            'critical_count', 'high_count', 'medium_count', 'low_count', 'info_count',
            'total_vulnerabilities',
            'active_researchers', 'new_researchers',
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Favorite
# ---------------------------------------------------------------------------

class ProgramFavoriteSerializer(serializers.ModelSerializer):
    program_name = serializers.CharField(source='program.name', read_only=True)
    program_slug = serializers.CharField(source='program.slug', read_only=True)

    class Meta:
        model = ProgramFavorite
        fields = ['id', 'program', 'program_name', 'program_slug', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_program(self, program):
        request = self.context.get('request')
        if request and ProgramFavorite.objects.filter(
            program=program, researcher=request.user
        ).exists():
            raise serializers.ValidationError("You have already favorited this program.")
        return program


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

class ProgramNotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', read_only=True
    )
    program_name = serializers.SerializerMethodField()

    class Meta:
        model = ProgramNotification
        fields = [
            'id', 'program', 'program_name',
            'notification_type', 'notification_type_display',
            'title', 'message', 'data',
            'read', 'created_at',
        ]
        read_only_fields = [
            'id', 'program', 'program_name',
            'notification_type', 'notification_type_display',
            'title', 'message', 'data',
            'created_at',
        ]

    def get_program_name(self, obj):
        return obj.program.name if obj.program else None


# ---------------------------------------------------------------------------
# Report — avoids circular import with reports app
# ---------------------------------------------------------------------------

class ProgramReportSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    severity = serializers.CharField(read_only=True)
    bonus_points = serializers.IntegerField(read_only=True)
    points_awarded = serializers.IntegerField(read_only=True)
    reporter_username = serializers.CharField(source='reporter.username', read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
