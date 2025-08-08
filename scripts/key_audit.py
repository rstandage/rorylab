from mistrs import get_credentials, get_headers, get_paginated, get, create_csv, edittime, jprint
from datetime import date, datetime
import sys
from dataclasses import dataclass
from pathlib import Path

@dataclass
class APIConfig:
    baseurl: str
    headers: dict
    org_id: str
    get_config: bool = False
    limit: int = 200
    config_dir: Path = Path.home() / "created_files"

class APIError(Exception):
    pass

def get_org_id(credentials: dict) -> str:
    org_id = credentials.get("org_id")
    if org_id is None:
        print("\nNo organization ID found in credentials.")
        while True:
            org_id = input("Please enter your organization ID: ").strip()
            if org_id:  # Check if input is not empty
                confirm = input(f"Confirm organization ID '{org_id}' is correct? (y/n): ").lower()
                if confirm == 'y':
                    break
            print("Please enter a valid organization ID")
    return org_id

def get_org_name(config: APIConfig):
    url = f'{config.baseurl}orgs/{config.org_id}/stats'
    resp = get(url, config.headers)
    return resp.get('name')

def create_site_array(config: APIConfig):
    # Creates Array of item names and IDs and country code for sites.
    Array = []
    url = f'{config.baseurl}orgs/{config.org_id}/sites'
    resp = get(url, config.headers)
    for i in resp:
        site = {
            'id': i.get('id'),
            'name': i.get('name'),
            'cc': i.get('country_code')
        }
        Array.append(site)
    return Array

def find_site_details(id, Site_Array):
    name = ''
    cc = ''
    for s in Site_Array:
        if s.get('id') == id:
            name = s.get('name')
            cc = s.get('cc')
            break
    return name, cc

def format_data(array):
    data = []
    for i in array:
        key = {
            'name': i.get('name'),
            'created': edittime(i.get('created_time')),
            'created_by': i.get('created_by'),
            'key':(i.get('key')),
            'last_used':edittime(i.get('last_used')),
            'scope': i['privileges'][0]['scope'],
            'role': i['privileges'][0]['role']
        }
        data.append(key)
    return data

def main():
    try:
        # Get credentials and setup
        credentials = get_credentials(otp=True)
        org_id = get_org_id(credentials)
        config = APIConfig(
            baseurl=credentials["api_url"],
            headers=get_headers(credentials["api_token"]),
            org_id=org_id
        )
        orgname = get_org_name(config).replace(" ", "_")
        Site_Array = create_site_array(config)
        Key_Array1 = get_paginated(
            f'{config.baseurl}orgs/{config.org_id}/apitokens',
            config.headers, config.limit,
            show_progress=True
        )
        jprint(Key_Array1)
        Device_Data = format_data(Key_Array1)
        filename  = f'{orgname}_API_Key_Report_{date.today()}.csv'
        file_path = config.config_dir / filename
        print(f'Created Report {file_path}')
        create_csv(Device_Data, file_path)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)

if __name__ == "__main__":
    main()

