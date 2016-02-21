# -*- coding: utf-8 -*-
"""
Created on Sun Apr 19 00:38:33 2015

@author: rogier

This appears to be redundant (same result as pyexiv2)
"""

import libxmp #requires exempi v2 to be installed on the system - overlaps with pyexiv2
import libxmp.utils
import os

def apply_keyword_local(pair):
    
    if 'Full Collection' in pair.album:
        pair.keyword = pair.album.lstrip('Full Collection')
    elif 'Album' in pair.album:
        pair.keyword = pair.album.lstrip('Album')
    else:
        pair.keyword = pair.album     
    try:        
        xmpfile = libxmp.XMPFiles( file_path=os.path.join(pair.local_path,pair.local_fn), open_forupdate=True )
        xmp = xmpfile.get_xmp()        
        #Using the dict, you can get a full dump of all file contens:        
#        xmpdict = libxmp.utils.object_to_dict(xmp)        
        current_keywords = xmp.get_property(libxmp.consts.XMP_NS_DC,'subject[1]')        
        if not pair.keyword in current_keywords:  #See: http://purl.org/dc/elements/1.1/ in the dict or online
            if not current_keywords[-1] == ',' and len(current_keywords) > 0:
                pair.keyword = ',' + pair.keyword
            xmp.set_property(libxmp.consts.XMP_NS_DC,'subject[1]',current_keywords + pair.keyword)
            if xmpfile.can_put_xmp(xmp):
                xmpfile.put_xmp(xmp)        
        xmpfile.close_file()        
    except:
        pass   
    return pair