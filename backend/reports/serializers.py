from rest_framework import serializers
from .models import BugReport, Comment, ActivityLog
from .models import Attachment
from .sanitizers import sanitize_html


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "author", "text", "created_at")

    def validate_text(self, value):
        """Strip all HTML tags to prevent stored XSS attacks.

        A researcher could submit a comment containing <script>...</script> or
        event-handler attributes (e.g. onerror=) that would execute in a
        triager's browser when the comment is rendered.  Running the text
        through bleach before saving ensures no markup survives to the DB.
        """
        return sanitize_html(value, allowed_tags=[])

class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ("id","original_name","size","mime","sha256","scan_status","created_at")
        read_only_fields = fields

class BugReportSerializer(serializers.ModelSerializer):
    reporter_username = serializers.CharField(source='reporter.username', read_only=True)
    assigned_to_username = serializers.SerializerMethodField()
    program_name = serializers.SerializerMethodField()

    class Meta:
        model = BugReport
        fields = '__all__'
        read_only_fields = [
            'severity_score', 'time_to_triage', 'time_to_resolution',
            'created_at', 'updated_at', 'reporter'  # reporter is set in perform_create
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