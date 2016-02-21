# -*- coding: utf-8 -*-
"""
Created on Wed Mar 25 12:10:41 2015

@author: rogier
"""


from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

Base        = declarative_base()

class Pairs(Base):
    
    __tablename__ = 'pairs'
    
    id = Column(Integer, primary_key=True)
    
    album               = Column(String)
    keywords            = Column(String)
    local_path          = Column(String)
    local_fn            = Column(String)
    local_mtime         = Column(Float)
    local_size          = Column(Integer)    
    google_fn           = Column(String)
    google_url          = Column(String)
    google_timestamp    = Column(Float)
    google_size         = Column(String)
    google_photoid      = Column(String)
        

#    def __init__(self, name, fullname, password):
#        self.name = name
#        self.fullname = fullname
#        self.password = password
        
    def __repr__(self):
       return "<Pair '%s'>" % (self.local_fn)