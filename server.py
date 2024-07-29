import os
import argparse
import http.server as httpserver

from datetime import datetime


class ServerException(Exception):
    def __str__(self):
        return "Server error"


class CaseNoFile:
    """
        File or directory does not exist
    """

    @staticmethod
    def test(handler):
        return not os.path.exists(handler.full_path)

    def act(self, handler):
        raise ServerException("'{0}' not found".format(handler.path))


class CaseExistingFile:
    """
        File exists
    """

    @staticmethod
    def test(handler):
        return os.path.isfile(handler.full_path)

    @staticmethod
    def act(handler):
        handler.handle_file(handler.full_path)


class CaseAlwaysFail:
    """
        Base case if nothing else worked
    """

    @staticmethod
    def test(handler):
        return True

    def act(self, handler):
        raise ServerException("Unknown object '{0}'".format(handler.path))


class CaseDirectoryIndexFile:
    """
        Serve index.html page for a directory
    """

    @staticmethod
    def index_path(handler):
        return os.path.join("templates", handler.full_path, "index.html")

    def test(self, handler):
        return os.path.isdir(handler.full_path) and os.path.isfile(self.index_path(handler))

    def act(self, handler):
        handler.handle_file(self.index_path(handler))


class CaseDirectoryNoIndexFile:
    """
        Serve listing for a directory without an index.html page
    """

    @staticmethod
    def index_path(handler):
        return os.path.join(handler.full_path, "index.html")

    def test(self, handler):
        return os.path.isdir(handler.full_path) and not os.path.isfile(self.index_path(handler))

    @staticmethod
    def act(handler):
        handler.list_dir(handler.full_path)


class CaseCGIFile:
    """
        Something runnable
    """

    @staticmethod
    def test(handler):
        return os.path.isfile(handler.full_path) and handler.full_path.endswith(".py")

    @staticmethod
    def act(handler):
        handler.run_cgi(handler.full_path)


class RequestHandler(httpserver.BaseHTTPRequestHandler):
    """
        Handles HTTP requests by returning a fixed 'page'
    """

    full_path = None

    cases = [
        CaseExistingFile, CaseNoFile, CaseDirectoryIndexFile, CaseDirectoryNoIndexFile, CaseAlwaysFail,
        CaseCGIFile
    ]

    page = """
        <html>
            <body>
                <table>
                    <tr>  <td>Header</td>         <td>Value</td>          </tr>
                    <tr>  <td>Date and time</td>  <td>{date_time}</td>    </tr>
                    <tr>  <td>Client host</td>    <td>{client_host}</td>  </tr>
                    <tr>  <td>Client port</td>    <td>{client_port}s</td> </tr>
                    <tr>  <td>Command</td>        <td>{command}</td>      </tr>
                    <tr>  <td>Path</td>           <td>{path}</td>         </tr>
                </table>
            </body>
        </html>
    """

    error = """
        <html>
            <body>
                <h1>Error accessing {path}</h1>
                <p>{msg}</p>
            </body>
        </html>
    """

    listing_page = """
        <html>
            <body>
                <ul>
                    {0}
                </ul>
            </body>
        </html>
    """

    def send_page(self, page):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Content-length', str(len(self.page)))
        self.end_headers()
        self.wfile.write(page.encode('utf-8'))

    def create_page(self):
        values = {
            'date_time': str(datetime.now()),
            'client_host': self.client_address[0],
            'client_port': self.client_address[1],
            'command': self.command,
            'path': self.path
        }
        page = self.page.format(**values)
        return page

    def handle_file(self, full_path):
        try:
            with open(full_path, 'rb') as reader:
                content = reader.read()
            self.send_content(content)
        except IOError as ex:
            msg = "'{0}' cannot be read: {1}".format(self.path, ex)
            self.handle_error(msg)

    def run_cgi(self, full_path):
        cmd = "python {0}".format(full_path)
        child_sdtin, child_stdout = os.popen(cmd)
        child_sdtin.close()
        data = child_stdout.read()
        child_stdout.close()
        self.send_content(data)

    def list_dir(self, full_path):
        try:
            entries = os.listdir(full_path)
            bullets = ['<li>{0}</li>'.format(e) for e in entries if not e.startswith('.')]
            page = self.listing_page.format('<br/>'.join(bullets))
            self.send_content(page.encode('utf-8'))
        except OSError as ex:
            msg = "'{0}' cannot be listed: {1}".format(self.path, ex)
            self.handle_error(msg)

    def handle_error(self, error):
        content = self.error.format(path=self.path, msg=error)
        self.send_content(content.encode('utf-8'), 404)

    def send_content(self, content, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.send_header('Content-length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        try:
            # Figure out what exactly is being requested
            self.full_path = os.getcwd() + self.path

            # Figure out how to handle it
            for case in self.cases:
                handler = case()
                if handler.test(self):
                    handler.act(self)
                    break

        except Exception as ex:
            self.handle_error(ex)


class Messages:

    @staticmethod
    def success(message):
        color_format = ';'.join([str(1), str(32), str(48)])
        print('\x1b[%sm %s \x1b[0m' % (color_format, message))

    @staticmethod
    def error(message):
        color_format = ';'.join([str(1), str(31), str(48)])
        print('\x1b[%sm %s \x1b[0m' % (color_format, message))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run a simple HTTP server.')
    parser.add_argument('-p', '--port', type=int, default=8000, help='Port to run the server on.')
    args = parser.parse_args()

    os.system('cls' if os.name == 'nt' else 'clear')
    serverAddress = ('', args.port)
    server = httpserver.HTTPServer(serverAddress, RequestHandler)
    Messages.success("Server running on http://localhost:{}".format(args.port))
    server.serve_forever()
