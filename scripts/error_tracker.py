from mistrs import get_credentials, get_headers, get_paginated, get, analyze_errors
import sys
from datetime import date
from pathlib import Path
from dataclasses import dataclass

@dataclass
class APIConfig:
    baseurl: str
    headers: dict
    org_id: str
    limit: int = 1000
    error: str = 'REPEATED_AUTH_FAILURES'
    duration:str = '24h'
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
        }
        Array.append(site)
    return Array

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
        org_name = get_org_name(config).replace(" ", "_")
        Site_Array = create_site_array(config)

        # Get disconnection events
        AP_Array1 = get_paginated(
            f'{config.baseurl}orgs/{config.org_id}/device/events?'
            f'type={config.error}&duration={config.duration}',
            config.headers, config.limit,
            show_progress=True
        )

        print(f'Found {len(AP_Array1)} {config.error} events')

        # Ask user for grouping preference
        while True:
            group_by = input("Group by 'site' or 'ap'? ").lower().strip()
            if group_by in ['site', 'ap']:
                break
            print("Please enter either 'site' or 'ap'")

        # Ask user if they want to limit to top N sites/APs
        top_n = None
        limit_display = input("Limit display to top N sites/APs? (y/n): ").lower().strip() == 'y'
        if limit_display:
            while True:
                try:
                    top_n = int(input("Enter number of top sites/APs to display: "))
                    break
                except ValueError:
                    print("Please enter a valid number")

        # Ask if user wants to save the figure
        save_fig = input("Save figure? (y/n): ").lower().strip() == 'y'
        save_path = None
        if save_fig:
            top_str = f"_top{top_n}" if top_n else ""
            save_path = f"{config.config_dir}/{org_name}_{config.error}_{group_by}{top_str}_{config.duration}_{date.today()}.png"

        # Analyze and visualize the data
        processed_data = analyze_errors(
            data=AP_Array1,
            site_array=Site_Array,
            error=config.error,
            group_by=group_by,
            top_n=top_n,
            save_path=save_path
        )

        print("Analysis complete!")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()