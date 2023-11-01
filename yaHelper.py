#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fileencoding=utf-8
from datetime import date
from fileinput import filename
import os
from pickle import NONE, TRUE
import credentials
import random
import yadisk

from stringHelper import get_random_string

dst = '/temp/'

y = yadisk.YaDisk(token=credentials.yandex_token)


def createFolder():
    newFolderName = get_random_string(date.today().day)
    y.mkdir(credentials.main_dirrectory + '/' + newFolderName)
    return newFolderName

def digToSubfolder(item):
    if item.type == "dir":
        rand = random.choice(list(y.listdir(item.path)))
        return digToSubfolder(rand)
    if item.media_type == "image" or item.media_type == "video":
        return item;
    return NONE


def downloadFile(url, fileName):
    y.download_by_link(url, dst + '/' + fileName)
    

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


def saveFileTo(localpath, yandexFolder):
    if(y.check_token()):
        if(os.path.isfile(localpath)):
            y.upload(localpath, credentials.main_dirrectory + "/" + yandexFolder, overwrite=TRUE)