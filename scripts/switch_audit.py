from mistrs import get_credentials, get_headers, get_paginated, get, create_csv
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
    limit: int = 50
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

def format_data(Data_Array, Site_Array):
    New_Array = []
    for switch in Data_Array:
        site_id = switch.get('site_id')
        site_name, site_cc = find_site_details(site_id, Site_Array)
        online = int(switch.get('timestamp')) - switch.get('uptime')
        if switch.get('uptime') is None:
            uptime = None
            fonline = None
        else:
            dt = datetime.fromtimestamp(switch.get('uptime'))
            uptime = dt.strftime('%dd %Hh %Mm')
            fonline = datetime.fromtimestamp(online)
        data = {
            'Name': switch.get('last_hostname'),
            'SKU': switch.get('model'),
            'Site': site_name,
            'MAC': switch.get('mac'),
            'IP': switch.get('ip'),
            'Country Code': site_cc,
            'Firmware': switch.get('version'),
            'Uptime': uptime,
            'Cluster Size': switch.get('num_members'),
            'Online Since': fonline
        }
        New_Array.append(data)
    return New_Array

def main():
    try:
        # Get credentials and setup
        credentials = get_credentials(otp=False)
        org_id = get_org_id(credentials)
        config = APIConfig(
            baseurl=credentials["api_url"],
            headers=get_headers(credentials["api_token"]),
            org_id=org_id
        )
        orgname = get_org_name(config).replace(" ", "_")
        Site_Array = create_site_array(config)
        Switch_Array1 = get_paginated(
            f'{config.baseurl}orgs/{config.org_id}/devices/search?type=switch',
            config.headers, config.limit,
            show_progress=True
        )
        Device_Data = format_data(Switch_Array1, Site_Array)
        filename  = f'{orgname}_Switch_Report_{date.today()}.csv'
        file_path = config.config_dir / filename
        print(f'Created Report {file_path}')
        create_csv(Device_Data, file_path)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)

if __name__ == "__main__":
    main()