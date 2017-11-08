# Google Drive Backup

This script will backup a user's Google Drive contents to a local folder. Binary files will be downloaded as-is, while Google Documents will be exported to locally viewable formats as follows:

```
Google Docs -> docx
Google Sheets -> xlsx
Google Slides -> pptx
Google Drawings -> svg
Google Scripts -> json
```

Non-binary files other than those listed above will be skipped with a message logged to the console.

This script requires a client_secret.json file containing credentials that identify the application to Google's OAuth 2.0 server. To obtain application credentials for your project, complete these steps:

1. Create a new application in the [Google API Console](https://console.developers.google.com).
2. Enable the [Google Drive API](https://console.developers.google.com/apis/library/drive.googleapis.com/).
3. Open the [Credentials page](https://console.developers.google.com/apis/credentials) in the API Console.
4. Create the OAuth 2.0 credentials by clicking `OAuth client ID` under the `Create credentials` heading.
5. Select the `Other` application type and give the credentials a name.
6. Download the newly created credentials in JSON format and rename to client_secret.json.

## Usage

```
./backup-google-drive.py <destination>
```

## License

Copyright 2017 Andrew Naoum

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
