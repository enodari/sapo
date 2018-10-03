from os.path import abspath

from lxml import etree as et, objectify
from lxml.builder import ElementMaker

ValidationErrors = (et.DocumentInvalid, et.XMLSyntaxError)

PARSER = et.XMLParser(
    resolve_entities=False, load_dtd=True, remove_comments=True
)


def factory(ns=''):
    if ns:
        return ElementMaker(namespace=ns, nsmap={None: ns})
    return ElementMaker()


def from_path(path):
    return et.parse(abspath(path), PARSER)


def to_object(root, clean=False):
    root = strip_ns(root) if clean else root
    return objectify.fromstring(to_bytes(root))


def from_string(string):
    return et.fromstring(string, PARSER)


def to_bytes(root, declaration=False):
    return et.tostring(root, xml_declaration=declaration, encoding='utf-8')


def get_ns(element):
    return et.QName(element).namespace


def qstring(string):
    if ':' in string:
        return string.split(':', 1)
    return 'tns', string


def strip_ns(tree):
    query = "descendant-or-self::*[namespace-uri()!='']"
    for element in tree.xpath(query):
        element.tag = et.QName(element).localname
    return tree
