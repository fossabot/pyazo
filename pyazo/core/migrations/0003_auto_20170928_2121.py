# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-09-28 19:21
from __future__ import unicode_literals

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pyazo_core", "0002_auto_20170601_1850"),
    ]

    operations = [
        migrations.AlterField(
            model_name="upload",
            name="user",
            field=models.ForeignKey(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
