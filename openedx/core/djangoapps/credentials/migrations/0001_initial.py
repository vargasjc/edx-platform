# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CredentialsApiConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('change_date', models.DateTimeField(auto_now_add=True, verbose_name='Change date')),
                ('enabled', models.BooleanField(default=False, verbose_name='Enabled')),
                ('api_version_number', models.IntegerField(verbose_name='API Version')),
                ('internal_service_url', models.URLField(verbose_name='Internal Service URL')),
                ('public_service_url', models.URLField(verbose_name='Public Service URL')),
                ('enable_learner_credentials', models.BooleanField(default=False, help_text='This flag is required to enable learner credential.', verbose_name='Enable Learner Credential')),
                ('enable_studio_credentials', models.BooleanField(default=False, help_text='This flag is required to enable learner credential for studio authoring.', verbose_name='Enable Learner Credential in Studio')),
                ('changed_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, editable=False, to=settings.AUTH_USER_MODEL, null=True, verbose_name='Changed by')),
            ],
            options={
                'ordering': ('-change_date',),
                'abstract': False,
            },
        ),
    ]