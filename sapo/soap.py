from collections import OrderedDict
from os.path import abspath, dirname, join, normpath

from sapo import xml

NSMAP = {
    'env': 'http://schemas.xmlsoap.org/soap/envelope/',
    'soap': 'http://schemas.xmlsoap.org/wsdl/soap/',
    'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
    'xsd': 'http://www.w3.org/2001/XMLSchema'
}


class WSDL:
    docs = OrderedDict()
    types = OrderedDict()
    services = OrderedDict()

    def __init__(self, path):
        self.resolve_docs(path)

        self.schema = self.get_schema()

        if self.schema is None:
            raise ValueError('Missing schema')

        self.xml = next(iter(self.docs))

    def resolve_docs(self, path):
        doc = xml.from_path(path)
        obj = xml.to_dict(doc.getroot())

        url = dirname(abspath(doc.docinfo.URL))

        for d in doc.findall('wsdl:import', namespaces=NSMAP):
            location = d.attrib['location']
            # namespace = obj['@namespace']
            new_url = normpath(join(url, location))
            self.resolve_docs(new_url)

        tns = obj['@targetNamespace']

        self.docs[tns] = doc

        types = doc.find('wsdl:types', namespaces=NSMAP)
        if types is not None:
            self.types[tns] = types

        service = doc.find('wsdl:service', namespaces=NSMAP)
        if service is not None:
            self.services[tns] = service

    def get_schema(self):
        for tns, types in self.types.items():
            return types.find('xsd:schema', namespaces=NSMAP)
        return None

    def validate(self, message, server=False):
        for tns, types in self.types.items():
            schema = types.find('xsd:schema', namespaces=NSMAP)

            if schema is None:
                continue

            try:
                xml.validate(schema, message)
            except xml.ValidationErrors as e:
                if 'No matching global declaration available for the validation root' in str(e):
                    continue
                raise ServerError(e) if server else ClientError(e)

    def __bytes__(self):
        return xml.to_bytes(self.xml, declaration=True)


class Envelope:
    """
    A SOAP message is an XML document that consists of a mandatory
    SOAP envelope, an optional SOAP header, and a mandatory SOAP body.
    """
    @staticmethod
    def enclose(content):
        f = xml.factory(NSMAP['env'])
        return xml.to_bytes(f.Envelope(f.Body(content)))

    @staticmethod
    def disclose(body):
        """
        Errors:
            Check if is Envelope
            Wrong envelope version (versionMismatch FAULT)
        """
        try:
            envelope = xml.from_string(body)
        except xml.ValidationErrors as e:
            raise ClientError(e)

        try:
            body = envelope.find('env:Body', namespaces=NSMAP)
        except TypeError as e:
            raise ClientError('Missing body element')

        try:
            operation = body[0]
        except IndexError as e:
            raise ClientError('Missing operation element')

        try:
            message = operation[0]
        except IndexError as e:
            raise ClientError('Missing message element')

        return operation.tag, xml.to_object(message)

    def __bytes__(self):
        return xml.to_bytes(self.xml)


class Fault:
    CODES = {
        'soap:VersionMismatch': 'SOAP Version Mismatch Error',
        'soap:MustUnderstand': 'SOAP Must Understand Error',
        'soap:Client': 'Client Error',
        'soap:Server': 'Server Error'
    }

    def __init__(self, code, detail, actor=None):
        """
        Manage:
            VersionMismatch
            MustUnderstand

            faultactor
        """
        f = xml.factory(NSMAP['env'])

        self.envelope = f.Envelope(f.Body(f.Fault(
            f.faultcode(code),
            f.faultstring(Fault.CODES[code]),
            f.detail(detail),
        )))

    def __bytes__(self):
        return xml.to_bytes(self.envelope)


class SoapError(Exception):
    def __init__(self, message):
        self.fault = Fault(self.code, str(message))


class ServerError(SoapError):
    code = 'soap:Server'


class ClientError(SoapError):
    code = 'soap:Client'


class OperationError(ClientError):
    def __init__(self):
        self.fault = Fault(self.code, 'Operation not found')
