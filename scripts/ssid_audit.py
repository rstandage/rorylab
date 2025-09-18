from mistrs import get_credentials, get_headers, get_paginated, get, create_csv
from datetime import date, datetime
import sys
import argparse
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict

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

def get_sites(config: APIConfig):
    """Get list of sites for user selection"""
    try:
        url = f'{config.baseurl}orgs/{config.org_id}/sites'
        resp = get(url, config.headers)
        sites = []
        for site in resp:
            # Include all sites - wifi_enabled might not be in the basic site list
            # We'll filter based on the presence of WiFi configurations later if needed
            sites.append({
                'id': site.get('id'),
                'name': site.get('name'),
                'country_code': site.get('country_code', 'Unknown'),
                'wifi_enabled': site.get('wifi_enabled', True)  # Default to True if not specified
            })
        return sites
    except Exception as e:
        print(f"Error retrieving sites: {e}")
        return []

def select_site(config: APIConfig) -> str:
    """Allow user to select a site"""
    sites = get_sites(config)
    
    if not sites:
        print("No sites found")
        return None
    
    print("\nAvailable Sites:")
    print("-" * 60)
    for i, site in enumerate(sites, 1):
        wifi_status = "✓" if site.get('wifi_enabled', True) else "✗"
        print(f"{i:3}. {site['name']:<30} ({site['country_code']}) [{wifi_status}]")
    
    while True:
        try:
            choice = input(f"\nSelect site (1-{len(sites)}) or 'q' to quit: ").strip()
            if choice.lower() == 'q':
                return None
            
            index = int(choice) - 1
            if 0 <= index < len(sites):
                selected_site = sites[index]
                print(f"\nSelected: {selected_site['name']}")
                return selected_site['id']
            else:
                print(f"Please enter a number between 1 and {len(sites)}")
        except ValueError:
            print("Please enter a valid number or 'q' to quit")

def get_wlan_configs(config: APIConfig):
    """Get WLAN configurations from organization level"""
    try:
        url = f'{config.baseurl}orgs/{config.org_id}/wlans'
        resp = get(url, config.headers)
        
        wlan_configs = {}
        for wlan in resp:
            wlan_id = wlan.get('id')
            wlan_configs[wlan_id] = {
                'ssid': wlan.get('ssid'),
                'enabled': wlan.get('enabled', False),
                'auth_type': wlan.get('auth', {}).get('type', 'unknown'),
                'vlan_enabled': wlan.get('vlan_enabled', False),
                'vlan_id': wlan.get('vlan_id'),
                'bands': wlan.get('bands', []),
                'hide_ssid': wlan.get('hide_ssid', False),
                'wlan_limit_up': wlan.get('wlan_limit_up', 0),
                'wlan_limit_down': wlan.get('wlan_limit_down', 0),
                'client_limit_up': wlan.get('client_limit_up', 0),
                'client_limit_down': wlan.get('client_limit_down', 0),
                'max_idletime': wlan.get('max_idletime', 0),
                'portal_enabled': wlan.get('portal', {}).get('enabled', False),
                'mist_nac_enabled': wlan.get('mist_nac', {}).get('enabled', False),
                'created_time': wlan.get('created_time'),
                'modified_time': wlan.get('modified_time')
            }
        
        return wlan_configs
    except Exception as e:
        print(f"Error retrieving WLAN configurations: {e}")
        return {}

def get_site_client_data(config: APIConfig, site_id):
    """Get client data for specific site"""
    try:
        url = f'{config.baseurl}orgs/{config.org_id}/clients/search'
        params = {
            'site_id': site_id,
            'duration': config.duration,
            'limit': config.limit
        }
        
        # Build URL with parameters
        param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{url}?{param_str}"
        
        print(f"Fetching client data for site (duration: {config.duration})...")
        clients = get_paginated(
            full_url,
            config.headers,
            config.limit,
            show_progress=True,
            debug=config.debug
        )
        
        return clients
        
    except Exception as e:
        print(f"Error fetching site client data: {e}")
        return []

def analyze_ssid_usage(clients, wlan_configs):
    """Analyze SSID usage statistics"""
    ssid_stats = defaultdict(lambda: {
        'total_clients': 0,
        'unique_clients': set(),
        'client_count_over_time': defaultdict(int),
        'bands_used': defaultdict(int),
        'protocols_used': defaultdict(int),
        'manufacturers': defaultdict(int),
        'device_types': defaultdict(int),
        'vlans_used': defaultdict(int),
        'first_seen': None,
        'last_seen': None
    })
    
    for client in clients:
        ssid = client.get('last_ssid', 'Unknown')
        if not ssid or ssid == 'Unknown':
            continue
        
        wlan_id = client.get('last_wlan_id')
        client_mac = client.get('mac')
        timestamp = client.get('timestamp')
        
        # Track unique clients
        if client_mac:
            ssid_stats[ssid]['unique_clients'].add(client_mac)
        
        # Track total connections (including reconnections)
        ssid_stats[ssid]['total_clients'] += 1
        
        # Track timing
        if timestamp:
            if not ssid_stats[ssid]['first_seen'] or timestamp < ssid_stats[ssid]['first_seen']:
                ssid_stats[ssid]['first_seen'] = timestamp
            if not ssid_stats[ssid]['last_seen'] or timestamp > ssid_stats[ssid]['last_seen']:
                ssid_stats[ssid]['last_seen'] = timestamp
        
        # Track bands
        band = client.get('band')
        if band:
            ssid_stats[ssid]['bands_used'][band] += 1
        
        # Track protocols
        protocol = client.get('protocol')
        if protocol:
            ssid_stats[ssid]['protocols_used'][protocol] += 1
        
        # Track manufacturers
        mfg = client.get('mfg')
        if mfg:
            ssid_stats[ssid]['manufacturers'][mfg] += 1
        
        # Track device types
        device_type = client.get('last_device')
        if device_type:
            ssid_stats[ssid]['device_types'][device_type] += 1
        
        # Track VLANs
        vlan = client.get('last_vlan')
        if vlan:
            ssid_stats[ssid]['vlans_used'][vlan] += 1
    
    return ssid_stats

def format_timestamp(timestamp):
    """Convert timestamp to readable format"""
    if timestamp:
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, OSError):
            return 'Invalid timestamp'
    return 'N/A'

def format_list_data(data_dict, limit=3):
    """Format dictionary data as a readable string"""
    if not data_dict:
        return 'None'
    
    # Sort by count (descending) and take top items
    sorted_items = sorted(data_dict.items(), key=lambda x: x[1], reverse=True)[:limit]
    result = []
    
    for item, count in sorted_items:
        result.append(f"{item} ({count})")
    
    if len(data_dict) > limit:
        result.append(f"... +{len(data_dict) - limit} more")
    
    return '; '.join(result)

def create_ssid_report(ssid_stats, wlan_configs, site_info, config):
    """Create formatted SSID report data"""
    report_data = []
    
    for ssid, stats in ssid_stats.items():
        # Find matching WLAN config
        wlan_config = None
        for wlan_id, config_data in wlan_configs.items():
            if config_data['ssid'] == ssid:
                wlan_config = config_data
                break
        
        # Calculate unique client count
        unique_clients = len(stats['unique_clients'])
        
        # Get most used band and protocol
        top_band = max(stats['bands_used'].items(), key=lambda x: x[1]) if stats['bands_used'] else ('Unknown', 0)
        top_protocol = max(stats['protocols_used'].items(), key=lambda x: x[1]) if stats['protocols_used'] else ('Unknown', 0)
        
        data = {
            'SSID': ssid,
            'Site': site_info['name'],
            'Enabled': wlan_config['enabled'] if wlan_config else 'Unknown',
            'Authentication': wlan_config['auth_type'] if wlan_config else 'Unknown',
            'Hidden': wlan_config['hide_ssid'] if wlan_config else 'Unknown',
            'VLAN Enabled': wlan_config['vlan_enabled'] if wlan_config else 'Unknown',
            'VLAN ID': wlan_config['vlan_id'] if wlan_config else 'Unknown',
            'Supported Bands': ', '.join(wlan_config['bands']) if wlan_config and wlan_config['bands'] else 'Unknown',
            'Total Connections': stats['total_clients'],
            'Unique Clients': unique_clients,
            'Most Used Band': f"{top_band[0]} ({top_band[1]} clients)" if top_band[0] != 'Unknown' else 'None',
            'Most Used Protocol': f"{top_protocol[0]} ({top_protocol[1]} clients)" if top_protocol[0] != 'Unknown' else 'None',
            'Top Manufacturers': format_list_data(stats['manufacturers']),
            'Top Device Types': format_list_data(stats['device_types']),
            'VLANs Used': format_list_data(stats['vlans_used']),
            'First Seen': format_timestamp(stats['first_seen']),
            'Last Seen': format_timestamp(stats['last_seen']),
            'WLAN Upload Limit (Kbps)': wlan_config['wlan_limit_up'] if wlan_config else 'Unknown',
            'WLAN Download Limit (Kbps)': wlan_config['wlan_limit_down'] if wlan_config else 'Unknown',
            'Client Upload Limit (Kbps)': wlan_config['client_limit_up'] if wlan_config else 'Unknown',
            'Client Download Limit (Kbps)': wlan_config['client_limit_down'] if wlan_config else 'Unknown',
            'Max Idle Time (sec)': wlan_config['max_idletime'] if wlan_config else 'Unknown',
            'Portal Enabled': wlan_config['portal_enabled'] if wlan_config else 'Unknown',
            'Mist NAC Enabled': wlan_config['mist_nac_enabled'] if wlan_config else 'Unknown'
        }
        
        report_data.append(data)
    
    # Sort by unique clients (descending)
    report_data.sort(key=lambda x: x['Unique Clients'], reverse=True)
    
    return report_data

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Generate SSID audit report for a selected site',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Duration examples:
  7d     - 7 days (default)
  2w     - 2 weeks (14 days)
  24h    - 24 hours (1 day)
  30d    - 30 days (maximum)

This script will:
1. Show you a list of WiFi-enabled sites
2. Allow you to select a specific site to audit
3. Generate a comprehensive SSID usage report including:
   - Client connection statistics
   - SSID configuration details
   - Usage patterns and trends
   - Security and VLAN information

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

def main():
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Validate duration
        if not validate_duration(args.duration):
            print(f"Error: Invalid duration '{args.duration}'. Must be between 1-30 days.")
            print("Examples: 7d, 2w, 24h, 30d")
            sys.exit(1)
        
        print(f"Starting SSID audit for duration: {args.duration}")
        
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
        
        # Get available sites and let user select one
        print("Fetching available sites...")
        selected_site_id = select_site(config)
        if not selected_site_id:
            print("No site selected. Exiting.")
            return
        
        # Get site info for selected site
        sites = get_sites(config)
        selected_site = next((site for site in sites if site['id'] == selected_site_id), None)
        if not selected_site:
            print("Error: Could not find selected site details.")
            return
        
        # Get WLAN configurations
        print("Fetching WLAN configurations...")
        wlan_configs = get_wlan_configs(config)
        
        # Get client data for selected site
        clients = get_site_client_data(config, selected_site_id)
        
        if not clients:
            print("No client data found for the specified site and duration.")
            return
        
        print(f"Found {len(clients)} client connections")
        
        # Analyze SSID usage
        print("Analyzing SSID usage patterns...")
        ssid_stats = analyze_ssid_usage(clients, wlan_configs)
        
        if not ssid_stats:
            print("No SSID usage data found.")
            return
        
        # Create formatted report
        print("Generating SSID audit report...")
        report_data = create_ssid_report(ssid_stats, wlan_configs, selected_site, config)
        
        # Create filename
        site_name_clean = selected_site['name'].replace(" ", "_").replace("/", "_")
        filename = f'{orgname}_{site_name_clean}_SSID_Audit_{args.duration}_{date.today()}.csv'
        file_path = config.config_dir / filename
        
        # Ensure directory exists
        config.config_dir.mkdir(exist_ok=True)
        
        # Create CSV file
        create_csv(report_data, file_path)
        
        # Print summary
        print(f'\nSSID Audit Report Created: {file_path}')
        print(f'Site: {selected_site["name"]} ({selected_site["country_code"]})')
        print(f'Duration: {args.duration}')
        print(f'Total SSIDs analyzed: {len(report_data)}')
        print(f'Total client connections: {sum(stats["total_clients"] for stats in ssid_stats.values())}')
        print(f'Total unique clients: {len(set().union(*[stats["unique_clients"] for stats in ssid_stats.values()]))}')
        
        # Show top SSIDs by usage
        print("\nTop SSIDs by unique clients:")
        for i, ssid_data in enumerate(report_data[:5], 1):
            print(f"  {i}. {ssid_data['SSID']}: {ssid_data['Unique Clients']} unique clients")
        
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