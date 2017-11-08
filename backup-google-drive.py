#!/usr/bin/env python3

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
        result = service.files().list(fields="nextPageToken, files(id, name, mimeType)", q=query, pageSize=PAGE_SIZE, pageToken=next_page_token).execute()
        for item in result['files']:
            backup_file(service, item['id'], item['name'], item['mimeType'], destination, include_trashed)
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

def backup_file(service, file_id, file_name, mime_type, destination, include_trashed):
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
        data = service.files().export(fileId=file_id, mimeType=export_mime_type).execute()
        output_file = os.path.join(destination, '{0}.{1}'.format(clean(file_name), extension))
        with open(output_file, 'wb') as output:
            output.write(data)
    else:
        data = service.files().get(fileId=file_id, fields='size').execute()
        if 'size' in data:
            data = service.files().get_media(fileId=file_id).execute()
            output_file = os.path.join(destination, clean(file_name))
            with open(output_file, 'wb') as output:
                output.write(data)
        else:
            print("Cannot handle", mime_type, file_id, file_name)

def clean(filename):
    filename = filename.replace('/', '-')
    filename = filename.replace('\\', '-')
    filename = filename.replace(': ', ' ')
    filename = filename.replace(':', ' ')
    return filename

if __name__ == '__main__':
    main()
