from uuid import uuid4

from django.contrib.auth.models import AbstractUser
from django.db import models

from storyfinder.models import BaseModel


# Create your models here.
class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    def __str__(self):
        return self.username

class RegisterUser(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    username = models.CharField()
    firstname = models.CharField()
    lastname = models.CharField()
    password = models.CharField()
    email = models.EmailField()
    unlockcode = models.CharField()
