from collections import OrderedDict

from lxml import etree as et, objectify
from lxml.builder import ElementMaker

ValidationErrors = (et.DocumentInvalid, et.XMLSyntaxError)

PARSER = et.XMLParser(resolve_entities=False, load_dtd=True, remove_comments=True)


def factory(ns=''):
    if ns:
        return ElementMaker(namespace=ns, nsmap={None: ns})
    return ElementMaker()


def from_path(path):
    return et.parse(path, PARSER)


def validate(schema, message):
    et.XMLSchema(schema).assertValid(message)


def to_object(root, clean=False):
    root = strip_ns(root) if clean else root
    return objectify.fromstring(to_bytes(root))


def from_string(string):
    return et.fromstring(string, PARSER)


def to_bytes(root, declaration=False):
        return et.tostring(root, xml_declaration=declaration, encoding='utf-8')


def to_dict(r):
    d = OrderedDict()
    d.update(('@' + k, v) for k, v in r.attrib.items())
    d['#tag'] = r.tag
    d['#text'] = r.text.strip() if r.text else ''
    d['#nsmap'] = r.nsmap
    for e in r:
        t = to_dict(e)
        if e.tag not in d:
            d[e.tag] = []
        d[e.tag].append(t)
    return d


def from_dict(d):
    r = et.Element(d['#tag'], nsmap=d['#nsmap'])
    for k, v in d.items():
        if k == '#text' and v:
            r.text = str(v)
        elif k.startswith('@'):
            r.set(k[1:], v)
        elif isinstance(v, list):
            for e in v:
                r.append(from_dict(e))
    return r


def get_ns(element):
    return element.xpath('namespace-uri(.)')


def strip_ns(tree):
    query = "descendant-or-self::*[namespace-uri()!='']"
    for element in tree.xpath(query):
        element.tag = et.QName(element).localname
    return tree
