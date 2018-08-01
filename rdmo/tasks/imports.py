import logging

from django.core.exceptions import ValidationError

from rdmo.core.imports import get_savelist_setting, get_value_from_treenode, model_will_be_imported
from rdmo.core.utils import get_ns_map, get_uri, get_ns_tag
from rdmo.domain.models import Attribute

from .models import Task, TimeFrame
from .validators import TaskUniqueKeyValidator

log = logging.getLogger(__name__)


def import_tasks(tasks_node, savelist={}, do_save=False):
    log.info('Importing tasks')
    nsmap = get_ns_map(tasks_node.getroot())

    for task_node in tasks_node.findall('task'):
        task_uri = get_uri(task_node, nsmap)

        try:
            task = Task.objects.get(uri=task_uri)
            task_before = task
        except Task.DoesNotExist:
            task = Task()
            log.info('Task not in db. Created with uri ' + task_uri)
            task_before = None
        else:
            log.info('Task does exist. Loaded from uri ' + task_uri)

        task.uri_prefix = task_uri.split('/tasks/')[0]
        task.key = task_uri.split('/')[-1]

        try:
            attribute_uri = get_uri(task_node, nsmap, 'attrib')
            task.attribute = Attribute.objects.get(uri=attribute_uri)
        except (AttributeError, Attribute.DoesNotExist, KeyError):
            task.attribute = None

        for element in task_node.findall('title'):
            setattr(task, 'title_' + element.attrib['lang'], element.text)
        for element in task_node.findall('text'):
            setattr(task, 'text_' + element.attrib['lang'], element.text)

        try:
            TaskUniqueKeyValidator(task).validate()
        except ValidationError:
            log.info('Task not saving "' + str(task_uri) + '" due to validation error')
            continue
        else:
            savelist_uri_setting = get_savelist_setting(task_uri, savelist)
            # update savelist
            if task_before is None:
                savelist[task_uri] = True
            else:
                savelist[task_uri] = model_will_be_imported(task_before, task)
            # save
            if do_save is True and savelist_uri_setting is True:
                log.info('Task saving to "' + str(task_uri) + '"')
                task.save()

        try:
            timeframe = TimeFrame.objects.get(task=task)
        except TimeFrame.DoesNotExist as e:
            timeframe = TimeFrame()
            timeframe.task = task
            log.info('Timeframe not in db. Created with task uri ' + str(task.uri))
        else:
            log.info('Timeframe does exist. Loaded from task uri ' + str(task.uri))

        timeframe_node = task_node.find('timeframe')
        save_validator = False
        if timeframe_node.find('start_attribute') is not None:
            try:
                start_attribute_uri = timeframe_node.find('start_attribute').get(get_ns_tag('dc:uri', nsmap))
                timeframe.start_attribute = Attribute.objects.get(uri=start_attribute_uri)
            except Attribute.DoesNotExist:
                pass

        if timeframe_node.find('end_attribute') is not None:
            try:
                end_attribute_uri = timeframe_node.find('end_attribute').get(get_ns_tag('dc:uri', nsmap))
                timeframe.end_attribute = Attribute.objects.get(uri=end_attribute_uri)
            except Attribute.DoesNotExist:
                pass

        days_before = get_value_from_treenode(timeframe_node, 'days_before')
        if days_before.isdigit() is True:
            save_validator = True
            timeframe.days_before = get_value_from_treenode(timeframe_node, 'days_before')

        days_after = get_value_from_treenode(timeframe_node, 'days_after')
        if days_after.isdigit() is True:
            save_validator = True
            timeframe.days_after = get_value_from_treenode(timeframe_node, 'days_after')

        if save_validator is True:
            timeframe.save()

    return savelist
