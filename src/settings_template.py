# Rename this file to "settings.conf". That is the default filename used by the script.

BASEPATH_LOCAL          = r'path to your local photo storage' # Make sure that the folder exists

CLIENT_SECRET           = r'path to client secret json file downloaded from Google Console'

ALBUMS                  = ('Album 1', # Full names (titles) - If they do not exist on Google/Locally, they will be created
                           'Album 2',
                           )

REMOTE_ACCOUNTS         = ({
                            'email':        'accountA@gmail.com',                            
                            'password':     'yourpasswordA', 			#obtain here: https://security.google.com/settings/security/apppasswords
                            'trailing_text':'A',                  # specify a single letter to avoid clashes between photo filenames that theoretically be identical coming from two camera's/phone
                            },{
                            'email':        'accountB@gmail.com',
                            'password':     'yourpasswordB', 			#obtain here: https://security.google.com/settings/security/apppasswords
                            'trailing_text':'B',                  # specify a single letter to avoid clashes between photo filenames that theoretically be identical coming from two camera's/phone
                            })