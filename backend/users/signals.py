from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()

try:
    # Try to import Profile from users app (the actual model name)
    from users.models import Profile


    @receiver(post_save, sender=User)
    def create_user_profile(sender, instance, created, **kwargs):
        """Create a Profile when a new User is created"""
        if created:
            Profile.objects.create(user=instance)


    @receiver(post_save, sender=User)
    def save_user_profile(sender, instance, **kwargs):
        """Save the Profile when User is saved"""
        if hasattr(instance, 'profile'):
            instance.profile.save()
except ImportError:
    # If users app doesn't exist or doesn't have Profile, do nothing
    print("Warning: Could not import Profile from users.models")
    pass
