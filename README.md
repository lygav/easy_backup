##Python easy_backup

Friendly, simple solution for backing up servers to AWS S3 elastic cloud storage.  
Allows to backup all databases vs all tables (visible for that database user) and important direcotries.

##Can Backup
* folders
* MySQL databases

##Compatability
**Script written for python 2.7** but can easily adapted
for python 2.6 as follows:

* remove *RawCongifParser* *allow_no_value* argument
* as *gzipfile* won't work with the 'with' keyword - change it to be closed manually by using gz_file.close()
