from os.path import dirname, join, normpath

from sapo import xml
from sapo.soap import ClientError, MessageError, OperationError, ServerError

NSMAP = {
    'env': 'http://schemas.xmlsoap.org/soap/envelope/',
    'soap': 'http://schemas.xmlsoap.org/wsdl/soap/',
    'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
    'xsd': 'http://www.w3.org/2001/XMLSchema'
}


class WSDL:
    def __init__(self, location):
        root_tree = xml.load_from_abs_path(location)
        root_nsmap = root_tree.getroot().nsmap

        self.root_tree = root_tree

        self.documents = {}
        self.schemas = {}
        self.operations = {}
        self.resolve_imports(location)

        service_node = root_tree.find('wsdl:service', namespaces=NSMAP)

        port_node = service_node.find('wsdl:port', namespaces=NSMAP)
        port_binding = port_node.get('binding')

        port_binding_ns, port_binding_name = xml.qstring(port_binding)

        binding_doc = self.documents[root_nsmap[port_binding_ns]]
        binding_node = self.get_el_by_name(binding_doc['tree'], 'wsdl:binding', port_binding_name)
        port_type = binding_node.get('type')

        port_type_ns, port_type_name = xml.qstring(port_type)

        port_type_doc = self.documents[binding_doc['nsmap'][port_type_ns]]
        port_type_node = self.get_el_by_name(port_type_doc['tree'], 'wsdl:portType', port_type_name)

        for operation_node in port_type_node.findall('wsdl:operation', namespaces=NSMAP):
            operation_name = operation_node.get('name')

            self.operations[operation_name] = {}

            for node in operation_node.iterchildren():
                msg = node.get('message')  # if not None
                msg_ns, msg_name = xml.qstring(msg)

                msg_tns = port_type_doc['nsmap'][msg_ns]
                msg_doc = self.documents[msg_tns]
                msg_node = self.get_el_by_name(msg_doc['tree'], 'wsdl:message', msg_name)

                part_node = msg_node.find('wsdl:part', namespaces=NSMAP)
                element = part_node.get('element')

                msg_name = xml.qstring(element)[1]
                msg_variety = xml.et.QName(node).localname

                self.operations[operation_name][msg_name] = {
                    'tns': msg_tns,
                    'variety': msg_variety
                }

    def resolve_imports(self, location):
        doc = xml.load_from_abs_path(location)

        tns = doc.getroot().get('targetNamespace')

        self.documents[tns] = {
            'tree': doc,
            'nsmap': doc.getroot().nsmap
        }

        base = dirname(location)

        for node in doc.findall('wsdl:import', namespaces=NSMAP):
            import_location = normpath(join(base, node.get('location')))
            self.resolve_imports(import_location)

        types = doc.find('wsdl:types', namespaces=NSMAP)
        if types is not None:
            schema = types.find('xsd:schema', namespaces=NSMAP)
            if schema is not None:
                self.schemas[tns] = schema

    def validate(self, operation_name, message, server=False):
        msg_name = xml.et.QName(message.tag).localname
        try:
            operation = self.operations[operation_name]
        except KeyError:
            raise OperationError()

        try:
            schema_tns = operation[msg_name]['tns']
        except KeyError:
            raise MessageError(msg_name)

        try:
            schema = self.schemas[schema_tns]
        except KeyError:
            raise ServerError('No schema found')

        try:
            xml.validate(schema, message)
            return True
        except xml.ValidationErrors as e:
            raise ServerError(e) if server else ClientError(e)

    def get_el_by_name(self, tree, tag, name):
        return tree.find(tag + '[@name=\'{}\']'.format(name), namespaces=NSMAP)

    def __bytes__(self):
        return xml.to_bytes(self.root_tree)
