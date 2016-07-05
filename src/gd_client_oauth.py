# -*- coding: utf-8 -*-
"""
Created on Fri Jul 10 23:52:07 2015

@author: rogier

See: http://stackoverflow.com/questions/30474269/using-google-picasa-api-with-python
"""

import gdata.photos.service
from oauth2client.file import Storage
from oauth2client.client import flow_from_clientsecrets
import webbrowser
import httplib2
from datetime import datetime, timedelta

def OAuth2Login(client_secrets, credential_store, email):
    scope='https://picasaweb.google.com/data/'
    user_agent='myapp'

    storage = Storage(credential_store)
    credentials = storage.get()
    if credentials is None or credentials.invalid:
        flow = flow_from_clientsecrets(client_secrets, scope=scope, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
        uri = flow.step1_get_authorize_url()
        webbrowser.open(uri)
        code = raw_input('Enter the authentication code: ').strip()
        credentials = flow.step2_exchange(code)
        storage.put(credentials)

    if (credentials.token_expiry - datetime.utcnow()) < timedelta(minutes=5):
        http = httplib2.Http()
        http = credentials.authorize(http)
        credentials.refresh(http)

    gd_client = gdata.photos.service.PhotosService(source=user_agent,
                                               email=email,
                                               additional_headers={'Authorization' : 'Bearer %s' % credentials.access_token})

    return gd_client