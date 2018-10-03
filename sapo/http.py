from sapo import soap, wsdl, xml

HTTP_200 = '200 OK'
HTTP_404 = '404 Not Found'
HTTP_405 = '405 Method Not Allowed'
HTTP_500 = '500 Internal Server Error'


class Response:
    def __init__(self, status, body=None):
        self.status = status
        self.body = bytes(body) or status.encode('utf-8')
        self.headers = [
            ('Content-Type', 'text/xml' if body else 'text/plain'),
            ('Content-Length', str(len(self.body)))
        ]


class Sapo:
    def __init__(self, location):
        self.wsdl = wsdl.WSDL(location)
        self.operations = {}

    def operation(self, name, methods=['POST']):
        def decorator(func):
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            self.operations[name] = {'methods': methods, 'func': wrapper}
            return wrapper
        return decorator

    def __call__(self, env, start_response):
        response = self.handle(
            env['PATH_INFO'],
            env['QUERY_STRING'].lower(),
            env['REQUEST_METHOD'].upper(),
            env['wsgi.input'].read(int(env.get('CONTENT_LENGTH', 0)))
        )

        start_response(response.status, response.headers)
        yield response.body

    def handle(self, path, query, method, body):
        if path != '/':
            return Response(HTTP_404)

        if method == 'GET':
            if query == 'wsdl':
                return Response(HTTP_200, self.wsdl)
        if method == 'POST':
            try:
                operation, request = soap.Envelope.disclose(body)
                self.wsdl.validate(operation, request)
                try:
                    response = self.operations[operation]['func'](xml.strip_ns(request))
                except KeyError:
                    raise soap.OperationError()
                except:
                    raise soap.ServerError()
                self.wsdl.validate(operation, response, server=True)
            except (soap.ClientError, soap.ServerError) as error:
                return Response(HTTP_500, error.fault)

            envelope = soap.Envelope.enclose(response)
            return Response(HTTP_200, envelope)
        return Response(HTTP_405)
