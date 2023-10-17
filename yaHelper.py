#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fileencoding=utf-8
import credentials
import random
from statistics import median
import yadisk
from yadisk.api import FilesRequest
from yadisk.yadisk import _apply_default_args
import statistics

y = yadisk.YaDisk(token=credentials.yandex_token)
    
def getPhoto():
    
    # or
    #y = yadisk.YaDisk("<application-id>", "<application-secret>", "<token>")

    # Check if the token is valid
    print(y.check_token())

    # Get disk information
    print(y.get_disk_info())
    files = (list(y.get_files(media_type="image")))
    wallpaperInfo = (list(y.listdir("/Photo/Саночки")))

    return random.choice(wallpaperInfo)
