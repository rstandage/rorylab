from mistrs import get_credentials, get_headers, get, create_csv
from datetime import date, datetime
import sys
from dataclasses import dataclass
from pathlib import Path

@dataclass
class APIConfig:
    baseurl: str
    headers: dict
    org_id: str
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
            if org_id:
                confirm = input(f"Confirm organization ID '{org_id}' is correct? (y/n): ").lower()
                if confirm == 'y':
                    break
            print("Please enter a valid organization ID")
    return org_id

def get_org_name(config: APIConfig):
    url = f'{config.baseurl}orgs/{config.org_id}/stats'
    resp = get(url, config.headers)
    return resp.get('name')

def get_licenses(config: APIConfig):
    """Fetch license data from the Mist API"""
    url = f'{config.baseurl}orgs/{config.org_id}/licenses'
    resp = get(url, config.headers)
    return resp

def format_license_data(license_response: dict):
    """Format license data for CSV output"""
    licenses = license_response.get('licenses', [])
    formatted_data = []
    
    for lic in licenses:
        # Convert timestamps to readable dates
        start_date = datetime.fromtimestamp(lic.get('start_time', 0)).strftime('%Y-%m-%d')
        end_date = datetime.fromtimestamp(lic.get('end_time', 0)).strftime('%Y-%m-%d')
        created_date = datetime.fromtimestamp(lic.get('created_time', 0)).strftime('%Y-%m-%d %H:%M:%S')
        
        # Calculate days until expiry
        end_timestamp = lic.get('end_time', 0)
        now = datetime.now().timestamp()
        days_until_expiry = int((end_timestamp - now) / 86400)  # 86400 seconds in a day
        
        # Determine status
        if days_until_expiry < 0:
            status = 'Expired'
        elif days_until_expiry <= 30:
            status = 'Expiring Soon'
        elif days_until_expiry <= 90:
            status = 'Expiring Within 90 Days'
        else:
            status = 'Active'
        
        data = {
            'Subscription ID': lic.get('subscription_id', 'N/A'),
            'Order ID': lic.get('order_id', 'N/A'),
            'Type': lic.get('type', 'N/A'),
            'Quantity': lic.get('quantity', 0),
            'Remaining Quantity': lic.get('remaining_quantity', 0),
            'Start Date': start_date,
            'End Date': end_date,
            'Days Until Expiry': days_until_expiry,
            'Status': status,
            'Created Date': created_date,
            'License ID': lic.get('id', 'N/A')
        }
        formatted_data.append(data)
    
    # Sort by expiry date (soonest first)
    formatted_data.sort(key=lambda x: x['Days Until Expiry'])
    
    return formatted_data

def print_license_summary(license_response: dict):
    """Print summary of licenses"""
    summary = license_response.get('summary', {})
    entitled = license_response.get('entitled', {})
    fully_loaded = license_response.get('fully_loaded', {})
    
    print("\n" + "="*80)
    print("LICENSE SUMMARY")
    print("="*80)
    
    print("\n--- Currently Used (Summary) ---")
    for lic_type, count in sorted(summary.items()):
        print(f"{lic_type:15} : {count:6}")
    
    print("\n--- Entitled (Available) ---")
    for lic_type, count in sorted(entitled.items()):
        print(f"{lic_type:15} : {count:6}")
    
    print("\n--- Fully Loaded (Including Auto-Granted) ---")
    for lic_type, count in sorted(fully_loaded.items()):
        print(f"{lic_type:15} : {count:6}")
    
    # Check for insufficiencies
    print("\n--- Insufficiency Status ---")
    print(f"VNA Insufficient: {license_response.get('vna_insufficient', False)}")
    print(f"SVNA Insufficient: {license_response.get('svna_insufficient', False)}")
    print(f"WVNA Insufficient: {license_response.get('wvna_insufficient', False)}")
    
    print("="*80 + "\n")

def print_expiring_licenses(formatted_data: list):
    """Print licenses expiring soon"""
    expiring = [lic for lic in formatted_data if lic['Status'] in ['Expiring Soon', 'Expiring Within 90 Days', 'Expired']]
    
    if expiring:
        print("\n" + "!"*80)
        print("ATTENTION: LICENSES REQUIRING REVIEW")
        print("!"*80)
        for lic in expiring:
            print(f"\n{lic['Type']:15} | Qty: {lic['Quantity']:4} | Remaining: {lic['Remaining Quantity']:4}")
            print(f"  Subscription: {lic['Subscription ID']}")
            print(f"  End Date: {lic['End Date']} ({lic['Days Until Expiry']} days)")
            print(f"  Status: {lic['Status']}")
        print("!"*80 + "\n")
    else:
        print("\n✓ All licenses are active with sufficient time remaining.\n")

def main():
    try:
        # Get credentials and setup
        print("Fetching Mist credentials...")
        credentials = get_credentials(otp=False)
        org_id = get_org_id(credentials)
        
        config = APIConfig(
            baseurl=credentials["api_url"],
            headers=get_headers(credentials["api_token"]),
            org_id=org_id
        )
        
        print(f"Retrieving organization information...")
        orgname = get_org_name(config).replace(" ", "_")
        print(f"Organization: {orgname}")
        
        # Fetch license data
        print(f"\nFetching license data for organization: {org_id}")
        license_data = get_licenses(config)
        
        # Print summary
        print_license_summary(license_data)
        
        # Format license details
        formatted_licenses = format_license_data(license_data)
        
        # Print expiring licenses alert
        print_expiring_licenses(formatted_licenses)
        
        # Create CSV report
        filename = f'{orgname}_License_Report_{date.today()}.csv'
        file_path = config.config_dir / filename
        
        if not config.config_dir.exists():
            config.config_dir.mkdir(parents=True, exist_ok=True)
        
        create_csv(formatted_licenses, file_path)
        print(f'✓ Created detailed license report: {file_path}')
        print(f'  Total licenses exported: {len(formatted_licenses)}')
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        if config and config.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
