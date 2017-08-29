"""
This serves `/services/public/user/directory/Notebook.ipynb` and other files.
"""

import os
import re
import glob
import mimetypes
import shutil
from urllib.parse import urlparse
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado.web import RequestHandler, Application, HTTPError
from tornado.log import app_log

import nbformat
from nbconvert.exporters import HTMLExporter, PDFExporter
from nbformat.v4 import new_markdown_cell

class PublicHandler(RequestHandler):
    def get(self, user, filename):
        ## filename can have a path on it
        prefix = os.environ['JUPYTERHUB_SERVICE_PREFIX']
        next = "%s/%s/%s" % (prefix, user, filename)
        filesystem_path = "/home/%s/public_html/%s" % (user, filename)
        if filename and filename.endswith(".raw.ipynb"):
            filename = filename[:-10] + ".ipynb"
            self.set_header('Content-Type', "application/json")
            with open("/home/%s/public_html/%s" % (user, filename), "rb") as fp:
                self.write(fp.read())
            return
        elif os.path.isfile(filesystem_path): # download, raw, or view notebook
            command = "view"
            if len(self.get_arguments("view")) > 0:
                command = "view"
            elif len(self.get_arguments("download")) > 0:
                command = "download" 
            elif len(self.get_arguments("pdf")) > 0:
                command = "pdf" 
            elif len(self.get_arguments("raw")) > 0:
                command = "raw" 
            # else:  view
            if filename.endswith(".ipynb"):
                if command in ["view", "pdf"]:
                    if command == "view":
                        exporter = HTMLExporter(template_file='full-tabs')
                    else:
                        exporter = PDFExporter(latex_count=1)
                    
                    nb_json = nbformat.read("/home/%s/public_html/%s" % (user, filename), as_version=4)
                    if command == "pdf":
                        self.set_header('Content-Type', "application/pdf")
                        base_filename = os.path.basename(filename)
                        self.set_header('Content-Disposition', 'attachment; filename="%s"' % base_filename)
                    else: # render as HTML
                        # add header/footer:
                        path = "%s/%s" % (prefix, user)
                        parts = [(path, path)]
                        for part in filename.split("/")[:-1]:
                            path += "/" + part
                            parts.append((path, part))
                        breadcrumbs = " / ".join(map(lambda pair: '<a href="%s" target="_blank">%s</a>' % pair, parts))
                        env = {
                            "breadcrumbs": breadcrumbs,
                            "url": next + "?download",
                            "prefix": prefix,
                        }
                        cell = new_markdown_cell(source="""<table width="100%" style="border: none;">
<tr style="border: none;">
  <td style="border: none;" width="100px">
    <img src="https://blog.jupyter.org/content/images/2015/02/jupyter-sq-text.png" width="100"/> 
  </td>
  <td style="border: none;" width="50%">
    <h2><a href="/">Jupyter at Bryn Mawr College</a></h2>
  </td>
  <td style="border: none;">
                        <a href="{prefix}/dblank/Jupyter%20Help.ipynb" title="Help">
            <img src="https://upload.wikimedia.org/wikipedia/commons/a/ae/High-contrast-help-browser.svg" style="border: none" width="32"></img> 
        </a>
  </td>
  <td style="border: none;">
        <a href="{url}" title="Download Notebook" download>
            <img src="https://upload.wikimedia.org/wikipedia/commons/8/8d/Download_alt_font_awesome.svg" style="border: none" width="32"></img>
        </a>
  </td>
</tr>
<tr style="border: none;">
  <td colspan="4" style="border: none;">
      <b>Public notebooks:</b> {breadcrumbs}
  </td>
</tr>
</table>""".format(**env))
                        nb_json["cells"].insert(0, cell)
                    (body, resources) = exporter.from_notebook_node(nb_json)
                    body = body.replace('<title>Notebook</title>', '<title>%s</title>' % filename.split("/")[-1])
                    self.write(body)
                elif command == "download": # download notebook json
                    self.download(user, filename, "text/plain")
                else: # raw, just get file contents
                    self.set_header('Content-Type', "application/json")
                    with open("/home/%s/public_html/%s" % (user, filename), "rb") as fp:
                        self.write(fp.read())
            else: # some other kind of file
                # FIXME: how to get all of custom stuff?
                if True: # whatever, just get or download it
                    base_filename = os.path.basename(filename)
                    base, ext = os.path.splitext(base_filename)
                    app_log.info("extension is: %s" % ext)
                    if base_filename == "custom.css":
                        file_path = "/home/%s/.ipython/profile_default/static/custom/custom.css" % user
                        self.set_header('Content-Type', "text/css")
                        with open(file_path, "rb") as fp:
                            self.write(fp.read())
                    elif ext in [".txt", ".html", ".js", ".css", ".pdf", ".gif", ".jpeg", ".jpg", ".png"]: # show in browser
                        app_log.info("mime: %s" % str(mimetypes.guess_type(filename)[0]))
                        self.set_header('Content-Type', mimetypes.guess_type(filename)[0])
                        with open("/home/%s/public_html/%s" % (user, filename), "rb") as fp:
                            self.write(fp.read())
                    else:
                        self.download(user, filename)
        else: # not a file; directory listing
            # filename can have a full path, and might be empty
            url_path = "%s/%s" % (prefix, user)
            ##
            path = "%s/%s" % (prefix, user)
            parts = [(path, path)]
            for part in filename.split("/")[:]:
                path += "/" + part
                parts.append((path, part))
            breadcrumbs = " / ".join(map(lambda pair: '<a href="%s" target="_blank">%s</a>' % pair, parts))
            ##
            # could be: images, images/, images/subdir, images/subdir/
            if not filename.endswith("/") and filename.strip() != "":
                filename += "/"
            files = glob.glob("/home/%s/public_html/%s*" % (user, filename))
            self.write("<h1>Jupyter Project at Bryn Mawr College</h1>\n")
            self.write("[<a href=\"/hub/login\">Home</a>] ")
            if self.get_current_user_name():
                self.write("[<a href=\"/user/%(current_user)s/tree\">%(current_user)s</a>] " % {"current_user": self.get_current_user_name()})
            self.write("<p/>\n")
            self.write("<p>Public notebooks: %s </p>\n" % breadcrumbs)
            self.write("<ol>\n")
            for absolute_filename in sorted(files):
                if os.path.isdir(absolute_filename): 
                    dir_path = absolute_filename.split("/")
                    dir_name = dir_path[-1]
                    public_path = "/".join(dir_path[dir_path.index("public_html") + 1:])
                    self.write("<li><a href=\"%(url_path)s/%(public_path)s\">%(dir_name)s</a></li>\n" % {"url_path": url_path, 
                                                                                                      "dir_name": dir_name,
                                                                                                      "public_path": public_path})
                else:
                    file_path, filename = absolute_filename.rsplit("/", 1)
                    dir_path = absolute_filename.split("/")
                    public_path = "/".join(dir_path[dir_path.index("public_html") + 1:])
                    variables = {"user": user, "filename": filename, "url_path": url_path, "next": next,
                                 "public_path": public_path}
                    if filename.endswith(".ipynb"):
                        if self.get_current_user_name():
                            self.write(("<li><a href=\"%(url_path)s/%(public_path)s\">%(filename)s</a> "+
                                        "(<a href=\"%(url_path)s/%(public_path)s?download\">download</a>" +
                                        ")</li>\n") % variables)
                        else:
                            self.write(("<li><a href=\"%(url_path)s/%(public_path)s\">%(filename)s</a> "+
                                        "(<a href=\"%(url_path)s/%(public_path)s?download\">download</a>)" +
                                        "</li>\n") % variables)
                    else:
                        # some other kind of file (eg, .zip, .css):
                        self.write("<li><a href=\"%(url_path)s/%(public_path)s\">%(filename)s</a></li>\n" % variables)
            self.write("</ol>\n")
            self.write("<hr>\n")
            self.write("<p><i>Please see <a href=\"{prefix}/dblank/Jupyter Help.ipynb\">Jupyter Help</a> for more information about this server.</i></p>\n".format(prefix=prefix))

    def download(self, user, filename, mime_type=None):
        self.download_file(filename, "/home/%s/public_html/%s" % (user, filename), mime_type)

    def download_file(self, filename, file_path, mime_type=None):
        # just download it
        # filename can be a full path + filename
        if os.path.exists(file_path):
            if mime_type is None:
                mime_type, encoding = mimetypes.guess_type(filename)
            if mime_type is None:
                mime_type = "text/plain"
            base_filename = os.path.basename(filename)
            self.set_header('Content-Type', mime_type)
            self.set_header('Content-Disposition', 'attachment; filename="%s"' % base_filename)
            fp = open(file_path, "rb")
            try:
                self.write(fp.read())
            except:
                # file read/write issue
                print("File IO issue")
            finally:
                fp.close()
        else:
            raise HTTPError(404)

    def get_current_user_name(self):
        user = self.get_current_user()
        if user:
            return user.name
        else:
            return None

def main():
    app = Application([
        (os.environ['JUPYTERHUB_SERVICE_PREFIX'] + r"/([^/]+)/?(.*)", PublicHandler),
    ])
    http_server = HTTPServer(app)
    url = urlparse(os.environ['JUPYTERHUB_SERVICE_URL'])
    http_server.listen(url.port, url.hostname)
    IOLoop.current().start()

if __name__ == '__main__':
    main()
