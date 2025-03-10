#!/usr/bin/env python3

"""
This script is intended to be run in a cron job to automatically download new
WCA data zips and place them in the correct directory for the app to use them.
Each run, it'll poll the WCA API to see if there's a new export, and if there
is, download it and overwrite the existing one.

WCA data zip only gets updated roughly weekly, so no need to run this script
very often.

SCRIPT ASSUMES THE WCA DATA FOLDER IS ../wca_data/ (relative to script location)
"""

import requests
import json
import os
import zipfile
from datetime import datetime

WCA_DATA_DIR = 'wca_data'
WCA_ZIP_FILENAME = 'WCA_export.tsv.zip'
WCA_ZIP_FILEPATH = os.path.join(os.path.dirname(__file__), '..', WCA_DATA_DIR, WCA_ZIP_FILENAME)
WCA_EXPORT_POLL_URL = 'https://www.worldcubeassociation.org/api/v0/export/public'

"""
Retrieves the timestamp of the currently saved WCA data zip file. Returns None
if the file doesn't exist yet, or if it's not readable or something
"""
def get_local_file_timestamp(zip_path):
    try:
        with zipfile.ZipFile(zip_path) as z:
            with z.open('metadata.json') as f:
                metadata = json.loads(f.read())
        timestamp = datetime.strptime(metadata['export_date'], '%Y-%m-%d %H:%M:%S %Z')
        return timestamp
    except (FileNotFoundError, ValueError, KeyError):
        return None

"""
Retrieves the timestamp and download URL of the latest WCA data export from
their API endpoint. Returns as a tuple (timestamp, download URL)
"""
def poll_latest_export():
    response = requests.get(WCA_EXPORT_POLL_URL)
    if not response.ok:
        return (None, None)
    result = response.json()
    download_url = result.get('tsv_url')
    timestamp = result.get('export_date')
    if timestamp:
        timestamp = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ')
    return (timestamp, download_url)

"""
Downloads the latest WCA data export to the provided filepath.
"""
def download_wca_export(download_url, filepath):
    response = requests.get(download_url)
    if not response.ok:
        raise RuntimeError(f'unable to retrieve WCA data export from URL {download_url}')
    try:
        with open(filepath, 'wb') as f:
            f.write(response.content)
    except:
        raise RuntimeError(f'unable to write WCA data export to file {filepath}')

def main():
    file_timestamp = get_local_file_timestamp(WCA_ZIP_FILEPATH)
    print(f'local file timestamp is {file_timestamp if file_timestamp else 'not found'}')
    print('polling WCA endpoint for latest data export...')
    latest_timestamp, download_url = poll_latest_export()

    if file_timestamp and file_timestamp == latest_timestamp:
        print('latest downloaded export up to date!')
    elif download_url:
        print(f'new data export found for timestamp {latest_timestamp}')
        print('downloading (will take a moment) ...')
        download_wca_export(download_url, WCA_ZIP_FILEPATH)
        print(f'data export successfully downloaded to {WCA_ZIP_FILEPATH}')
    else:
        print('ERROR: unable to download export for some reason')
    
if __name__ == '__main__':
    main()