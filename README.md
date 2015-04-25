# GooglePhotosSync
Bi-directional sync between local folder and Google Photos/Picasa. This code may be unstable. It comes without any warranty.

# Features
This script allows to synchronize bi-directionally between selected albums on Google Photos/Picasa and local folders. It allows to define several Google accounts mapping to one local folder. Multiple Google Accounts can be synchronized to the same local folders, which effectively synchronizes these two Google Accounts.

Currently, the synchronization is limited to new files and updates. Deletes are not yet propagated.

If pyexiv2 is installed, then individual photo's will also be tagged according to the album name.

# Install and configure

Install Python (2.7) and the following packages:
-gdata (tested with version 2.0.18)
-sqlalchemy (tested with version 0.8.4)
-python-sqlite (tested with version 1.0.1)
-pyexiv2 (optional; tested with version 0.3.2)

Clone this repository.

Rename settings_template.py to settings.py and edit it (see the included comments).

# Usage

Run main.py as a script from its own working directory. 

A sqlite database will be created for each Google account to record the current status. Subsequent runs will refer to the database to see which files are new or have changed. Only changed and new files are propagated.

A full sync can be forced by removing the sqlite databases and running main.py again.
