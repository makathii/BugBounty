from rest_framework import serializers
from .models import BugReport, Comment, ActivityLog
from .models_attachment import Attachment
from rest_framework import serializers

class CommentSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Comment
        fields = ("id","author","text","created_at")

class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ("id","original_name","size","mime","sha256","scan_status","created_at")
        read_only_fields = fields

class BugReportSerializer(serializers.ModelSerializer):
    reporter = serializers.StringRelatedField(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = BugReport
        fields = ("id","title","description","reporter","severity","status","bounty_amount","created_at","updated_at","comments","attachments")
        read_only_fields = ("status","reporter","created_at","updated_at")

        def validate_title(self, value):
            if len(value)<10:
                raise serializers.ValidationError("Title is too short, must be at least 10 characters.")
            if len(value)>200:
                raise serializers.ValidationError("Title is too long, must be no more than 200 characters.")
            return value

        def validate_description(self, value):
            if len(value)<50:
                raise serializers.ValidationError("Description is too short, must be no more than 50 characters.")
            if len(value)>5000:
                raise serializers.ValidationError("Description is too long, must be no more than 5000 characters.")
            return value

        def validate_severity(self, value):
            validate_severities=[choice[0] for choice in BugReport.SEVERITY_CHOICES]
            if value not in validate_severities:
                raise serializers.ValidationError("Severity must be one of {}".format(validate_severities))
            return value


class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = ActivityLog
        fields = ('id', 'user', 'user_name', 'action', 'action_display', 'details', 'created_at')
        read_only_fields = fields