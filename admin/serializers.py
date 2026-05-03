from rest_framework import serializers
from .models import UserVerification, PaymentDispute, AdminActionLog


class UserVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserVerification
        fields = "__all__"


class PaymentDisputeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentDispute
        fields = "__all__"


class AdminActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminActionLog
        fields = "__all__"
