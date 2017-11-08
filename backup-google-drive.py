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
parser.add_argument("destination", help="The local folder to which the Google Drive backup will be made. Existing files will be overwritten.")
parser.add_argument("--redownload-docs", help="Re-download Google Documents even if timestamps show no changes have been made.", action='store_true')
parser.add_argument("--redownload-files", help="Re-download binary files even if MD5 checksums match local files.", action='store_true')
parser.add_argument("--trashed", help="This will download items located in the Trash, instead of the regular drive.", action='store_true')
parser.add_argument("--credential-file", help="Location of the credential file storing user credentials (default: user.json).", default="user.json")
flags = parser.parse_args()

SCOPES = "https://www.googleapis.com/auth/drive.readonly"
CLIENT_SECRET_FILE = "client_secret.json"
APPLICATION_NAME = "Google Drive Backup"

def get_credentials(credential_path):
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

    credentials = get_credentials(flags.credential_file)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build("drive", "v3", http=http)

    def backup_folder(folder_id, destination):
        mkdirp(destination)
        next_page_token = ""
        query = "trashed = {0} and '{1}' in parents".format(flags.trashed, folder_id)
        while True:
            result = service.files().list(fields="nextPageToken, files(id, name, mimeType, size, md5Checksum, modifiedTime, viewedByMeTime)", q=query, pageToken=next_page_token).execute()
            for item in result["files"]:
                backup_file(item, destination)
            if "nextPageToken" in result:
                next_page_token = result["nextPageToken"]
            else:
                break

    backed_up_files = set()
    def rename(filename, file_id):
        i = filename.rfind(".")
        if i == -1:
            return filename + "-" + file_id
        return filename[:i] + "-" + file_id + filename[i:]
    def clean(filename):
        filename = filename.replace("/", "-")
        filename = filename.replace("\\", "-")
        filename = filename.replace(": ", " ")
        filename = filename.replace(":", " ")
        return filename
    def check_name(destination, filename, file_id):
        key = (destination, filename)
        if key in backed_up_files:
            new_filename = rename(filename, file_id)
            print("WARNING:", filename, "already exists in", destination + ".", "Renaming to", new_filename + ".", file=sys.stderr)
            key = (destination, new_filename)
            filename = new_filename
        backed_up_files.add(key)
        return clean(filename)

    def backup_file(item, destination):
        if item["mimeType"] == "application/vnd.google-apps.folder":
            folder_name = os.path.join(destination, check_name(destination, item["name"], item["id"]))
            backup_folder(item["id"], folder_name)
        elif item["mimeType"] in MIME_MAPPINGS:
            export_mime_type, extension = MIME_MAPPINGS[item["mimeType"]]
            output_file = os.path.join(destination, check_name(destination, "{0}.{1}".format(item["name"], extension), item["id"]))
            modified_time = parse_time(item["modifiedTime"])
            if not flags.redownload_docs and os.path.exists(output_file) and modified_time.timestamp() == os.stat(output_file).st_mtime:
                print("Unchanged", output_file)
            else:
                print("Downloading", output_file)
                data = service.files().export(fileId=item["id"], mimeType=export_mime_type).execute()
                with open(output_file, "wb") as output:
                    output.write(data)
                viewed_time = parse_time(item["viewedByMeTime"]) if "viewedByMeTime" in item else modified_time
                os.utime(output_file, times=(viewed_time.timestamp(), modified_time.timestamp()))
        elif "size" in item: # Binary file
            output_file = os.path.join(destination, check_name(destination, item["name"], item["id"]))
            if not flags.redownload_files and \
                    "md5Checksum" in item and \
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

def parse_time(time):
    return datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.timezone.utc).replace(microsecond=0)

if __name__ == "__main__":
    main()
