"""An example service authenticating with the Hub.

This serves `/services/accounts/`, authenticated with the Hub, showing the user their own info.
"""

import os
import pwd
import subprocess
from xkcdpass import xkcd_password
from getpass import getuser
from urllib.parse import urlparse
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado.web import RequestHandler, Application, authenticated
from jupyterhub.services.auth import HubAuthenticated

class AccountsHandler(HubAuthenticated, RequestHandler):
    hub_users = {getuser()} # the users allowed to access me

    @authenticated
    def get(self):
        user_model = self.get_current_user()
        self.set_header('content-type', 'text/html')
        if user_model["admin"]:
            self.write("""<!DOCTYPE html>
<html>
<body>

<h1>Create Jupyter Accounts</h1>

<p>Each line should be in one of the following forms:</p>

<pre>
   username                             OR
   username@address                     OR
   Real Name, username@school.edu       OR
   Real Name, username-email            OR
   Real Name, email@school.edu, username
</pre>

<form method="post" action="/services/accounts/">
  <textarea rows="30" cols="70" name="usernames"></textarea>
  <br><br>
  <b>Professor name and email:</b> <input size="50" type="text" name="prof_email"/> <br/>
  <b>Send Email:<b> <input type="checkbox" name="Send Email" value="send"></input><br/> 
  <b>Display Passwords:</b> <input type="checkbox" name="Display Passwords" value="display"></input> <br/> <br/>
  <input type="submit" value="Create Accounts">
</form>
</body>
</html>
            """)
        else:
            self.write("Not an admin!")

    @authenticated
    def post(self):
        user_model = self.get_current_user()
        usernames = self.get_argument('usernames').split("\n")
        prof_email = self.get_argument('prof_email')
        display = self.get_argument('Display Passwords', "") == "display"
        send_email = self.get_argument('Send Email', "") == "send"
        self.set_header('content-type', 'text/html')
        if user_model["admin"]:
            self.process_lines(usernames, prof_email, send_email, display)
        else:
            self.write("Not an admin!")

    def process_lines(self, lines, prof_email, send_email, display):
        """
        filename is a file: 
           username                             OR
           username@address                     OR
           Real Name, email+username            OR
           Real Name, email+username@address    OR
           Real Name, email@address, username
        """
        for line in lines:
            line = line.strip()
            if line.startswith("#") or line == "":
                continue
            data = [item.strip() for item in line.split(",")]
            if len(data) == 1: # USERNAME/EMAIL
                if "@" in data[0]:
                    email = data[0]
                    username = email.split("@")[0]
                else:
                    username = data[0]
                    email = data[0] + "@" + "brynmawr.edu" 
                realname = "Jupyter User"
            elif len(data) == 2: # REALNAME, USERNAME/EMAIL
                if "@" in data[1]:
                    realname = data[0]
                    email = data[1]
                    username = email.split("@")[0]
                else:
                    realname = data[0]
                    username = data[1]
                    email = data[1] + "@" + "brynmawr.edu"
            elif len(data) == 3: # REALNAME, EMAIL, USERNAME
                realname = data[0]
                email = data[1]
                username = data[2]
            else:
                self.write("invalid line: " + line + "; skipping! <br/><br/>")
                continue
            ### Now, let's see if there is an account:
            if not display:
                self.write("processing: %s %s %s... <br/><br/>" % (username, realname, email))
            account_info = get_user_info(username)
            if account_info:
                username = account_info[0]
                realname = account_info[4]
                self.write("Account exists! username: %s realname: %s <br/><br/>" %(username, realname))
                #continue ## Do it anyway
            # otherwise, make account
            gecos = "%s <%s>" % (realname, email)
            password = make_password("-w safe6 -n 4 --min 1 --max=6") 
            env = {
                "username": username,
                "gecos": gecos,
                "password": password,
                "prof_email": prof_email,
                "email": email,
                }
            #print("env:", env)
            system('useradd -m -d /home/{username} -c "{gecos}" {username}'.format(**env))
            system('echo {username}:{password} | chpasswd'.format(**env))
            if display:
                self.write("""
<pre>
===============================================
Bryn Mawr College
Jupyter Computer Resource

{prof_email}
-----------------------------------------------

Computer: http://jupyter.brynmawr.edu

User: {gecos}

Username     : {username}
Pass phrase  : {password}
Email address: {email}

Note: you must type any spaces in pass phrase when you login.


%< ---------------------------------------------
</pre>
""".format(**env))
            if send_email and env["email"]:
                message = """
Welcome to Computing at Bryn Mawr College!

You are currently enrolled in a course using this resource.

You will be given details in class on how to login and use the system
using the following information.

Computer: https://jupyter.brynmawr.edu/
Username: {username}
Password: {password}

If you have any questions, please check with your instructor
({prof_email}).

Thank you!
"""
                env["message"] = message.format(**env)
                system('echo -e "{message}" | mail -c "systems.cs.brynmawr.edu" -s "Computer Science Course Resources" {email}'.format(**env))

def make_password(arg_string=None):
    if arg_string is None:
        arg_string = "-w safe6 -n 4 --min 1 --max=6"
    argv = arg_string.split()
    parser = xkcd_password.XkcdPassArgumentParser(prog="xkcdpass")

    options = parser.parse_args(argv)
    xkcd_password.validate_options(parser, options)

    my_wordlist = xkcd_password.generate_wordlist(
        wordfile=options.wordfile,
        min_length=options.min_length,
        max_length=options.max_length,
        valid_chars=options.valid_chars)
    
    if options.verbose:
        xkcd_password.verbose_reports(my_wordlist, options)

    return xkcd_password.generate_xkcdpassword(
        my_wordlist,
        interactive=options.interactive,
        numwords=options.numwords,
        acrostic=options.acrostic,
        delimiter=options.delimiter)

def get_user_info(username):
    """
    Returns pwd.struct_passwd(pw_name='baldwin01', 
                              pw_passwd='x', 
                              pw_uid=1544, 
                              pw_gid=1544, 
                              pw_gecos='Baldwin Student 01', 
                              pw_dir='/home/baldwin01', 
                              pw_shell='/bin/bash')
    """
    retval = None
    try:
        retval = pwd.getpwnam(username)
    except KeyError:
        retval = None
    return retval

def system(command):
    #print("COMMAND: ", command)
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    return out.decode().strip()
	
def main():
    app = Application([
        (os.environ['JUPYTERHUB_SERVICE_PREFIX'] + '/?', AccountsHandler),
        (r'.*', AccountsHandler),
    ])
    http_server = HTTPServer(app)
    url = urlparse(os.environ['JUPYTERHUB_SERVICE_URL'])
    http_server.listen(url.port, url.hostname)
    IOLoop.current().start()

if __name__ == '__main__':
    main()
