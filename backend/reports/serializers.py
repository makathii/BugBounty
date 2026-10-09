from rest_framework import serializers
from .models import BugReport, Comment, ActivityLog
from .models import Attachment
from core.roles import is_admin_or_triager
from .sanitizers import sanitize_html


class CommentSerializer(serializers.ModelSerializer):
    """Flat comment. Pass ``request`` in the context to get ``can_edit``/``can_delete``."""

    author = serializers.StringRelatedField(read_only=True)
    text = serializers.CharField(max_length=5000)
    is_deleted = serializers.BooleanField(read_only=True)
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = (
            "id", "author", "text", "created_at", "edited_at", "parent",
            "is_internal", "is_deleted", "can_edit", "can_delete",
        )
        read_only_fields = ("id", "author", "created_at", "edited_at", "parent", "is_internal")

    def validate_text(self, value):
        """Strip all HTML tags to prevent stored XSS attacks.

        A researcher could submit a comment containing <script>...</script> or
        event-handler attributes (e.g. onerror=) that would execute in a
        triager's browser when the comment is rendered.  Running the text
        through bleach before saving ensures no markup survives to the DB.
        """
        value = sanitize_html(value, allowed_tags=[]).strip()
        if not value:
            raise serializers.ValidationError("Comment cannot be empty.")
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_deleted:
            data["text"] = ""  # the body is gone; the node stays so replies keep their place
        return data

    def _request(self):
        return self.context.get("request")

    def get_can_edit(self, obj):
        request = self._request()
        return bool(
            request and not obj.is_deleted and obj.author_id == request.user.id
        )

    def get_can_delete(self, obj):
        request = self._request()
        if not request or obj.is_deleted:
            return False
        return obj.author_id == request.user.id or is_admin_or_triager(request)


def build_comment_tree(comments, context=None):
    """Nest a flat, chronologically ordered comment list into ``replies`` trees.

    One pass over an already-fetched list, so a whole thread costs a single query.
    A comment whose parent is not in the list (e.g. an internal parent hidden from
    this viewer) is promoted to the top level rather than dropped.
    """
    nodes = {}
    for comment in comments:
        node = CommentSerializer(comment, context=context or {}).data
        node["replies"] = []
        nodes[comment.id] = node

    roots = []
    for comment in comments:
        node = nodes[comment.id]
        parent = nodes.get(comment.parent_id)
        (parent["replies"] if parent else roots).append(node)
    return roots

class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ("id","original_name","size","mime","sha256","scan_status","created_at")
        read_only_fields = fields

class BugReportSerializer(serializers.ModelSerializer):
    reporter_username = serializers.CharField(source='reporter.username', read_only=True)
    assigned_to_username = serializers.SerializerMethodField()
    program_name = serializers.SerializerMethodField()
    points_awarded = serializers.IntegerField(read_only=True)

    class Meta:
        model = BugReport
        fields = '__all__'
        read_only_fields = [
            'severity_score', 'time_to_triage', 'time_to_resolution',
            'created_at', 'updated_at', 'reporter',  # reporter is set in perform_create
            'bonus_points',  # only a triager's accept action may award bonus points
        ]

    def get_assigned_to_username(self, obj):
        return obj.assigned_to.username if obj.assigned_to_id else None

    def get_program_name(self, obj):
        return obj.program.name if obj.program_id else None
        
    def validate_title(self, value):
        if len(value)<10:
            raise serializers.ValidationError("Title is too short, must be at least 10 characters.")
        if len(value)>200:
            raise serializers.ValidationError("Title is too long, must be no more than 200 characters.")
        return value

    def validate_description(self, value):
        if len(value)<50:
            raise serializers.ValidationError("Description is too short, must be at least 50 characters.")
        if len(value)>5000:
            raise serializers.ValidationError("Description is too long, must be no more than 5000 characters.")
        return value

    def validate_severity(self, value):
        validate_severities=[choice[0] for choice in BugReport.SEVERITY_CHOICES]
        if value not in validate_severities:
            raise serializers.ValidationError("Severity must be one of {}".format(validate_severities))
        return value

    def validate(self, data):
        """Check for potential duplicates during validation"""
        # Create a temporary instance to check duplicates
        temp_report = BugReport(**data)
        duplicates = temp_report.find_potential_duplicates(threshold=0.8)

        if duplicates:
            duplicate_info = [
                {
                    "id": dup.id,
                    "title": dup.title,
                    "similarity": round(score, 2),
                    "created_at": dup.created_at.isoformat() if dup.created_at else None
                }
                for dup, score in duplicates
            ]
            raise serializers.ValidationError({
                "potential_duplicates": duplicate_info,
                "message": "Potential duplicate reports found. Please review before submitting."
            })
        return data


class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = ActivityLog
        fields = ('id', 'user', 'user_name', 'action', 'action_display', 'details', 'created_at')
        read_only_fields = fields