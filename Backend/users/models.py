from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Profile(models.Model):
    ROLE_USER = "User"
    ROLE_PROGRAM_OWNER = "ProgramOwner"
    ROLE_ADMIN = "Admin"

    ROLE_CHOICES = [
        (ROLE_USER, "User"),
        (ROLE_PROGRAM_OWNER, "Program Owner"),
        (ROLE_ADMIN, "Admin"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_USER)  # <-- add this
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=64, blank=True, null=True)

    def __str__(self):
        return self.user.username