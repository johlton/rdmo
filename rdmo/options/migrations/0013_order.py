# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-07-31 10:44
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('options', '0012_meta'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='option',
            options={'ordering': ('optionset__order', 'optionset__key', 'order', 'key'), 'permissions': (('view_option', 'Can view Option'),), 'verbose_name': 'Option', 'verbose_name_plural': 'Options'},
        ),
    ]