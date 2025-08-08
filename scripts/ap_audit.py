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

def find_lldp_stats(mac, AP_Array1):
    speed = ''
    switch = ''
    port = ''
    desc = ''
    for i in AP_Array1:
        if i.get('mac') == mac:
            speed = i.get('eth0_port_speed')
            switch = i.get('lldp_system_name')
            port = i.get('lldp_port_id')
            desc = i.get('lldp_system_desc')
            break
    return speed, switch, port, desc

def get_ap_config(config: APIConfig, siteid, mac):
    # uses the mac address to get BSSIDs (increases API count to 1 per AP)
    try:
        url = f'{config.baseurl}sites/{siteid}/devices/last_config/search?ap={mac}'
        resp = get(url, config.headers)
        results = resp.get('results', [{}])[0]
        return results.get('radio_macs', []), results.get('ssids', [])
    except Exception as e:
        print(f"Error getting AP config for MAC {mac}: {e}")
        return [], []

def format_data(AP_Array1, AP_Array2, Site_Array, config: APIConfig):
    New_Array = []
    for ap in AP_Array2:
        site_id = ap.get('site_id')
        site_name, site_cc = find_site_details(site_id, Site_Array)
        mac = ap.get('mac')
        if ap.get('uptime') is None:
            uptime = None
        else:
            dt = datetime.fromtimestamp(ap.get('uptime'))
            uptime = dt.strftime('%dd %Hh %Mm')
        speed, switch, port, desc = find_lldp_stats(mac, AP_Array1)
        data = {
            'Name': ap.get('name'),
            'Site': site_name,
            'MAC': mac,
            'Country Code': site_cc,
            'Type': ap.get('model'),
            'Firmware': ap.get('version'),
            'Status': ap.get('status'),
            'Uptime': uptime,
            'IP': ap.get('ip'),
            'Port Speed': speed,
            'LLDP System Name': switch,
            'LLDP Port': port,
            'LLDP System Description': desc
        }
        if config.get_config:
            bssid_list, ssid_list = get_ap_config(config, site_id, mac)
            data.update({
            'SSIDS': ssid_list,
            'BSSIDs': bssid_list,
            '2.4Ghz Power': ap.get('band_24_power'),
            '2.4Ghz Channel': ap.get('band_24_channel'),
            '5Ghz Power': ap.get('band_5_power'),
            '5Ghz Channel': ap.get('band_5_channel'),
            '6Ghz Power': ap.get('band_6_power'),
            '6Ghz Channel': ap.get('band_6_channel')
        })
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
        AP_Array1 = get_paginated(
            f'{config.baseurl}orgs/{config.org_id}/devices/search?type=ap',
            config.headers, config.limit,
            show_progress=True
        )
        AP_Array2 = get_paginated(
            f'{config.baseurl}orgs/{config.org_id}/stats/devices?type=ap',
            config.headers, config.limit,
            show_progress=True,
            debug = False
        )
        Device_Data = format_data(AP_Array1, AP_Array2, Site_Array, config)
        filename  = f'{orgname}_AP_Report_{date.today()}.csv'
        file_path = config.config_dir / filename
        print(f'Created Report {file_path}')
        create_csv(Device_Data, file_path)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)

if __name__ == "__main__":
    main()

