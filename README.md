# GooglePhotosSync
Bi-directional sync between local folder and Google Photos/Picasa. This code should be judged as alhpa. It comes without any warranty.

# Features
This script allows to synchronize bi-directionally between selected albums on Google Photos/Picasa and local folders. It allows to define several Google accounts mapping to one local folder. The result is that thealbums for separate Google accounts can be synchronized.

Currently, the synchronization is limited to new files and updates. Deletes are not yet propagated.

If pyexiv2 is installaed, then individual photo's will also be tagged according to the album name.

# Install and configure

Install the following python packages:
-gdata (tested with version 2.0.18)
-sqlalchemy (tested with version 0.8.4)
-python-sqlite (tested with version 1.0.1)
-pyexiv2 (optional; tested with version 0.3.2)

Clone this repository.

Rename settings_template.py to settings.py and edit it.

# Usage

Run main.py as a script.
