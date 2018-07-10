import logging

from django.core.exceptions import ValidationError

from rdmo.core.imports import get_savelist_setting, get_value_from_treenode, make_bool, model_will_be_imported
from rdmo.core.utils import get_ns_map, get_ns_tag, get_uri

from .models import OptionSet, Option
from .validators import OptionSetUniqueKeyValidator

log = logging.getLogger(__name__)


def import_options(optionsets_node, savelist={}, do_save=False):
    log.info('Importing options')
    nsmap = get_ns_map(optionsets_node.getroot())

    for optionset_node in optionsets_node.findall('optionset'):
        optionset_uri = get_uri(optionset_node, nsmap)

        try:
            optionset = OptionSet.objects.get(uri=optionset_uri)
            optionset_before = optionset
        except OptionSet.DoesNotExist:
            optionset = OptionSet()
            log.info('Optionset not in db. Created with uri ' + str(optionset_uri))
            optionset_before = None
        else:
            log.info('Optionset does exist. Loaded from uri ' + str(optionset_uri))

        optionset.uri_prefix = optionset_uri.split('/options/')[0]
        optionset.key = optionset_uri.split('/')[-1]
        optionset.comment = get_value_from_treenode(optionset_node, get_ns_tag('dc:comment', nsmap))
        optionset.order = get_value_from_treenode(optionset_node, 'order')
        try:
            OptionSetUniqueKeyValidator(optionset).validate()
        except ValidationError:
            log.info('Optionset not saving "' + str(optionset_uri) + '" due to validation error')
            pass
        else:
            savelist_uri_setting = get_savelist_setting(optionset_uri, savelist)
            # update savelist
            if optionset_before is None:
                savelist[optionset_uri] = True
            else:
                savelist[optionset_uri] = model_will_be_imported(optionset_before, optionset)
            # save
            if do_save is True and savelist_uri_setting is True:
                log.info('Optionset saving to "' + str(optionset_uri) + '"')
                optionset.save()

        for options_node in optionset_node.findall('options'):
            for option_node in options_node.findall('option'):
                option_uri = get_uri(option_node, nsmap)

                try:
                    option = Option.objects.get(uri=option_uri)
                except Option.DoesNotExist:
                    log.info(Option.DoesNotExist)
                    option = Option()

                option.optionset = optionset
                option.uri_prefix = option_uri.split('/options/')[0]
                option.key = option_uri.split('/')[-1]
                option.comment = get_value_from_treenode(option_node, get_ns_tag('dc:comment', nsmap))
                option.order = get_value_from_treenode(option_node, 'order')

                for element in option_node.findall('text'):
                    setattr(option, 'text_' + element.attrib['lang'], element.text)
                option.additional_input = make_bool(get_value_from_treenode(option_node, 'additional_input'))

                try:
                    OptionSetUniqueKeyValidator(optionset).validate()
                except ValidationError:
                    log.info('Optionset not saving "' + str(option_uri) + '" due to validation error')
                    pass
                else:
                    savelist_uri_setting = get_savelist_setting(option_uri, savelist)
                    # update savelist
                    if optionset_before is None:
                        savelist[option_uri] = True
                    else:
                        savelist[option_uri] = model_will_be_imported(optionset_before, optionset)
                    # save
                    if do_save is True and savelist_uri_setting is True:
                        log.info('Option saving to "' + str(option_uri) + '"')
                        option.save()
    return savelist
