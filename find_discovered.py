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
    limit: int = 1000
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

def get_sites(config: APIConfig):
    """Get list of sites in the organization"""
    url = f'{config.baseurl}orgs/{config.org_id}/sites'
    resp = get(url, config.headers)
    sites = []
    for site in resp:
        sites.append({
            'id': site.get('id'),
            'name': site.get('name'),
            'country_code': site.get('country_code', '')
        })
    return sites

def get_discovered_switches_for_site(config: APIConfig, site_id: str):
    """Get discovered switches for a specific site"""
    try:
        url = f'{config.baseurl}sites/{site_id}/stats/discovered_switches/search'
        resp = get(url, config.headers)
        return resp.get('results', [])
    except Exception as e:
        print(f"Error getting discovered switches for site {site_id}: {e}")
        return []

def format_switch_data(switches_data, sites_dict):
    """Format the discovered switches data for CSV output"""
    formatted_data = []
    
    for switch in switches_data:
        site_id = switch.get('site_id')
        site_info = sites_dict.get(site_id, {})
        
        # Get AP count and redundancy info
        aps = switch.get('aps', [])
        ap_redundancy = switch.get('ap_redundancy', {})
        
        # Format timestamp
        timestamp = switch.get('timestamp')
        if timestamp:
            formatted_timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        else:
            formatted_timestamp = ''
        
        # Create base switch data
        switch_data = {
            'Site Name': site_info.get('name', ''),
            'Site ID': site_id,
            'Country Code': site_info.get('country_code', ''),
            'System Name': switch.get('system_name', ''),
            'Hostname': switch.get('hostname', ''),
            'Management Address': switch.get('mgmt_addr', ''),
            'Model': switch.get('model', ''),
            'Version': switch.get('version', ''),
            'Vendor': switch.get('vendor', ''),
            'Adopted': switch.get('adopted', False),
            'Chassis ID': ', '.join(switch.get('chassis_id', [])),
            'System Description': switch.get('system_desc', ''),
            'Timestamp': formatted_timestamp,
            'Number of APs': ap_redundancy.get('num_aps', 0),
            'APs with Switch Redundancy': ap_redundancy.get('num_aps_with_switch_redundancy', 0),
            'Connected APs': len(aps)
        }
        
        # Add AP details if any APs are connected
        if aps:
            ap_details = []
            for ap in aps:
                ap_detail = f"{ap.get('hostname', 'Unknown')} ({ap.get('mac', '')}) on {ap.get('port', '')} - {ap.get('power_draw', 0)}mW"
                ap_details.append(ap_detail)
            switch_data['AP Details'] = '; '.join(ap_details)
        else:
            switch_data['AP Details'] = 'No APs connected'
        
        formatted_data.append(switch_data)
    
    return formatted_data

def main():
    try:
        # Get credentials and setup
        print("Getting credentials...")
        credentials = get_credentials(otp=False)
        org_id = get_org_id(credentials)
        config = APIConfig(
            baseurl=credentials["api_url"],
            headers=get_headers(credentials["api_token"]),
            org_id=org_id
        )
        
        print("Getting organization name...")
        orgname = get_org_name(config).replace(" ", "_")
        
        print("Getting list of sites...")
        sites = get_sites(config)
        sites_dict = {site['id']: site for site in sites}
        print(f"Found {len(sites)} sites")
        
        print("Getting discovered switches for each site...")
        all_switches = []
        
        for i, site in enumerate(sites, 1):
            site_id = site['id']
            site_name = site['name']
            print(f"Processing site {i}/{len(sites)}: {site_name}")
            
            switches = get_discovered_switches_for_site(config, site_id)
            if switches:
                print(f"  Found {len(switches)} discovered switches")
                all_switches.extend(switches)
            else:
                print("  No discovered switches found")
        
        print(f"\nTotal discovered switches found: {len(all_switches)}")
        
        if not all_switches:
            print("No discovered switches found in any site. Exiting.")
            return
        
        print("Formatting data...")
        formatted_data = format_switch_data(all_switches, sites_dict)
        
        # Create output file
        filename = f'{orgname}_Discovered_Switches_Report_{date.today()}.csv'
        file_path = config.config_dir / filename
        
        print(f"Creating report: {file_path}")
        config.config_dir.mkdir(exist_ok=True)  # Ensure directory exists
        create_csv(formatted_data, file_path)
        
        print(f"\nReport created successfully: {file_path}")
        print(f"Total switches reported: {len(formatted_data)}")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()