from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Profile


User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Auto-create a Profile when a User is created.

    Uses get_or_create to be safe against legacy data where the relation may
    already exist. The previous redundant `save_user_profile` handler was
    removed: it called `instance.profile.save()` on every User.save(), which
    triggered cascading signal noise and offered no real benefit.
    """
    if created:
        Profile.objects.get_or_create(user=instance)


@receiver(pre_save, sender=Profile)
def delete_old_avatar_on_change(sender, instance, **kwargs):
    """
    Remove the previous avatar file from storage when the user uploads a new one.

    Without this, every replaced avatar would leak a file in MEDIA_ROOT.
    Running on `pre_save` lets us compare the database row to the new instance
    before the field is overwritten.
    """
    if not instance.pk:
        return  # New profile, nothing to delete

    try:
        old = Profile.objects.get(pk=instance.pk)
    except Profile.DoesNotExist:
        return

    old_file = old.avatar
    new_file = instance.avatar
    if old_file and old_file != new_file:
        # Delete only when the file actually changed.
        old_file.delete(save=False)


@receiver(post_delete, sender=Profile)
def delete_avatar_on_profile_delete(sender, instance, **kwargs):
    """Remove the avatar file when the Profile row is deleted."""
    if instance.avatar:
        instance.avatar.delete(save=False)