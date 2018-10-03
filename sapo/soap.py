from sapo import xml

NSMAP = {
    'env': 'http://schemas.xmlsoap.org/soap/envelope/',
}


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
    def disclose(envelope_string):
        """
        Should supports Header, multiple child elements, no message?
        Wrong envelope version (versionMismatch FAULT)
        Check NSMAP['env'] by SOAP version
        """
        try:
            envelope = xml.from_string(envelope_string)
        except xml.ValidationErrors as e:
            raise ClientError(e)

        envelope_tag = xml.et.QName(envelope.tag)

        try:
            # assert envelope_tag.namespace == NSMAP['env']
            assert envelope_tag.localname == 'Envelope'
        except AssertionError:
            raise ClientError('Missing Envelope')

        body = envelope.find('env:Body', namespaces=NSMAP)

        try:
            operation = body[0]
        except TypeError as e:
            raise ClientError('Missing body element')
        except IndexError as e:
            raise ClientError('Missing operation element')

        operation_tag = xml.et.QName(operation.tag)

        try:
            message = operation[0]
        except IndexError as e:
            raise ClientError('Missing message element')

        return operation_tag, xml.to_object(message)

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
    def __init__(self, message=None):
        message = str(message) if message else self.default
        self.fault = Fault(self.code, message)


class ServerError(SoapError):
    default = 'A server error occurred. Please contact the administrator.'
    code = 'soap:Server'


class ClientError(SoapError):
    default = 'An unknown error occurred.'
    code = 'soap:Client'


class OperationError(ClientError):
    def __init__(self):
        self.fault = Fault(self.code, 'Operation not found')


class MessageError(ClientError):
    def __init__(self, msg_name):
        error_msg = 'Invalid message \'{}\''.format(msg_name)
        self.fault = Fault(self.code, error_msg)
