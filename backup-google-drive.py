#!/usr/bin/env python3

import sys
import httplib2
import os, errno

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import argparse
parser = argparse.ArgumentParser(parents=[tools.argparser])
parser.add_argument("destination")
flags = parser.parse_args()

SCOPES = "https://www.googleapis.com/auth/drive.readonly"
CLIENT_SECRET_FILE = "client_secret.json"
APPLICATION_NAME = "Google Drive Backup"

def get_credentials():
    home_dir = os.path.expanduser("~")
    credential_dir = os.path.join(home_dir, ".credentials")
    try:
        os.makedirs(credential_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    credential_path = os.path.join(credential_dir, "google-drive-backup.json")
    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store, flags)
        print("Storing credentials to " + credential_path)
    return credentials

def main():
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build("drive", "v3", http=http)
    backup_folder(service, "root", flags.destination)

PAGE_SIZE = 1000

def backup_folder(service, folder_id, destination, include_trashed=False):
    try:
        os.makedirs(destination)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    next_page_token = ''
    query = "trashed = {0} and '{1}' in parents".format(include_trashed, folder_id)
    while True:
        result = service.files().list(fields="nextPageToken, files(id, name, mimeType, size, md5Checksum)", q=query, pageSize=PAGE_SIZE, pageToken=next_page_token).execute()
        for item in result['files']:
            backup_file(service, item, destination, include_trashed)
        if 'nextPageToken' in result:
            next_page_token = result['nextPageToken']
        else:
            break

# https://developers.google.com/drive/v3/web/manage-downloads

MIME_MAPPINGS = {
    'application/vnd.google-apps.document': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'docx'),
    'application/vnd.google-apps.spreadsheet': ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'xlsx'),
    'application/vnd.google-apps.drawing': ('image/svg+xml', 'svg'),
    'application/vnd.google-apps.presentation': ('application/vnd.openxmlformats-officedocument.presentationml.presentation', 'pptx'),
    'application/vnd.google-apps.script': ('application/vnd.google-apps.script+json', 'json'),
}

def backup_file(service, item, destination, include_trashed):
    file_id = item['id']
    file_name = item['name']
    mime_type = item['mimeType']
    if mime_type == 'application/vnd.google-apps.folder':
        directory = os.path.join(destination, clean(file_name))
        try:
            os.makedirs(directory)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        backup_folder(service, file_id, directory, include_trashed)
    elif mime_type in MIME_MAPPINGS:
        export_mime_type, extension = MIME_MAPPINGS[mime_type]
        output_file = os.path.join(destination, '{0}.{1}'.format(clean(file_name), extension))
        print("Downloading", output_file)
        data = service.files().export(fileId=file_id, mimeType=export_mime_type).execute()
        with open(output_file, 'wb') as output:
            output.write(data)
    elif 'size' in item: # Binary file
        output_file = os.path.join(destination, clean(file_name))
        if os.path.exists(output_file):
            if os.path.getsize(output_file) == int(item['size']):
                local_checksum = md5(output_file)
                if local_checksum == item['md5Checksum']:
                    print("Unchanged", output_file)
                    return
        print("Downloading", output_file)
        data = service.files().get_media(fileId=file_id).execute()
        with open(output_file, 'wb') as output:
            output.write(data)
    else:
        print("WARNING: Cannot handle", mime_type, file_id, file_name, file=sys.stderr)

import hashlib
def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def clean(filename):
    filename = filename.replace('/', '-')
    filename = filename.replace('\\', '-')
    filename = filename.replace(': ', ' ')
    filename = filename.replace(':', ' ')
    return filename

if __name__ == '__main__':
    main()
