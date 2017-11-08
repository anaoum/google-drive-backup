#!/usr/bin/env python3

import sys
import httplib2
import os, errno
import datetime

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
    mkdirp(credential_dir)
    credential_path = os.path.join(credential_dir, "google-drive-backup.json")
    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store, flags)
        print("Storing credentials to " + credential_path)
    return credentials

# https://developers.google.com/drive/v3/web/manage-downloads

MIME_MAPPINGS = {
    "application/vnd.google-apps.document": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
    "application/vnd.google-apps.spreadsheet": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"),
    "application/vnd.google-apps.drawing": ("image/svg+xml", "svg"),
    "application/vnd.google-apps.presentation": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "pptx"),
    "application/vnd.google-apps.script": ("application/vnd.google-apps.script+json", "json"),
}

def main():

    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build("drive", "v3", http=http)

    def backup_folder(folder_id, destination):
        mkdirp(destination)
        next_page_token = ""
        query = "trashed = false and '{0}' in parents".format(folder_id)
        while True:
            result = service.files().list(fields="nextPageToken, files(id, name, mimeType, size, md5Checksum, modifiedTime, viewedByMeTime)", q=query, pageToken=next_page_token).execute()
            for item in result["files"]:
                backup_file(item, destination)
            if "nextPageToken" in result:
                next_page_token = result["nextPageToken"]
            else:
                break

    def rename(item):
        i = item["name"].rfind(".")
        if i == -1:
            return item["name"] + "-" + item["id"]
        return item["name"][:i] + "-" + item["id"] + item["name"][i:]

    backed_up_files = set()
    def backup_file(item, destination):
        key = (destination, item["name"])
        if key in backed_up_files:
            print("WARNING:", item["name"], "already exists in", destination + ".", "Renaming to", rename(item) + ".", file=sys.stderr)
            item["name"] = rename(item)
            key = (destination, item["name"])
        backed_up_files.add(key)
        if item["mimeType"] == "application/vnd.google-apps.folder":
            backup_folder(item["id"], os.path.join(destination, clean(item["name"])))
        elif item["mimeType"] in MIME_MAPPINGS:
            export_mime_type, extension = MIME_MAPPINGS[item["mimeType"]]
            output_file = os.path.join(destination, "{0}.{1}".format(clean(item["name"]), extension))
            modified_time = parse_time(item["modifiedTime"])
            if os.path.exists(output_file) and modified_time.timestamp() == os.stat(output_file).st_mtime:
                print("Unchanged", output_file)
            else:
                print("Downloading", output_file)
                data = service.files().export(fileId=item["id"], mimeType=export_mime_type).execute()
                with open(output_file, "wb") as output:
                    output.write(data)
                viewed_time = parse_time(item["viewedByMeTime"]) if "viewedByMeTime" in item else modified_time
                os.utime(output_file, times=(viewed_time.timestamp(), modified_time.timestamp()))
        elif "size" in item: # Binary file
            output_file = os.path.join(destination, clean(item["name"]))
            if "md5Checksum" in item and \
                    os.path.exists(output_file) and \
                    os.path.getsize(output_file) == int(item["size"]) and \
                    md5(output_file) == item["md5Checksum"]:
                        print("Unchanged", output_file)
            else:
                print("Downloading", output_file)
                data = service.files().get_media(fileId=item["id"]).execute()
                with open(output_file, "wb") as output:
                    output.write(data)
                modified_time = parse_time(item["modifiedTime"])
                viewed_time = parse_time(item["viewedByMeTime"]) if "viewedByMeTime" in item else modified_time
                os.utime(output_file, times=(viewed_time.timestamp(), modified_time.timestamp()))
        else:
            print("WARNING: Cannot handle", item["mimeType"], item["id"], item["name"], file=sys.stderr)

    backup_folder("root", flags.destination)

def mkdirp(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

import hashlib
def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def clean(filename):
    filename = filename.replace("/", "-")
    filename = filename.replace("\\", "-")
    filename = filename.replace(": ", " ")
    filename = filename.replace(":", " ")
    return filename

def parse_time(time):
    return datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.timezone.utc).replace(microsecond=0)

if __name__ == "__main__":
    main()
