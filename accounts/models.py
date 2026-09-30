from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Empty for now, but owning this model means we can add fields later
    without a painful migration away from django.contrib.auth.User."""
