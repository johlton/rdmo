import logging

from django.core.exceptions import ValidationError

from rdmo.core.utils import get_ns_map, get_uri

from rdmo.core.imports import get_savelist_setting, model_will_be_imported
from .models import View
from .validators import ViewUniqueKeyValidator

log = logging.getLogger(__name__)


def import_views(views_node, savelist={}, do_save=False):
    log.info('Importing views')
    nsmap = get_ns_map(views_node.getroot())

    for view_node in views_node.findall('view'):
        view_uri = get_uri(view_node, nsmap)

        try:
            view = View.objects.get(uri=view_uri)
            view_before = view
        except View.DoesNotExist:
            view = View()
            log.info('View not in db. Created with uri ' + view_uri)
            view_before = None
        else:
            log.info('View does exist. Loaded from uri ' + view_uri)

        view.uri_prefix = view_uri.split('/views/')[0]
        view.key = view_uri.split('/')[-1]

        for element in view_node.findall('title'):
            setattr(view, 'title_' + element.attrib['lang'], element.text)
        for element in view_node.findall('help'):
            setattr(view, 'help_' + element.attrib['lang'], element.text)

        try:
            ViewUniqueKeyValidator(view).validate()
        except ValidationError:
            log.info('View not saving "' + str(view.key) + '" due to validation error')
            pass
        else:
            savelist_uri_setting = get_savelist_setting(view_uri, savelist)
            # update savelist
            if view_before is None:
                savelist[view_uri] = True
            else:
                savelist[view_uri] = model_will_be_imported(view_before, view)
            # save
            if do_save is True and savelist_uri_setting is True:
                log.info('View saving to "' + str(view_uri) + '"')
                view.save()
            return savelist
