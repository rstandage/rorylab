from mistrs import get_credentials, get_headers, get_paginated, get, create_csv
from datetime import date, datetime, timedelta
import sys
import argparse
from dataclasses import dataclass
from pathlib import Path

@dataclass
class APIConfig:
    baseurl: str
    headers: dict
    org_id: str
    duration: str = "7d"
    limit: int = 200
    config_dir: Path = Path.home() / "created_files"
    debug: bool = False

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
    """Get organization name for filename"""
    try:
        url = f'{config.baseurl}orgs/{config.org_id}/stats'
        resp = get(url, config.headers)
        return resp.get('name', 'Unknown_Org')
    except Exception as e:
        print(f"Warning: Could not retrieve org name: {e}")
        return 'Unknown_Org'

def create_site_array(config: APIConfig):
    """Creates Array of site names and IDs for mapping."""
    sites = {}
    try:
        url = f'{config.baseurl}orgs/{config.org_id}/sites'
        resp = get(url, config.headers)
        for site in resp:
            sites[site.get('id')] = {
                'name': site.get('name'),
                'country_code': site.get('country_code')
            }
    except Exception as e:
        print(f"Warning: Could not retrieve sites: {e}")
    return sites

def find_site_details(site_id, site_array):
    """Find site name and country code by site ID"""
    site_info = site_array.get(site_id, {})
    return site_info.get('name', 'Unknown'), site_info.get('country_code', 'Unknown')

def format_timestamp(timestamp):
    """Convert timestamp to readable format"""
    if timestamp:
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, OSError):
            return 'Invalid timestamp'
    return 'N/A'

def get_client_data(config: APIConfig, site_array):
    """Get wireless client data using the search API"""
    print(f"Fetching wireless clients for the last {config.duration}...")
    
    try:
        # Use the search API with pagination
        url = f'{config.baseurl}orgs/{config.org_id}/clients/search'
        params = {
            'duration': config.duration,
            'limit': config.limit
        }
        
        # Build URL with parameters
        param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{url}?{param_str}"
        
        # Get paginated results
        clients = get_paginated(
            full_url,
            config.headers,
            config.limit,
            show_progress=True,
            debug=config.debug
        )
        
        return clients
        
    except Exception as e:
        print(f"Error fetching client data: {e}")
        return []

def format_client_data(clients, site_array):
    """Format client data for CSV export"""
    formatted_data = []
    
    for client in clients:
        site_id = client.get('site_id')
        site_name, country_code = find_site_details(site_id, site_array)
        
        # Handle array fields - take the last/most recent values
        last_ap = client.get('last_ap', '')
        last_ip = client.get('last_ip', '')
        last_hostname = client.get('last_hostname', '')
        last_ssid = client.get('last_ssid', '')
        last_device = client.get('last_device', '')
        last_os = client.get('last_os', '')
        last_model = client.get('last_model', '')
        last_vlan = client.get('last_vlan', '')
        
        # Format timestamp
        last_seen = format_timestamp(client.get('timestamp'))
        
        data = {
            'MAC Address': client.get('mac', ''),
            'Site': site_name,
            'Country Code': country_code,
            'Hostname': last_hostname,
            'IP Address': last_ip,
            'SSID': last_ssid,
            'VLAN': last_vlan,
            'Last AP': last_ap,
            'Manufacturer': client.get('mfg', ''),
            'Device Type': last_device,
            'Device Model': last_model,
            'OS': last_os,
            'OS Version': client.get('last_os_version', ''),
            'Band': client.get('band', ''),
            'Protocol': client.get('protocol', ''),
            'Random MAC': client.get('random_mac', False),
            'Last Seen': last_seen,
            'Username': ', '.join(client.get('username', [])) if client.get('username') else '',
            'PSK Name': ', '.join(client.get('psk_name', [])) if client.get('psk_name') else ''
        }
        
        formatted_data.append(data)
    
    return formatted_data

def validate_duration(duration_str):
    """Validate duration string and convert to days for validation"""
    try:
        if duration_str.endswith('d'):
            days = int(duration_str[:-1])
        elif duration_str.endswith('w'):
            days = int(duration_str[:-1]) * 7
        elif duration_str.endswith('h'):
            days = int(duration_str[:-1]) / 24
        else:
            raise ValueError("Invalid duration format")
        
        if days < 1 or days > 30:
            raise ValueError("Duration must be between 1 and 30 days")
        
        return True
    except (ValueError, IndexError):
        return False

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Generate WiFi client audit report',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Duration examples:
  7d     - 7 days (default)
  2w     - 2 weeks (14 days)
  24h    - 24 hours (1 day)
  30d    - 30 days (maximum)

Authentication:
  Uses OTP=True for enhanced security by default.
        """
    )
    
    parser.add_argument(
        '--duration', '-d',
        default='7d',
        help='Time period to audit (default: 7d, max: 30d). Examples: 7d, 2w, 24h'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='API request limit per call (default: 200)'
    )
    
    return parser.parse_args()

def main():
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Validate duration
        if not validate_duration(args.duration):
            print(f"Error: Invalid duration '{args.duration}'. Must be between 1-30 days.")
            print("Examples: 7d, 2w, 24h, 30d")
            sys.exit(1)
        
        print(f"Starting WiFi client audit for duration: {args.duration}")
        
        # Get credentials with OTP for best practice security
        credentials = get_credentials(otp=True)
        org_id = get_org_id(credentials)
        
        # Setup configuration
        config = APIConfig(
            baseurl=credentials["api_url"],
            headers=get_headers(credentials["api_token"]),
            org_id=org_id,
            duration=args.duration,
            limit=args.limit if args.limit else 200,
            debug=args.debug
        )
        
        # Get organization name for filename
        orgname = get_org_name(config).replace(" ", "_")
        
        # Create site mapping
        print("Fetching site information...")
        site_array = create_site_array(config)
        
        # Get client data
        clients = get_client_data(config, site_array)
        
        if not clients:
            print("No clients found for the specified duration.")
            return
        
        print(f"Found {len(clients)} clients")
        
        # Format data for CSV
        print("Formatting client data...")
        formatted_data = format_client_data(clients, site_array)
        
        # Create filename with duration and date
        filename = f'{orgname}_WiFi_Clients_{args.duration}_{date.today()}.csv'
        file_path = config.config_dir / filename
        
        # Ensure directory exists
        config.config_dir.mkdir(exist_ok=True)
        
        # Create CSV file
        create_csv(formatted_data, file_path)
        print(f'Created client audit report: {file_path}')
        print(f'Total clients exported: {len(formatted_data)}')
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()