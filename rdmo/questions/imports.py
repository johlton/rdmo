import logging

from django.core.exceptions import ValidationError

from rdmo.core.imports import get_savelist_setting, get_value_from_treenode, model_will_be_imported
from rdmo.core.utils import get_ns_map, get_ns_tag, get_uri
from rdmo.domain.models import AttributeEntity

from .models import Catalog, Section, Subsection, QuestionEntity, Question
from .validators import CatalogUniqueKeyValidator, SectionUniquePathValidator, SubsectionUniquePathValidator, QuestionEntityUniquePathValidator, QuestionUniquePathValidator

log = logging.getLogger(__name__)


def import_catalog(catalog_node, savelist={}, do_save=False):
    nsmap = get_ns_map(catalog_node.getroot())
    catalog_uri = get_uri(catalog_node, nsmap)
    log.info('Importing catalog ' + catalog_uri)

    try:
        catalog = Catalog.objects.get(uri=catalog_uri)
        catalog_before = catalog
    except Catalog.DoesNotExist:
        log.info('Catalog not in db. Created with uri ' + str(catalog_uri))
        catalog = Catalog()
        catalog_before = None
    else:
        log.info('Catalog does exist. Loaded from uri ' + str(catalog_uri))

    catalog.uri_prefix = catalog_uri.split('/questions/')[0]
    catalog.key = catalog_uri.split('/')[-1]
    catalog.comment = get_value_from_treenode(catalog_node, get_ns_tag('dc:comment', nsmap))
    catalog.order = get_value_from_treenode(catalog_node, 'order')

    for element in catalog_node.findall('title'):
        setattr(catalog, 'title_' + element.attrib['lang'], element.text)

    try:
        CatalogUniqueKeyValidator(catalog).validate()
    except ValidationError:
        log.info('Catalog not saving "' + str(catalog_uri) + '" due to validation error')
        pass
    else:
        savelist_uri_setting = get_savelist_setting(catalog_uri, savelist)
        # update savelist
        if catalog_before is None:
            savelist[catalog_uri] = True
        else:
            savelist[catalog_uri] = model_will_be_imported(catalog_before, catalog)
        # save
        if do_save is True and savelist_uri_setting is True:
            log.info('Catalog saving to "' + str(catalog_uri) + '"')
            catalog.save()

    for section_node in catalog_node.find('sections').findall('section'):
        savelist = import_section(section_node, nsmap, savelist=savelist, do_save=do_save, catalog=catalog)

    return savelist


def import_section(section_node, nsmap, savelist, do_save, catalog=None):
    section_uri = get_uri(section_node, nsmap)
    log.info('Importing section ' + section_uri)

    try:
        section = Section.objects.get(uri=section_uri)
        section_before = section
    except Section.DoesNotExist:
        log.info('Section not in db. Created with uri ' + str(section_uri))
        section = Section()
        section_before = None
    else:
        log.info('Section does exist. Loaded from uri ' + str(section_uri))

    section.uri_prefix = section_uri.split('/questions/')[0]
    section.key = section_uri.split('/')[-1]
    section.comment = get_value_from_treenode(section_node, get_ns_tag('dc:comment', nsmap))
    section.catalog = catalog
    section.order = get_value_from_treenode(section_node, 'order')

    for element in section_node.findall('title'):
        setattr(section, 'title_' + element.attrib['lang'], element.text)

    try:
        SectionUniquePathValidator(section).validate()
    except ValidationError:
        log.info('Section not saving "' + str(section_uri) + '" due to validation error')
        pass
    else:
        savelist_uri_setting = get_savelist_setting(section_uri, savelist)
        # update savelist
        if section_before is None:
            savelist[section_uri] = True
        else:
            savelist[section_uri] = model_will_be_imported(section_before, section)
        # save
        if do_save is True and savelist_uri_setting is True:
            log.info('Section saving to "' + str(section_uri) + '"')
            section.save()

    try:
        for subsection_node in section_node.find('subsections').findall('subsection'):
            savelist = import_subsection(subsection_node, nsmap, savelist, do_save, section=section)
    except AttributeError:
        pass

    return savelist


def import_subsection(subsection_node, nsmap, savelist, do_save, section=None):
    subsection_uri = get_uri(subsection_node, nsmap)
    log.info('Importing subsection ' + subsection_uri)

    try:
        subsection = Subsection.objects.get(uri=subsection_uri)
        subsection_before = subsection
    except Subsection.DoesNotExist:
        log.info('Subsection not in db. Created with uri ' + str(subsection_uri))
        subsection = Subsection()
        subsection_before = None
    else:
        log.info('Subsection does exist. Loaded from uri ' + str(subsection_uri))

    subsection.uri_prefix = subsection_uri.split('/questions/')[0]
    subsection.key = subsection_uri.split('/')[-1]
    subsection.comment = get_value_from_treenode(subsection_node, get_ns_tag('dc:comment', nsmap))
    subsection.section = section
    subsection.order = get_value_from_treenode(subsection_node, 'order')

    for element in subsection_node.findall('title'):
        setattr(subsection, 'title_' + element.attrib['lang'], element.text)

    try:
        SubsectionUniquePathValidator(subsection).validate()
    except ValidationError:
        log.info('Subsection not saving "' + str(subsection_uri) + '" due to validation error')
    else:
        savelist_uri_setting = get_savelist_setting(subsection_uri, savelist)
        # update savelist
        if subsection_uri is None:
            savelist[subsection_uri] = True
        else:
            savelist[subsection_uri] = model_will_be_imported(subsection_before, subsection)
        # save
        log.debug('---')
        log.debug(do_save)
        log.debug(savelist_uri_setting)
        if do_save is True and savelist_uri_setting is True:
            log.info('Subsection saving to "' + str(subsection_uri) + '"')
            subsection.save()

    log.debug(subsection_node.find('entities'))
    for questionset_node in subsection_node.find('entities').findall('questionset'):

        savelist = import_questionset(questionset_node, nsmap, savelist, do_save, subsection=subsection)
    for question_node in subsection_node.find('entities').findall('question'):
        savelist = import_question(question_node, nsmap, savelist, do_save, subsection=subsection)

    return savelist


def import_questionset(questionset_node, nsmap, savelist, do_save, subsection=None):
    questionset_uri = get_uri(questionset_node, nsmap)
    log.info('Importing questionset ' + questionset_uri)

    try:
        questionset = QuestionEntity.objects.get(uri=questionset_uri)
        questionset_before = questionset
    except QuestionEntity.DoesNotExist:
        log.info('Questionset not in db. Created with uri ' + str(questionset_uri))
        questionset = QuestionEntity()
        questionset_before = None
    else:
        log.info('Questionset does exist. Loaded from uri ' + str(questionset_uri))

    questionset.uri_prefix = questionset_uri.split('/questions/')[0]
    questionset.key = questionset_uri.split('/')[-1]
    questionset.comment = get_value_from_treenode(questionset_node, get_ns_tag('dc:comment', nsmap))
    questionset.subsection = subsection
    questionset.order = get_value_from_treenode(questionset_node, 'order')

    for element in questionset_node.findall('help'):
        setattr(questionset, 'help_' + element.attrib['lang'], element.text)

    try:
        urimap = questionset_node.find('attribute_entity').attrib
        nstag = get_ns_tag('dc:uri', nsmap)
        attribute_entity_uri = urimap[nstag]
        questionset.attribute_entity = AttributeEntity.objects.get(uri=attribute_entity_uri)
    except (AttributeError, AttributeEntity.DoesNotExist):
        questionset.attribute_entity = None

    try:
        QuestionEntityUniquePathValidator(questionset).validate()
    except ValidationError:
        log.info('Questionset not saving "' + str(questionset_uri) + '" due to validation error')
        pass
    else:
        savelist_uri_setting = get_savelist_setting(questionset_uri, savelist)
        # update savelist
        if questionset_uri is None:
            savelist[questionset_uri] = True
        else:
            savelist[questionset_uri] = model_will_be_imported(questionset_before, subsection)
        # save
        if do_save is True and savelist_uri_setting is True:
            log.info('Questionset saving to "' + str(questionset_uri) + '"')
            questionset.save()

    for question_node in questionset_node.find('questions').findall('question'):
        savelist = import_question(question_node, nsmap, savelist, do_save, subsection=subsection, parent=questionset)

    return savelist


def import_question(question_node, nsmap, savelist, do_save, subsection=None, parent=None):
    question_uri = get_uri(question_node, nsmap)
    try:
        question = Question.objects.get(uri=question_uri)
        question_before = question
    except Question.DoesNotExist:
        log.info('Question not in db. Created with uri ' + str(question_uri))
        question = Question()
        question_before = None
    else:
        log.info('Question does exist. Loaded from uri ' + str(question_uri))

    question.uri_prefix = question_uri.split('/questions/')[0]
    question.key = question_uri.split('/')[-1]
    question.comment = get_value_from_treenode(question_node, get_ns_tag('dc:comment', nsmap))
    question.subsection = subsection
    question.parent = parent
    question.order = get_value_from_treenode(question_node, 'order')
    question.widget_type = get_value_from_treenode(question_node, 'widget_type')

    for element in question_node.findall('text'):
        setattr(question, 'text_' + element.attrib['lang'], element.text)
    for element in question_node.findall('help'):
        setattr(question, 'help_' + element.attrib['lang'], element.text)
    try:
        urimap = question_node.find('attribute_entity').attrib
        nstag = get_ns_tag('dc:uri', nsmap)
        attribute_entity_uri = urimap[nstag]
        question.attribute_entity = AttributeEntity.objects.get(uri=attribute_entity_uri)
    except (AttributeError, AttributeEntity.DoesNotExist):
        question.attribute_entity = None
    try:
        QuestionUniquePathValidator(question).validate()
    except ValidationError:
        log.info('Question not saving "' + str(question_uri) + '" due to validation error')
        pass
    else:
        savelist_uri_setting = get_savelist_setting(question_uri, savelist)
        # update savelist
        if question_uri is None:
            savelist[question_uri] = True
        else:
            savelist[question_uri] = model_will_be_imported(question_before, question)
        # save
        if do_save is True and savelist_uri_setting is True:
            log.info('Question saving to "' + str(question_uri) + '"')
            question.save()

    return savelist
