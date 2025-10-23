from mistrs import get_credentials, get_headers, get, put, print_table
from dataclasses import dataclass
import sys
import re
import json

@dataclass
class APIConfig:
    baseurl: str
    headers: dict
    org_id: str

def safe_get(url, headers):
    """Safely execute GET request with error handling"""
    resp = get(url, headers)
    if isinstance(resp, str):
        print(f"API Error: {resp}")
        sys.exit(1)
    return resp

def safe_put(data, url, headers):
    """Safely execute PUT request with error handling"""
    resp = put(data, url, headers)
    if isinstance(resp, str):
        print(f"API Error: {resp}")
        return None
    return resp

def validate_ip(ip_str):
    """Validate IP address format"""
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip_str):
        return False
    octets = ip_str.split('.')
    return all(0 <= int(octet) <= 255 for octet in octets)

def validate_netmask(netmask_str):
    """Validate netmask - accepts both dotted decimal (255.255.255.0) and CIDR (/24)"""
    # Check if it's CIDR notation
    if netmask_str.startswith('/'):
        try:
            cidr = int(netmask_str[1:])
            return 0 <= cidr <= 32
        except ValueError:
            return False
    elif netmask_str.isdigit():
        # Just a number like "24"
        cidr = int(netmask_str)
        return 0 <= cidr <= 32
    else:
        # Dotted decimal notation
        return validate_ip(netmask_str)

def get_validated_input(prompt, validator=None, required=True):
    """Get and validate user input"""
    while True:
        value = input(prompt).strip()
        if not value and not required:
            return None
        if not value and required:
            print("This field is required.")
            continue
        if validator and not validator(value):
            print("Invalid input format. Please try again.")
            continue
        return value

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

def create_site_array(config: APIConfig):
    """Creates Array of item names and IDs for sites."""
    url = f'{config.baseurl}orgs/{config.org_id}/sites'
    resp = safe_get(url, config.headers)
    
    return [
        {
            '#': idx,
            'id': site.get('id'),
            'name': site.get('name')
        }
        for idx, site in enumerate(resp, start=1)
    ]

def create_vlan_array(config: APIConfig, site_id: str):
    """Creates Array of VLANs from site derived settings."""
    url = f'{config.baseurl}sites/{site_id}/setting/derived?device_type=switch'
    resp = safe_get(url, config.headers)
    networks = resp.get('networks', {})
    vars_dict = resp.get('vars', {})
    
    Array = []
    for idx, (name, details) in enumerate(networks.items(), start=1):
        vlan_id = details.get('vlan_id', '')
        resolved = vlan_id
        # Resolve template variables like {{vlan_id}}
        if vlan_id.startswith('{{') and vlan_id.endswith('}}'):
            var_name = vlan_id[2:-2]
            resolved = vars_dict.get(var_name, vlan_id)
        
        Array.append({
            '#': idx,
            'name': name,
            'vlan_id': vlan_id,
            'resolved': resolved
        })
    return Array

def create_switch_array(config: APIConfig, site_id: str):
    """Creates Array of switches for the site."""
    url = f'{config.baseurl}orgs/{config.org_id}/devices/search?type=switch&site_id={site_id}'
    resp = safe_get(url, config.headers)
    # Search endpoints return {'results': [...], 'total': n, 'limit': n}
    results = resp.get('results', [])
    
    return [
        {
            '#': idx,
            'mac': switch.get('mac'),
            'name': switch.get('name') or switch.get('hostname') or 'Unnamed',
            'model': switch.get('model')
        }
        for idx, switch in enumerate(results, start=1)
    ]

def user_select(array, prompt):
    """Gets input from user, allows empty for skip"""
    if not array:
        print("No items available.")
        return None
    
    print(print_table(array))
    while True:
        choice_str = input(prompt).strip()
        if not choice_str:
            return None
        try:
            choice = int(choice_str)
            if 1 <= choice <= len(array):
                return array[choice - 1]
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(array)}.")
        except ValueError:
            print("Invalid input. Please enter a number or press Enter to skip.")

def main():
    try:
        # Get credentials and setup
        print("Initializing...")
        credentials = get_credentials()
        org_id = get_org_id(credentials)
        config = APIConfig(
            baseurl=credentials["api_url"],
            headers=get_headers(credentials["api_token"]),
            org_id=org_id
        )

        # Select site
        print("\nFetching sites...")
        sites = create_site_array(config)
        if not sites:
            print("No sites found in organization.")
            sys.exit(1)
        
        selected_site = user_select(sites, f"Select site (1-{len(sites)}): ")
        if not selected_site:
            print("No site selected. Exiting.")
            sys.exit(1)
        site_id = selected_site['id']
        print(f"Selected site: {selected_site['name']}")

        # Select switch
        print("\nFetching switches...")
        switches = create_switch_array(config, site_id)
        if not switches:
            print("No switches found at this site.")
            sys.exit(1)
        
        selected_switch = user_select(switches, f"Select switch (1-{len(switches)}): ")
        if not selected_switch:
            print("No switch selected. Exiting.")
            sys.exit(1)
        
        # Use MAC address as device identifier
        device_mac = selected_switch['mac']
        current_name = selected_switch['name']
        print(f"Selected switch: {current_name} ({device_mac})")

        # Get new name (optional)
        print(f"\nCurrent switch name: {current_name}")
        new_name = input("Enter new name for the switch (or press Enter to keep current name): ").strip()
        if new_name:
            switch_name = new_name
            print(f"Switch will be renamed to: {switch_name}")
        else:
            switch_name = current_name
            print(f"Keeping current name: {switch_name}")

        # Get role
        role = input("\nEnter role for the switch: ").strip()
        if not role:
            print("Role cannot be empty.")
            sys.exit(1)

        # Get IP details with validation
        print("\nEnter static IP configuration:")
        ip = get_validated_input("  IP address: ", validator=validate_ip)
        netmask = get_validated_input("  Netmask (e.g., 255.255.255.0 or /24 or 24): ", validator=validate_netmask)
        gateway = get_validated_input("  Default gateway: ", validator=validate_ip)
        dns = input("  DNS (comma separated, optional): ").strip()

        # Normalize netmask to string format (API accepts both formats)
        if netmask.isdigit():
            netmask = f"/{netmask}"  # Convert "24" to "/24"
        # If it's already /24 or 255.255.255.0, leave it as is

        dns_list = []
        if dns:
            dns_list = [d.strip() for d in dns.split(',')]
            # Validate each DNS entry
            for dns_ip in dns_list:
                if not validate_ip(dns_ip):
                    print(f"Invalid DNS IP address: {dns_ip}")
                    sys.exit(1)

        # Select VLAN (optional)
        print("\nFetching VLANs...")
        vlans = create_vlan_array(config, site_id)
        network_name = None
        if vlans:
            selected_vlan = user_select(vlans, f"Select VLAN (1-{len(vlans)}) or press Enter to skip: ")
            network_name = selected_vlan['name'] if selected_vlan else None
        else:
            print("No VLANs found at this site.")

        # Build data
        data = {
            "name": switch_name,
            "role": role,
            "ip_config": {
                "type": "static",
                "ip": ip,
                "netmask": netmask,
                "gateway": gateway,
                "dns": dns_list
            }
        }
        if network_name:
            data["ip_config"]["network"] = network_name

        # Confirm and send to API
        print("\n" + "="*50)
        print("Configuration Summary:")
        print(f"  Switch Name: {switch_name}")
        if new_name:
            print(f"    (changed from: {current_name})")
        print(f"  MAC Address: {device_mac}")
        print(f"  Site: {selected_site['name']}")
        print(f"  Role: {role}")
        print(f"  IP: {ip}")
        print(f"  Netmask: {netmask}")
        print(f"  Gateway: {gateway}")
        print(f"  DNS: {', '.join(dns_list) if dns_list else 'None'}")
        print(f"  Network: {network_name if network_name else 'None'}")
        print("="*50)
        
        confirm = input("\nProceed with update? (y/n): ").lower()
        if confirm != 'y':
            print("Operation cancelled.")
            sys.exit(0)

        print("\nUpdating switch configuration...")
        url = f'{config.baseurl}sites/{site_id}/devices/00000000-0000-0000-1000-{device_mac}'
        
        resp = safe_put(data, url, config.headers)
        if resp:
            print("\n✓ Successfully updated switch configuration.")
        else:
            print("\n✗ Failed to update switch configuration.")

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()