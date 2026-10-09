from rest_framework import serializers

from .models import WalletTransaction


class WalletTransactionSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = WalletTransaction
        fields = ("id", "amount", "kind", "kind_display", "reason", "reference", "created_at")
        read_only_fields = fields
