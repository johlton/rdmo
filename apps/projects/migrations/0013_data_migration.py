# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-09-28 11:23
from __future__ import unicode_literals

from django.db import migrations


def set_membership(apps, schema_editor):
    Project = apps.get_model('projects', 'Project')
    Membership = apps.get_model('projects', 'Membership')
    for project in Project.objects.all():
        for user in project.owner.all():
            membership = Membership(project=project, user=user, role='admin')
            membership.save()


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0012_membership'),
    ]

    operations = [
        migrations.RunPython(set_membership),
    ]
