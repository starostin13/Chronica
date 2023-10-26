#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fileencoding=utf-8
from pickle import NONE
from socket import timeout
import credentials
import random
from statistics import median
import yadisk
from yadisk.api import FilesRequest
from yadisk.yadisk import _apply_default_args
import statistics

y = yadisk.YaDisk(token=credentials.yandex_token)
    

def getLastUpdatedFolder():
    if y.check_token():
        folders = (list(y.listdir(credentials.main_dirrectory)))
        folders.sort(key=lambda dt: dt.modified)
        return folders[-1].name

def getPhoto():
    
    # or
    #y = yadisk.YaDisk("<application-id>", "<application-secret>", "<token>")

    # Check if the token is valid
    print(y.check_token())

    # Get disk information
    print("Your already use " + str(y.get_disk_info().used_space * (10 ** (-9))))
        
    subfolders = (list(y.listdir(credentials.main_dirrectory)))

    return digToSubfolder(random.choice(subfolders))

def digToSubfolder(item):
    if item.type == "dir":
        rand = random.choice(list(y.listdir(item.path)))
        return digToSubfolder(rand)
    if item.media_type == "image" or item.media_type == "video":
        return item;
    return NONE