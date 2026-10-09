from django.conf import settings
from django.db import models


class Company(models.Model):
    """Company profile that can create bug bounty programs"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='company_profile'
    )
    company_name = models.CharField(max_length=200)
    website = models.URLField()
    description = models.TextField()
    contact_email = models.EmailField()
    industry = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "companies"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.company_name} ({self.user.username})"

    @property
    def can_create_program(self):
        """Check if company can create programs"""
        return self.is_verified
