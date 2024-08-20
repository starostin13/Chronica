#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fileencoding=utf-8
from datetime import date
import os
from pickle import NONE, TRUE
import credentials
import random
import yadisk

from stringHelper import get_random_string

dst = credentials.temp_folder

y = yadisk.YaDisk(token=credentials.yandex_token)


def createFolder():
    newFolderName = get_random_string(date.today().day)
    y.mkdir(credentials.main_dirrectory + '/' + newFolderName)
    return newFolderName

def digToSubfolder(item):
    if item.type == "dir":
        li = list(y.listdir(item.path))
        random.shuffle(li)
        rand = random.choice(li)
        return digToSubfolder(rand)
    if item.media_type == "image" or item.media_type == "video":
        return item;
    return NONE


def downloadFile(url, fileName):
    y.download_by_link(url, dst + fileName)
    

def getLastUpdatedFolder():
    if y.check_token():
        folders = (list(y.listdir(credentials.main_dirrectory)))
        folders.sort(key=lambda dt: dt.modified)
        return folders[-1].name


def getPhoto():
    # �������� ���������� ������
    if not y.check_token():
        print("Invalid token")
        return None
    
    # ����� ���������� � ������� ������������
    print("You already use " + str(y.get_disk_info().used_space * (10 ** (-9))))

    # ��������� ������� ���� (���� � �����)
    today = date.today()
    today_day = today.day
    today_month = today.month
    
    # ������ ��� �������� ������, ��������� � ��� �� ���� � �����, �� � ������ ���
    matching_files = []
    
    # ��������� ������ ���� ������������� � �������� ����������
    subfolders = list(y.listdir(credentials.main_dirrectory))
    
    # ������� ���� ������ � ��������������
    for folder in subfolders:
        files = list(y.listdir(folder.path))
        for file in files:
            # ��������, �������� �� ���� ������������ ��� �����
            if file.media_type in ["image", "video"]:
                # ���������� ���� �������� �����
                created_date = file.created
                if created_date.day == today_day and created_date.month == today_month and created_date.year != today.year:
                    # ���������� ����� � ������, ���� ���� ���������
                    matching_files.append(file)
    
    # ���� ������� ����� � ����������� �����, ������� ��������� �� ���
    if matching_files:
        return random.choice(matching_files)
    
    # ���� �� ������� �� ������ ����������� �����, ����������� �������� ������
    random.shuffle(subfolders)
    return digToSubfolder(random.choice(subfolders))


def saveFileTo(localpath, yandexFolder):
    if(y.check_token()):
        if(os.path.isfile(localpath)):
            y.upload(localpath, credentials.main_dirrectory + "/" + yandexFolder, overwrite=TRUE)