# Services for Jupyterhub

## Public, a nbviewer service for jupyterhub

This code adds nbviewer-like functionality, via a JupyterHub Service, to a jupyterhub installation. 
That is, it allows users to "publish" their notebooks so that they can be seen as HTML.

Served at /services/public/username/... 

See also the Javascript nbextension for copying notebooks to a user's public_html folder:

https://github.com/Calysto/notebook-extensions

## Accounts, a more flexible way of adding accounts

Creates accounts and passwords following the xkcd password style.

Served at /services/accounts

Opens a form and textarea where each line should be in one of the following forms:

```
   username                             OR
   username@address                     OR
   Real Name, username@school.edu       OR
   Real Name, username-email            OR
   Real Name, email@school.edu, username
```

Can send email, and/or display the passwords. Optional field for professor/adminstrator's name.
