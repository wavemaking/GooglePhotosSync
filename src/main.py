# -*- coding: utf-8 -*-
"""
Created on Wed Mar 25 11:58:40 2015
@author: Wavemaker
Based on https://developers.google.com/picasa-web/docs/2.0/developers_guide_python

This script loops over the photos on google and then the photos locally to synchronise bi-directionally, except for deletes

TODO:            
    -Implement deletes?
    -Fix movie keywords?    
    -Sort albums automatically
    -Cleanup counters    
    -Also implement looping over the database (delete records for which no files exist on either end)
    -Split out entry points:
        -Full scan (automatically done when db is not available or when no arguments are supplied) - curently the only one implemented
        -Only poll most recent updates on google
        -Sync local files based on inotify updates or similar
"""

import gdata.photos.service
import gd_client_oauth
import gdata.media
import gdata.geo
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from model import Pairs, Base
import logging
import datetime
import sys
import logging.handlers
import os
from operations import *
from inspect import getsourcefile

os.chdir(os.path.dirname(getsourcefile(lambda:0)))

# Hack because python gdata client by default does not accept videos
for mtype in valid_mimetypes:
  mayor, minor = mtype.split('/')
  if mayor == 'video':
    gdata.photos.service.SUPPORTED_UPLOAD_TYPES += (minor,)

if __name__ == '__main__':

    config = {}
            
    execfile(os.path.join(os.path.dirname(__file__),'settings.py'),config)
                            
    REMOTE_ACCOUNTS     = config['REMOTE_ACCOUNTS'] + config['REMOTE_ACCOUNTS'][0:len(config['REMOTE_ACCOUNTS'])-1] # Ensures that changes from the last accounts are also propageted to the first accounts during the same run

    rootlogger          = logging.getLogger()
    rootlogger.setLevel(logging.DEBUG)
    
    logfile_size_MB     = 1024**2
    logfile             = logging.handlers.RotatingFileHandler('debug.log', maxBytes=5*logfile_size_MB)
    logfile_formatter   = logging.Formatter(
                            '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                            '%y-%m-%d % - %H:%M'
                            )
    logfile.setFormatter(logfile_formatter)
    logfile.setLevel(logging.DEBUG)
    rootlogger.addHandler(logfile)
    
    console             = logging.StreamHandler(sys.stdout)
    console_formatter   = logging.Formatter(
                            '%(asctime)s %(message)s',
                            '%H:%M'
                            )
    console.setFormatter(console_formatter)
    console.setLevel(logging.INFO)
    rootlogger.addHandler(console)
        
    logger              = logging.getLogger(__name__)
    
    #Initialise counters
    deleted_on_google   = {}
    deleted_locally     = {}
    new_on_google       = {}
    new_locally         = {}
    updated_on_google   = {}
    updated_locally     = {}
    duplicate_records_on_google   = {}
    duplicate_records_locally     = {}
    no_files_on_google  = {}
    no_files_locally    = {}        
    for remote_account in REMOTE_ACCOUNTS:
        deleted_on_google[remote_account['email']]   = {}
        deleted_locally[remote_account['email']]     = {}
        new_on_google[remote_account['email']]       = {}
        new_locally[remote_account['email']]         = {}
        updated_on_google[remote_account['email']]   = {}
        updated_locally[remote_account['email']]     = {}
        duplicate_records_on_google[remote_account['email']]   = {}
        duplicate_records_locally[remote_account['email']]     = {}
        no_files_on_google[remote_account['email']]  = {}
        no_files_locally[remote_account['email']]    = {}
        for album in config['ALBUMS']:
            deleted_on_google[remote_account['email']][album]           = {'no': 0, 'pairs': []}                        
            new_on_google[remote_account['email']][album]               = {'no': 0, 'pairs': []}            
            updated_on_google[remote_account['email']][album]           = {'no': 0, 'pairs': []}                        
            duplicate_records_on_google[remote_account['email']][album] = {'no': 0, 'pairs': []}                        
            deleted_locally[remote_account['email']][album]             = {'no': 0, 'pairs': []}                        
            new_locally[remote_account['email']][album]                 = {'no': 0, 'pairs': []}                                    
            updated_locally[remote_account['email']][album]             = {'no': 0, 'pairs': []}                                    
            duplicate_records_locally[remote_account['email']][album]   = {'no': 0, 'pairs': []}                
            no_files_locally[remote_account['email']][album]            = 0
            no_files_on_google[remote_account['email']][album]          = 0            
    
    for remote_account in REMOTE_ACCOUNTS+REMOTE_ACCOUNTS[1:len(REMOTE_ACCOUNTS)-1]:
                        
        logger.info('Now starting with account: ' + remote_account['email'])
            
        engine      = create_engine('sqlite:///sync_state_'+ remote_account['email'] + '.sqlite', echo=False)
        Session     = sessionmaker(bind=engine)
        session     = Session()
        Base.metadata.create_all(engine)                   
#        
#        gd_client               = gdata.photos.service.PhotosService()
#        gd_client.email         = remote_account['email']
#        gd_client.password      = remote_account['password']
#        gd_client.source        = 'GooglePhotoSync'
#        gd_client.ProgrammaticLogin()
                
        trailing_text   = remote_account['trailing_text'] #TODO: Force that this is only one letter and nothing else
        
        for album in config['ALBUMS']:
            
            gd_client           = gd_client_oauth.OAuth2Login(config['CLIENT_SECRET'], 'cred_store' + remote_account['email'], remote_account['email'])
            token_refresh_time  = datetime.datetime.now()
            
            logger.info('Now starting to sync album: ' + album)                        
            
            """
            Scan media on google
            Note: It is important to do google first, because:
                  Duplication of files with identical names on Google can happen, while locally files will simply be overwritten.
                  This is relevant for the first run.
            """
            logger.info('Checking google')
            
            album_g = strip_album_name(album)        
            try:        
                photos = gd_client.GetFeed('/data/feed/api/user/default/album/' + album_g)
            except gdata.photos.service.GooglePhotosException as GPE:
                if GPE.body == 'No album found.':
                    gd_client.InsertAlbum(title=album,summary='',access='private')
                    photos  = gd_client.GetFeed('/data/feed/api/user/default/album/' + album_g)
                else:
                    raise
            
            photos.entry.reverse()            
            for iphoto, photo in enumerate(photos.entry[::-1]): #loop through Google photos   
            
                if (datetime.datetime.now() - token_refresh_time).seconds > 600:
                    gd_client           = gd_client_oauth.OAuth2Login(config['CLIENT_SECRET'], 'cred_store' + remote_account['email'], remote_account['email'])
                    token_refresh_time  = datetime.datetime.now()
                
                try:
                    
                    google_timestamp= (photo.timestamp.datetime() - datetime.datetime(1970,1,1)).total_seconds()
                    google_fn       = photo.title.text
                                                            
                    pair            = session.query(Pairs).filter_by(album=album,google_fn=google_fn)                                                                                      
                    
                    if pair.count() > 1:
                        
                        logger.exception('{:d} - {}: Got back multiple records. Should be only one! Deleting latter record!!'.format(iphoto+1,pair.first().google_fn))
                        duplicate_records_on_google[remote_account['email']][album]['no']    += 1
                        duplicate_records_on_google[remote_account['email']][album]['pairs'].append(pair)
                        session.delete(pair[-1])                    
                        pair                    = pair.first()            
                        change_str              = sync_file(pair,gd_client,iphoto)
                        pair                    = update_db_2(pair,photo)                     
    
                        session.commit()
                        if 'update' in change_str:
                            locals()[change_str][remote_account['email']][album]['no']   += 1
                            locals()[change_str][remote_account['email']][album]['pairs'].append(pair)
                    
                    elif pair.count() == 1:
                        
                        pair                = pair.first()            
                        change_str          = sync_file(pair,gd_client,iphoto)
                        pair                = update_db_2(pair,photo)
                        if 'update' in change_str:
                            locals()[change_str][remote_account['email']][album]['no']   += 1
                            locals()[change_str][remote_account['email']][album]['pairs'].append(pair)
                        session.commit()
                        
                    elif pair.count() == 0:
                        
                        logger.info('{} {:d} - {}: New media not yet available locally'.format(album,iphoto+1,google_fn))
                        
                        pair                = Pairs()        
                        pair,photo          = update_db_1_2local(pair,gd_client,photo,config['BASEPATH_LOCAL'],album,trailing_text)        
                        photo,pair          = apply_keyword_google(gd_client,photo,pair)
                        copy2local(pair)
                        pair                = apply_keyword_local(pair)
                        pair                = update_db_2(pair,photo)
                        session.add(pair)
                        new_on_google[remote_account['email']][album]['no']    += 1
                        new_on_google[remote_account['email']][album]['pairs'].append(pair)
                        session.commit()      
                        
                    else:
                        logger.exception('Unrealistic number of records')
                        #raise ValueError #TODO: Could be more specific      
                        
                    no_files_on_google[remote_account['email']][album] += 1
                    
                except:
                    logger.exception('{:d} - {}: Could not handle this photo locally in album {}'.format(iphoto+1,pair.local_fn,album))    
            
            
            """
            Scan local media
            """
            logger.info('Checking locally')
                                    
            local_path          = os.path.join(config['BASEPATH_LOCAL'],album)
            make_sure_path_exists(local_path)  
            photos              = [f for f in os.listdir(local_path) if (os.path.isfile(os.path.join(local_path,f)) and os.stat(os.path.join(local_path,f)).st_size != 0)]
            
            gd_client           = gd_client_oauth.OAuth2Login(config['CLIENT_SECRET'], 'cred_store' + remote_account['email'], remote_account['email'])
            token_refresh_time  = datetime.datetime.now()
            
            for iphoto, photo in enumerate(photos[::-1]):
                                                
                if (datetime.datetime.now() - token_refresh_time).seconds > 60:
                    gd_client           = gd_client_oauth.OAuth2Login(config['CLIENT_SECRET'], 'cred_store' + remote_account['email'], remote_account['email'])
                    token_refresh_time  = datetime.datetime.now()            

                try:
                                
                    local_fn        = photo  
                    local_mtime     = os.path.getmtime(os.path.join(local_path, local_fn))
                            
                    pair            = session.query(Pairs).filter_by(album=album,local_fn=local_fn)
                    
                    if pair.count() > 1:                    
                        logger.exception('{:d} - {}: Got back multiple records. Should be only one! Deleting latter record!!'.format(iphoto+1,pair[-1].local_fn))
                        session.delete(pair[-1])
                        duplicate_records_locally[remote_account['email']][album]['no']    += 1
                        duplicate_records_locally[remote_account['email']][album]['pairs'].append(pair)
                        pair                = pair.first()
                        change_str          = sync_file(pair,gd_client,iphoto)
                        photo           = get_photo_google(pair,gd_client)                        
                        pair                = update_db_2(pair,photo)
                        if 'update' in change_str:
                            locals()[change_str][remote_account['email']][album]['no']   += 1
                            locals()[change_str][remote_account['email']][album]['pairs'].append(pair)
                        session.commit()
                        
                    elif pair.count() == 1:
                                                
                        pair                = pair.first()            
                        sync_file(pair,gd_client,iphoto)
                        try:
                            photo_g         = get_photo_google(pair,gd_client)
                        except:
                            gd_client       = gd_client_oauth.OAuth2Login(config['CLIENT_SECRET'], 'cred_store' + remote_account['email'], remote_account['email'])
                            photo_g         = get_photo_google(pair,gd_client)
                        if photo_g is None:
                            logger.warning('{:d} - {}: Photo not available anymore on google in album {}'.format(iphoto+1,pair.local_fn,album))
                            pair.google_fn  = 'missing'                        
                        else:
                            pair            = update_db_2(pair,photo_g)     
                        if 'update' in change_str:
                            locals()[change_str][remote_account['email']][album]['no']   += 1
                            locals()[change_str][remote_account['email']][album]['pairs'].append(pair)
                        session.commit()                
                        
                    elif pair.count() == 0:
                        
                        logger.info('{:d} - {}: New media not yet available on google'.format(iphoto+1,local_fn))
                        
                        pair        = Pairs()                            
                        pair        = update_db_1_2google(pair,config['BASEPATH_LOCAL'],album,local_fn,trailing_text)
                        pair        = apply_keyword_local(pair)
                        photo       = copy2google(pair,gd_client)
                        photo,pair  = apply_keyword_google(gd_client,photo,pair)            
                        pair        = update_db_2(pair,photo)
                        session.add(pair)
                        new_locally[remote_account['email']][album]['no']    += 1
                        new_locally[remote_account['email']][album]['pairs'].append(pair)
                        session.commit()
                        
                    else:                
                        logger.exception('Unrealistic number of records')
                        #raise ValueError #TODO: Could be more specific  
                        
                        no_files_locally[remote_account['email']][album] += 1
                        
                except:
                        logger.exception('{:d} - {}: Could not handle this photo on google in album {}'.format(iphoto+1,pair.local_fn,album))                    
                                        
                    
    for remote_acount in REMOTE_ACCOUNTS:
        for album in config['ALBUMS']:
            logger.info('{} - {} new_on_google:                 {:.0f}'.format(remote_account['email'],album,new_on_google[remote_account['email']][album]['no']))
            logger.info('{} - {} new_locally:                   {:.0f}'.format(remote_account['email'],album,new_locally[remote_account['email']][album]['no']))
            logger.info('{} - {} updated_on_google:             {:.0f}'.format(remote_account['email'],album,updated_on_google[remote_account['email']][album]['no']))
            logger.info('{} - {} updated_locally:               {:.0f}'.format(remote_account['email'],album,updated_locally[remote_account['email']][album]['no']))
            logger.info('{} - {} duplicate_records_on_google:   {:.0f}'.format(remote_account['email'],album,duplicate_records_on_google[remote_account['email']][album]['no']))
            logger.info('{} - {} duplicate_records_locally:     {:.0f}'.format(remote_account['email'],album,duplicate_records_locally[remote_account['email']][album]['no']))
            logger.info('{} - {} no_files_on_google:            {:.0f}'.format(remote_account['email'],album,duplicate_records_on_google[remote_account['email']][album]['no']))
            logger.info('{} - {} no_files_locally:              {:.0f}'.format(remote_account['email'],album,duplicate_records_locally[remote_account['email']][album]['no']))
    logger.info('Finished this run')
    
           