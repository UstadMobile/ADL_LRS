from django.db import models
from django.contrib.auth.models import User
import os
import uuid
import time
from lrs.models import Statement


class credentials(models.Model):
    user_destination = models.CharField(max_length=1500, blank=False)
    endpoint = models.CharField(max_length=1500, blank=False)
    username = models.CharField(max_length=1500, blank=False)
    user=models.ForeignKey(User)
    password = models.CharField(max_length=100, blank=False)

class statement_forward_status(models.Model):
    statement = models.OneToOneField(Statement)
    status = models.CharField(max_length=50, blank=False, default="pending") #pending, sent, fail
    tries = models.IntegerField(default=0)
    response = models.CharField(max_length=1000, blank=True)
    credential = models.ForeignKey(credentials)

# Create your models here.
