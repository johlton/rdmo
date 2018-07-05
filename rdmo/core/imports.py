import hashlib
import logging
import re
import tempfile
import time
import defusedxml.ElementTree as ET

from random import randint
from django.conf import settings


log = logging.getLogger(__name__)


def make_bool(instring):
    r = None
    s = instring
    try:
        s = s.decode('utf-8')
    except AttributeError:
        pass
    truelist = ['True', 'true']
    falselist = ['False', 'false']
    if s in truelist:
        r = True
    elif s in falselist:
        r = False
    return r


def get_value_from_treenode(xml_node, element, what_to_get=None):
    r = ''
    try:
        if what_to_get == 'attrib':
            r = xml_node.find(element).attrib
        elif what_to_get == 'tag':
            r = xml_node.find(element).tag
        else:
            r = xml_node.find(element).text
    except Exception as e:
        log.debug('Unable to extract "' + element + '" from "' + str(xml_node) + '". ' + str(e))
        pass
    else:
        if r is None:
            r = ''
        try:
            r = r.encode('utf-8', 'ignore')
        except Exception as e:
            log.debug('Unable to decode string to utf-8: ' + str(e))
            pass
    return r


def generate_tempfile_name():
    t = int(round(time.time() * 1000))
    r = randint(10000, 99999)
    fn = tempfile.gettempdir() + '/upload_' + str(t) + '_' + str(r) + '.xml'
    return fn


def handle_uploaded_file(filedata):
    tempfilename = generate_tempfile_name()
    with open(tempfilename, 'wb+') as destination:
        for chunk in filedata.chunks():
            destination.write(chunk)
    return tempfilename


def validate_xml(tempfilename):
    tree = None
    roottag = None
    try:
        tree = ET.parse(tempfilename)
    except Exception as e:
        log.error('Xml parsing error: ' + str(e))
        pass
    else:
        root = tree.getroot()
        roottag = root.tag
    return roottag, tree


def hash_string(string):
    hash_object = hashlib.sha512(string)
    hex_dig = hash_object.hexdigest()
    return hex_dig


def rx_count(rx, string):
    return len(re.findall(rx, string))


def make_filename_token(filename):
    part1 = hash_string(settings.SECRET_KEY)
    part2 = hash_string(settings.SECRET_KEY[::-1])
    part3 = hash_string(filename)
    filename_token = \
        part1[0:rx_count('[a-z]', part1)] + \
        part2[rx_count('[1|2|3|5|7]', part2):] + \
        part3[0:rx_count('[1-9]', part3)]
    return filename_token


def is_filename_good(filename, fn_token):
    return make_filename_token(filename).strip() == fn_token.strip()


def model_will_be_imported(model1, model2):
    will_be_imported = False
    fields = model1._meta.get_fields()
    for field in fields:
        f1val = getattr(model1, field.name, None)
        f2val = getattr(model2, field.name, None)
        if f1val != f2val:
            will_be_imported = True
    return will_be_imported


def get_savelist_setting(uri, condition_savelist):
    r = True
    try:
        r = condition_savelist[uri]
    except KeyError:
        pass
    return r
