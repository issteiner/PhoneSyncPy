#!/usr/bin/env python3

import datetime
import getpass
import hashlib
import json
import os
import sys

from gi.repository import Gio

sys.path.append("../DupliSeek")
import dupliSeek

GIO_FLAGS = Gio.FileCopyFlags(Gio.FileCopyFlags.OVERWRITE)
SCRIPT_PATH = sys.argv[0]
SCRIPT_DIR = os.path.realpath(os.path.dirname(SCRIPT_PATH))
SCRIPT_NAME = os.path.basename(SCRIPT_PATH).rstrip('.py')
ACT_DATE_TIME = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

FILEDATA_DIR = os.path.join(SCRIPT_DIR, "FileData")
LOGDIR = os.path.join(SCRIPT_DIR, "Logs")
OUTLOG = "{}/{}_{}.log".format(LOGDIR, SCRIPT_NAME, ACT_DATE_TIME)
ERRORLOG = OUTLOG.rstrip('log') + "err"

ACT_USER = getpass.getuser()
ACT_USER_ID = os.getuid()
PC_HOME_DIR = os.path.join("/home", ACT_USER)
PC_DOC_DIR = os.path.join(PC_HOME_DIR, "Documents")
PC_PHONE_DIR = os.path.join(PC_HOME_DIR, "PhoneTransfer")

for directory in [FILEDATA_DIR, LOGDIR, PC_PHONE_DIR]:
    if not os.path.isdir(directory):
        print("Creating directory {}...".format(directory))
        os.makedirs(directory)

PC_PHONE_ACTUAL_DIR = os.path.join(PC_PHONE_DIR, "FromPhone_" + ACT_DATE_TIME)

GVS_PATH = os.path.join("/run/user/{}".format(ACT_USER_ID), "gvfs")
PHONE_MTP_DIRS = os.listdir(GVS_PATH)
if len(PHONE_MTP_DIRS) > 1:
    print("ERROR! More than one phone is connected/mounted. Fix it and try again!")
    sys.exit(1)
elif len(PHONE_MTP_DIRS) == 0:
    print("ERROR! Phone is not connected/mounted. Fix it and try again!")
    sys.exit(1)

PHONE_MTP_DIR = PHONE_MTP_DIRS[0]
PHONE_BASE_DIR = os.path.join(GVS_PATH, PHONE_MTP_DIR, "Phone")
if not os.path.isdir(PHONE_BASE_DIR):
    print("ERROR! It is not allowed to read to / write from phone's memory. Fix it and try again!")
    sys.exit(1)

PHONE_DOC_DIR = os.path.join(PHONE_BASE_DIR, "Documents")
PHONE_TRANSFER_DIR = os.path.join(PHONE_DOC_DIR, "0_Transfer")

DIRS_TO_PHONE = ["Private/0_Privat/Projektek/0_Folyo/HazFelujitas_2015-",
                 "Private/6_AlkalmazottTudomany",
                 "Private/0_Privat/Aktualis/CsinalniValo",
                 "Private/0_Privat/Ingatlanok",
                 "Common/Scripts"]

DIRS_FROM_PHONE = ["DCIM",
                   "Download",
                   "Documents/Actual",
                   "Documents/1_BackTransfer"]


class FileDataStore(object):
    def __init__(self, dir_path):
        self.dir_path = dir_path
        self.file_data, self.dir_data = self.get_file_and_dir_data(dir_path)
        self.data_filename_prefix = self.get_dir_path_repr()

    @staticmethod
    def get_file_and_dir_data(dir_path):
        file_data_container = {}
        dir_data_container = {}
        for dirname, subdirs, filelist in os.walk(dir_path):
            for filename in filelist:
                file_full_path = os.path.join(dirname, filename)
                file_size = os.path.getsize(file_full_path)
                file_mod_time = os.path.getmtime(file_full_path)
                file_data_container[file_full_path] = [file_size, file_mod_time]
            for dir_name in subdirs:
                dir_full_path = os.path.join(dirname, dir_name)
                dir_data_container[dir_full_path] = None  # For future usage maybe
        return file_data_container, dir_data_container

    @staticmethod
    def dirpath_to_hash(dirpath):
        hasher = hashlib.md5()
        enc_string = dirpath.encode('utf-8')
        hasher.update(enc_string)
        return hasher.hexdigest()[:8]

    def get_dir_path_repr(self):
        dirname = os.path.basename(self.dir_path)
        parentdir_path = os.path.dirname(self.dir_path)
        parentdir_hash = self.dirpath_to_hash(parentdir_path)
        return "{}_{}".format(parentdir_hash, dirname)

    def save_file_and_dir_data(self, dir_path):
        filedata_file_path = "{}_filedata.json".format(os.path.join(dir_path, self.data_filename_prefix))
        with open(filedata_file_path, 'w') as datafile:
            json.dump(self.file_data, datafile, indent=2)
        dirdata_file_path = "{}_dirdata.json".format(os.path.join(dir_path, self.data_filename_prefix))
        with open(dirdata_file_path, 'w') as datafile:
            json.dump(self.dir_data, datafile, indent=2)

    def load_file_and_dir_data(self, dir_path):
        file_data = {}
        dir_data = []
        file_path = "{}_filedata.json".format(os.path.join(dir_path, self.data_filename_prefix))
        if os.path.isfile(file_path):
            with open(file_path, 'r') as datafile:
                file_data = json.load(datafile)
        else:
            file_data = {}
        file_path = "{}_dirdata.json".format(os.path.join(dir_path, self.data_filename_prefix))
        if os.path.isfile(file_path):
            with open(file_path, 'r') as datafile:
                dir_data = json.load(datafile)
        else:
            dir_data = {}
        return file_data, dir_data

    def get_file_and_dirdata_diff(self, dir_path):
        files_to_update = []
        old_file_data, old_dir_data = self.load_file_and_dir_data(dir_path)
        old_file_paths = set(old_file_data.keys())
        current_file_paths = set(self.file_data.keys())
        common_file_paths = old_file_paths & current_file_paths
        files_to_delete = list(old_file_paths - common_file_paths)
        files_to_add = list(current_file_paths - common_file_paths)
        for file_path in old_file_data.keys():
            if self.file_has_changed(file_path, old_file_data[file_path]):
                files_to_update.append(file_path)
        old_dir_paths = set(old_dir_data.keys())
        current_dir_paths = set(self.dir_data.keys())
        common_dir_paths = old_dir_paths & current_dir_paths
        dirs_to_delete = list(old_dir_paths - common_dir_paths)
        dirs_to_add = list(current_dir_paths - common_dir_paths)
        return files_to_update + files_to_add, files_to_delete, dirs_to_add, dirs_to_delete

    def file_has_changed(self, file_path, file_attrs):
        if file_path in self.file_data.keys():
            return file_attrs != self.file_data[file_path]
        else:
            return False


def copy_to_phone(dirs_to_copy, pc_base_dir_path, phone_transfer_dir_path):
    print("Copying files from the own HDD to the phone...")
    for act_dir in dirs_to_copy:
        act_dir_full_path = os.path.join(pc_base_dir_path, act_dir)
        fileData = FileDataStore(act_dir_full_path)
        files_to_update, files_to_delete, dirs_to_add, dirs_to_delete = fileData.get_file_and_dirdata_diff(FILEDATA_DIR)
        for act_file in files_to_delete:
            phone_act_file = act_file.replace(pc_base_dir_path, phone_transfer_dir_path)
            phone_act_gio_file = Gio.File.parse_name(phone_act_file)
            if phone_act_gio_file.query_exists():
                phone_act_gio_file.delete()

        for act_dir in dirs_to_delete:
            phone_act_dir = act_dir.replace(pc_base_dir_path, phone_transfer_dir_path)
            phone_act_gio_dir = Gio.File.parse_name(phone_act_dir)
            if phone_act_gio_dir.query_exists():
                phone_act_gio_dir.delete()

        for act_dir in dirs_to_add:
            phone_act_dir = act_dir.replace(pc_base_dir_path, phone_transfer_dir_path)
            phone_act_gio_dir = Gio.File.parse_name(phone_act_dir)
            if not phone_act_gio_dir.query_exists():
                phone_act_gio_dir.make_directory_with_parents()

        for act_file in files_to_update:
            act_gio_file = Gio.File.parse_name(act_file)
            phone_act_file = act_file.replace(pc_base_dir_path, phone_transfer_dir_path)
            phone_act_gio_file = Gio.File.parse_name(phone_act_file)
            phone_act_gio_file_dir = phone_act_gio_file.get_parent()
            if not phone_act_gio_file_dir.query_exists():
                phone_act_gio_file_dir.make_directory_with_parents()
            act_gio_file.copy(phone_act_gio_file, GIO_FLAGS, None, None, None)
        fileData.save_file_and_dir_data(FILEDATA_DIR)


def copy_from_phone(dirs_to_copy, phone_base_dir_path, pc_phone_actual_dir_path):
    print("Copying files from phone to the own HDD...")
    for act_dir in dirs_to_copy:
        file_container = []
        act_dir_full_path = os.path.join(phone_base_dir_path, act_dir)
        for dirname, subdirs, filelist in os.walk(act_dir_full_path):
            for filename in filelist:
                file_full_path = os.path.join(dirname, filename)
                file_container.append(file_full_path)
        for act_file in file_container:
            act_gio_file = Gio.File.parse_name(act_file)
            pc_act_file_full_path = act_file.replace(phone_base_dir_path, pc_phone_actual_dir_path)
            pc_act_gio_file = Gio.File.parse_name(pc_act_file_full_path)
            pc_act_gio_file_dir = pc_act_gio_file.get_parent()
            if not pc_act_gio_file_dir.query_exists():
                pc_act_gio_file_dir.make_directory_with_parents()
            act_gio_file.copy(pc_act_gio_file, GIO_FLAGS, None, None, None)


def dupliseek_on_copied_files(act_dir):
    print("Searching for duplicate files, and removing found duplicates in the copied files/directories on the HDD...")
    sys.argv = ['dupliSeek.py', '-v', '-p', '-r', PC_DOC_DIR, act_dir]
    dupliSeek.main()


def clean_zero_files_empty_dirs(actual_dir):
    print("Deleting zero size files and empty directories in the copied files/directories on the HDD...")
    for dirname, subdirs, filelist in os.walk(actual_dir):
        for filename in filelist:
            file_full_path = os.path.join(dirname, filename)
            if os.path.getsize(file_full_path) == 0:
                os.remove(file_full_path)
    for dirname, subdirs, filelist in os.walk(actual_dir):
        if subdirs == [] and filelist == []:
            os.removedirs(dirname)


def main():
    copy_from_phone(DIRS_FROM_PHONE, PHONE_BASE_DIR, PC_PHONE_ACTUAL_DIR)
    dupliseek_on_copied_files(PC_PHONE_ACTUAL_DIR)
    clean_zero_files_empty_dirs(PC_PHONE_ACTUAL_DIR)
    copy_to_phone(DIRS_TO_PHONE, PC_DOC_DIR, PHONE_TRANSFER_DIR)


if __name__ == '__main__':
    main()
