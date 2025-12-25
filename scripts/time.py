#!/usr/bin/env python3

"""
This script tests total time taken
"""

import requests

def time_wca_id_request(wca_id='2012PARK03'):
    url = 'http://localhost:5000/'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0',
    }

    data = {
        'chart-by': 'chart-by-solve-num',
        'secondary-y-axis': 'none',
        'subx-threshold': 'auto',
        'subx-override': '',
        'day-end-hour': '3',
        'custom-trimmed-mean': 'no',
        'trim-percentage': '5',
        'merge-sessions': 'merge-sessions-no',
        'tz': 'America/Phoenix',
        'textinput': wca_id,
    }

    files = {
        'file': ('', '', 'application/octet-stream')
    }

    try:
        response = requests.post(url, headers=headers, data=data, files=files, timeout=30)
        duration = response.elapsed.total_seconds()

        print(f"{wca_id} - Status {response.status_code} - Time Taken: {duration:.4f} sec")
        
        response.raise_for_status()

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")

if __name__ == "__main__":
    print('requests may take a long time to complete, be patient\n')
    print("Testing WCA ID requests...")
    time_wca_id_request('2012PARK03')
    time_wca_id_request('2024ANGE07')
