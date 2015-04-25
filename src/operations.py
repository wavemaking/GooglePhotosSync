# -*- coding: utf-8 -*-
"""
Created on Sat Mar 28 17:11:38 2015

@author: rogier
"""

import gdata.photos.service
import urllib2
try:
    import pyexiv2
except:
    pass
import mimetypes
import os
import re
import atom
import logging
import gdata
import gdata.photos

#See https://code.google.com/p/gdata-python-client/issues/detail?id=542
valid_mimetypes = [
    'image/bmp',
    'image/gif',
    'image/jpeg',
    'image/png',
    'video/3gpp',
    'video/avi',
    'video/quicktime',
    'video/mp4',
    'video/mpeg',
    'video/mpeg4',
    'video/msvideo',
    'video/x-ms-asf',
    'video/x-ms-wmv',
    'video/x-msvideo'
]

# Hack because python gdata client does not accept videos?!
for mtype in valid_mimetypes:
  mayor, minor = mtype.split('/')
  if mayor == 'video':
    gdata.photos.service.SUPPORTED_UPLOAD_TYPES += (minor,)

def strip_album_name(album):
        
    album = album.replace(' ','')
    album = album.replace('/','')
    album = album.replace('-','')
    
    return album

def make_sure_path_exists(path):
    
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise

def apply_keyword_google(gd_client,photo,pair):
    
    if 'Full Collection' in pair.album:
        pair.keyword = pair.album.lstrip('Full Collection')
    elif 'Album' in pair.album:
        pair.keyword = pair.album.lstrip('Album')
    else:
        pair.keyword = pair.album
    
    try:    
        if photo.media.keywords.text == None:
            photo.media.keywords.text = pair.keyword
        elif not pair.keyword in photo.media.keywords.text:
            photo.media.keywords.text = ','.join([photo.media.keywords.text,pair.keyword])
    except:
        pass
        
    return photo, pair

def apply_keyword_local(pair):
    
    if 'Full Collection' in pair.album:
        pair.keyword = pair.album.lstrip('Full Collection')
    elif 'Album' in pair.album:
        pair.keyword = pair.album.lstrip('Album')
    else:
        pair.keyword = pair.album            
        
    try: #IPTC using pyexiv2
        metadata    = pyexiv2.ImageMetadata(os.path.join(pair.local_path,pair.local_fn))
        metadata.read()
        
        try:
            if not pair.keyword in metadata['Iptc.Application2.Keywords'].raw_value:
                metadata['Iptc.Application2.Keywords'] = metadata['Iptc.Application2.Keywords'].raw_value + [pair.keyword]
        except KeyError:
            metadata['Iptc.Application2.Keywords'] = [pair.keyword]                
        metadata.write()
    except:
        pass
    
    return pair

def get_photo_google(pair,gd_client):
    
    photo   = None
    photos  = gd_client.GetFeed('/data/feed/api/user/default/album/'+strip_album_name(pair.album))
    for entry in photos.entry:
        if entry.title.text == pair.google_fn:
            photo = entry            
    if photo is None:
        return None
    return photo

def update_db_1_2local(pair,gd_client,photo_google,BASEPATH_LOCAL,album,trailing_text): #before copying
    
    pair.album              = album
    try:
        m                   = re.search('_([A-Z])$',photo_google.title.text.rsplit('.',1)[0])
        if m is None:
            photo_google.title.text         = photo_google.title.text.rsplit('.',1)[0] + '_' +  trailing_text + '.' + photo_google.title.text.rsplit('.',1)[-1]
            photo_google.media.title.text   = photo_google.title.text
            gd_client.UpdatePhotoMetadata(photo_google) 
    except:
        pass
    pair.google_url         = photo_google.media.content[-1].url
    if not 'video' in photo_google.media.content[-1].type:
        pair.google_url     = pair.google_url.rsplit('/',1)[0] + '/s0-d/' + pair.google_url.rsplit('/',1)[1]
    pair.google_fn          = photo_google.title.text       
    pair.local_fn           = pair.google_fn
    pair.local_path         = os.path.join(BASEPATH_LOCAL,album)    

    return pair, photo_google
    
def update_db_1_2google(pair,BASEPATH_LOCAL,album,local_fn,trailing_text): #Before copying
    
    pair.album              = album    
    pair.local_path         = os.path.join(BASEPATH_LOCAL,album)
    try:
        m                   = re.search('_([A-Z])$',local_fn.rsplit('.',1)[0])
        if m is None:
            local_fn_new    = local_fn.rsplit('.',1)[0] + '_' +  trailing_text + '.' + local_fn.rsplit('.',1)[-1]
            os.rename(os.path.join(pair,pair.local_path,local_fn),os.path.join(pair,pair.local_path,local_fn_new))
            pair.local_fn   = local_fn_new
        else:
            pair.local_fn   = local_fn
    except:
        pair.local_fn   = local_fn
    return pair    

def update_db_2(pair,photo): #Document state after copying
    
    try:    
        pair.local_mtime    = os.path.getmtime(os.path.join(pair.local_path, pair.local_fn))
        pair.local_size     = os.path.getsize(os.path.join(pair.local_path, pair.local_fn))
    except OSError:
        pair.local_fn       = 'missing'
        pair.local_mtime    = 0.
        pair.local_size     = ''
    else:
        pass
    
    pair.google_timestamp   = float(photo.timestamp.datetime().strftime('%s'))
    pair.google_url         = photo.GetMediaURL()
    pair.google_url         = pair.google_url.rsplit('/',1)[0] + '/s0-d/' + pair.google_url.rsplit('/',1)[1]
    pair.google_fn          = photo.title.text        
    pair.google_size        = photo.size.text    
    pair.google_photoid     = photo.gphoto_id.text
    
    return pair

def copy2google(pair,gd_client):
    
    album_g = strip_album_name(pair.album)
    try:        
        gd_client.GetFeed('/data/feed/api/user/default/album/' + album_g)
    except gdata.photos.service.GooglePhotosException as GPE:
        if GPE.body == 'No album found.':
            gd_client.InsertAlbum(title=pair.album,summary='')            
        else:
            raise
            
    album_url           = '/data/feed/api/user/default/album/' + album_g
    local_full_path     = os.path.join(pair.local_path,pair.local_fn)
    mimetype            = mimetypes.guess_type(local_full_path, strict=True)[0]
    photoentry          = gdata.photos.PhotoEntry()
    photoentry.title    = atom.Title(text=pair.local_fn)
    photoentry.summary  = atom.Summary(text='',summary_type='text')
    photo               = gd_client.InsertPhoto(album_url,photoentry,local_full_path,mimetype) 

    return photo
    
def copy2local(pair):

    make_sure_path_exists(os.path.join(pair.local_path))
    f                       = open(os.path.join(pair.local_path,pair.local_fn ),'wb')        
    f.write(urllib2.urlopen(pair.google_url).read())
    f.close()
    
def deletegoogle(pair,gd_client):

    raise NotImplemented

def deletelocal(pair):

    raise NotImplemented

def update2google(pair,gd_client):
    deletegoogle(pair,gd_client)
    copy2google(pair,gd_client)

def update2local(pair,gd_client):
    deletelocal(pair,gd_client)
    copy2local(pair,gd_client)
    
def sync_file(pair,gd_client,iphoto):
        
    logger = logging.getLogger(__name__)
    
    change_str  = ''

    try:    
        album_g             = strip_album_name(pair.album)
        photo               = gd_client.GetFeed('/data/feed/api/user/default/album/' + album_g + '/photoid/' + pair.google_photoid)    
        local_mtime         = os.path.getmtime(os.path.join(pair.local_path, pair.local_fn))
        google_timestamp    = float(photo.timestamp.datetime().strftime('%s'))
        
        if local_mtime == pair.local_mtime and google_timestamp == pair.google_timestamp:
            logger.info('{:d} - {}: Both sides unchanged'.format(iphoto+1,pair.local_fn))
                
        if local_mtime == pair.local_mtime and google_timestamp != pair.google_timestamp:
            logger.info('{:d} - {}: google changed'.format(iphoto+1,pair.local_fn))                
            update2local(pair,gd_client)
            change_str  = 'updated_on_google'
            
        if local_mtime != pair.local_mtime and google_timestamp == pair.google_timestamp:
            logger.info('{:d} - {}: Local changed'.format(iphoto+1,pair.local_fn))
            update2google(pair,gd_client)
            change_str  = 'updated_locally'
            
        if local_mtime != pair.local_mtime and google_timestamp != pair.google_timestamp:
            logger.info('{:d} - {}: Both sides changed'.format(iphoto+1,pair.local_fn))
            logger.info('{:d} - {}: google is preferred'.format(iphoto+1,pair.local_fn))
            update2local(pair,gd_client)
            change_str  = 'updated_on_google'
    
    except:
        logger.error('{:d} - {}: Uncaught error. Probably one side got deleted?'.format(iphoto+1,pair.local_fn))
        #TODO: Also handle deletion !    
        
    return change_str