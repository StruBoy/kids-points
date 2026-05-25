from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models


class Role(models.TextChoices):
    PARENT = "parent", "Parent"
    KID = "kid", "Kid"


class UserManager(BaseUserManager):
    def create_parent(self, *, username, name, password, **extra):
        user = self.model(
            username=username, name=name, role=Role.PARENT, **extra
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_kid(self, *, name, pin, **extra):
        user = self.model(
            username=None, name=name, role=Role.KID, **extra
        )
        user.set_password(pin)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    username = models.CharField(
        max_length=64, unique=True, null=True, blank=True
    )
    name = models.CharField(max_length=64)
    role = models.CharField(max_length=8, choices=Role.choices)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    class Meta:
        ordering = ["role", "name"]

    def __str__(self):
        return f"{self.name} ({self.role})"

    @property
    def is_parent(self):
        return self.role == Role.PARENT

    @property
    def is_kid(self):
        return self.role == Role.KID
