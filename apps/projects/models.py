from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from apps.core.models import Model
from apps.domain.models import Attribute, Option
from apps.questions.models import Catalog


@python_2_unicode_compatible
class Project(Model):

    owner = models.ManyToManyField(User)

    title = models.CharField(max_length=256, verbose_name=_('title'))
    description = models.TextField(blank=True, help_text=_('Optional'), verbose_name=_('description'))

    catalog = models.ForeignKey(Catalog, related_name='+', help_text=_('The catalog which will be used for this project.'), verbose_name=_('catalog'))

    class Meta:
        ordering = ('title', )
        verbose_name = _('Project')
        verbose_name_plural = _('Projects')

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('project', kwargs={'pk': self.pk})

    def owner_string(self):
        return ', '.join([user.profile.full_name for user in self.owner.all()])

    @property
    def current_snapshot(self):
        snapshot = self.snapshots.first()
        if snapshot is None:
            snapshot = Snapshot.objects.create(title='current', project=self)
        return snapshot


@python_2_unicode_compatible
class Snapshot(Model):

    title = models.CharField(max_length=256, verbose_name=_('title'))
    description = models.TextField(blank=True, help_text=_('Optional'), verbose_name=_('description'))

    project = models.ForeignKey('Project', related_name='snapshots')

    class Meta:
        ordering = ('project', '-created')
        verbose_name = _('Snapshot')
        verbose_name_plural = _('Snapshots')

    def __str__(self):
        return '%s / %s' % (self.project.title, self.title)

    def get_absolute_url(self):
        return reverse('project', kwargs={'pk': self.project.pk})


@python_2_unicode_compatible
class Value(Model):

    snapshot = models.ForeignKey('Snapshot', related_name='values')
    attribute = models.ForeignKey(Attribute, related_name='values', blank=True, null=True, on_delete=models.SET_NULL)

    set_index = models.IntegerField(default=0)
    collection_index = models.IntegerField(default=0)

    text = models.TextField(blank=True, null=True)
    option = models.ForeignKey(Option, blank=True, null=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        verbose_name = _('Value')
        verbose_name_plural = _('Values')

    @property
    def value(self):
        if self.option:
            if self.option.additional_input:
                return self.option.text + ': ' + self.text
            else:
                return self.option.text
        elif self.text:
            return self.text
        else:
            return None

    def __str__(self):
        if self.attribute:
            attribute_label = self.attribute.label
        else:
            attribute_label = '---'

        return '%s / %s.%i.%i = "%s"' % (
            self.snapshot,
            attribute_label,
            self.set_index,
            self.collection_index,
            self.value
        )
