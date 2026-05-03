from django.db import models

class AdminProfile(models.Model):
    user_id = models.IntegerField(unique=True)
    # Comes from Auth/User Service (JWT)

    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    is_super_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class UserVerification(models.Model):
    user_id = models.IntegerField(unique=True)
    is_verified = models.BooleanField(default=False)

    verified_by = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"User {self.user_id} Verification"


class PaymentDispute(models.Model):
    payment_id = models.IntegerField()
    application_id = models.IntegerField()

    raised_by = models.IntegerField()
    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=[
            ("open", "Open"),
            ("resolved", "Resolved"),
            ("rejected", "Rejected")
        ],
        default="open"
    )

    resolved_by = models.IntegerField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dispute {self.id} - {self.status}"


class AdminActionLog(models.Model):
    admin_id = models.IntegerField()

    action_type = models.CharField(max_length=100)
    target_type = models.CharField(max_length=50)
    target_id = models.IntegerField()

    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action_type} by Admin {self.admin_id}"

