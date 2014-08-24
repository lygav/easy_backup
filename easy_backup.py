import gzip
import os
import re
import socket
import sys
import time
import boto
import ConfigParser
from zipfile import ZipFile
import subprocess

config = ConfigParser.ConfigParser()
config.read('config.ini')

def establish_working_dir(dirpath):
    if not os.path.exists(dirpath):
        os.makedirs(dirpath, mode=0777)
    os.chdir(dirpath)

def backup_mysql(username, password, host, port):
    def __get_mysql_backup_file_name():
        hostname = socket.gethostname() + '-'
        sqldump_file_name = re.sub('[\\/:\*\?"<>\|\ ]', '-', hostname + 'backup') + '.sql'
        return os.path.abspath(sqldump_file_name)

    def __compress_file(filepath):
        print "compressing..."
        archive_path = filepath + '.gz'
        with open(filepath, 'rb') as target_file:
            with gzip.open(archive_path, 'wb') as gz_file:
                gz_file.writelines(target_file)
        print "SQL dump file compressed. filesize: %d bytes." % os.path.getsize(archive_path)
        return archive_path

    print 'Backing up mysql databases...'
    mysql_backup_file_path = __get_mysql_backup_file_name()
    if 'win' not in sys.platform:
        res = subprocess.Popen(['mysql', '-e', 'show databases'], stdout=subprocess.PIPE).communicate()[0]
        matches = re.findall(".+", res)
        for database in matches[1:]:
            print 'Dumping %s' % database
            try:
                os.system("/usr/bin/mysqldump -u %s -p%s -h %s -P %d --opt --databases %s > %s" % (username, password, host, port, database, mysql_backup_file_path))
                __compress_file(mysql_backup_file_path)
                os.unlink(mysql_backup_file_path)
            except Exception as e:
                print e
    print "Finished mysql backup"

def backup_filesystem(dirs_to_backup):
    def __zip_directory_tree(dirpath, zipfile_name):
        print 'Backing up %s' % dirpath
        for root, dirs, files in os.walk(dirpath):
            with ZipFile(os.path.join(os.getcwd(), zipfile_name + '.zip'), 'a') as myzip:
                for filename in files:
                    myzip.write(os.path.join(root, filename))
    [__zip_directory_tree(dirpath, dirname) for (dirname, dirpath) in dirs_to_backup]

def get_current_timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def upload_to_s3(aws_key, aws_secret, bucket_name, path, files_to_upload_list = None, retry = None):

    def __update_progress(transmitted, total):
        progress = transmitted * 100 / total
        sys.stdout.write("\rUploaded %s%% (%s/%s)" % (progress, transmitted, total))
        sys.stdout.flush()

    uploaded = []
    failed   = []

    s3 = boto.connect_s3(aws_key, aws_secret)
    bucket = s3.get_bucket(bucket_name)
    for filename in files_to_upload_list:
        if len(path.strip()):
            key_name = "%s/%s" % (path, os.path.basename(filename))
        else:
            key_name = os.path.basename(filename)
        key = bucket.new_key(key_name)
        try:
            print '\r\nUploading %s' % filename
            with open(filename, "rb") as ufile:
                res = key.set_contents_from_file(ufile, cb=__update_progress, num_cb=100, replace=True)
            if res == os.stat(filename).st_size:
                uploaded.append("%s/%s" % (bucket_name, key_name))
                os.unlink(filename)
        except: 
            sys.exit('failed to upload file %s' % filename)
            failed.append(filename)
    if failed and not retry:
        upload_to_s3(aws_key, aws_secret, bucket_name, path, failed, retry=True)
    return uploaded

def delete_all_files_from_working_dir():
    print "Cleaning up..."
    for filename in os.listdir(os.getcwd()):
        os.unlink(filename)

if __name__ == "__main__":

    establish_working_dir(config.get("environment", "work dir"))
    backup_mysql(config.get('mysql', 'username'), config.get('mysql', 'password'), config.get('mysql', 'host'), config.getint('mysql', 'port'))
    backup_filesystem(config.items("dirs to backup"))
    upload_to_s3(config.get('s3', 'aws_key'), config.get('s3', 'aws_secret'),  config.get('s3', 'bucket_name'),  config.get('s3', 'prefix') + get_current_timestamp(), os.listdir(os.getcwd()))    
    delete_all_files_from_working_dir()