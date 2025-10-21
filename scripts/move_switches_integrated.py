#!/usr/bin/env python3

"""
Move switches from inventory and assign them to a site.

This script integrates with the Mist MCP Server to:
1. Get unassigned switches from inventory  
2. Get site list
3. Allow user to select devices and site to move to
4. Execute move via the API

Usage: python move_switches_integrated.py
"""

from mistrs import get_credentials, get_headers, get_paginated, get, put, print_table
import sys
import json
from typing import Dict, List, Any, Optional

def get_org_name(baseurl: str, org_id: str, headers: dict) -> str:
    """Get organization name."""
    try:
        url = f'{baseurl}orgs/{org_id}/stats'
        resp = get(url, headers)
        return resp.get('name', 'Unknown Organization')
    except Exception as e:
        print(f"Warning: Could not get organization name: {e}")
        return 'Unknown Organization'

def get_unassigned_switches(baseurl: str, org_id: str, headers: dict) -> List[Dict]:
    """Get all unassigned switches from inventory."""
    print("Fetching unassigned switches from inventory...")
    
    try:
        # Get inventory with filters for unassigned switches
        url = f'{baseurl}orgs/{org_id}/inventory?type=switch&unassigned=true'
        switches = get_paginated(url, headers, limit=100, show_progress=True)
        
        # Additional filter to ensure site_id is None or empty
        unassigned_switches = [
            switch for switch in switches 
            if not switch.get('site_id') and switch.get('type') == 'switch'
        ]
        
        return unassigned_switches
    except Exception as e:
        print(f"Error fetching switches: {e}")
        return []

def get_sites(baseurl: str, org_id: str, headers: dict) -> List[Dict]:
    """Get all sites in the organization."""
    print("Fetching sites...")
    
    try:
        url = f'{baseurl}orgs/{org_id}/sites'
        sites = get(url, headers)
        return sites if isinstance(sites, list) else []
    except Exception as e:
        print(f"Error fetching sites: {e}")
        return []

def display_switches(switches: List[Dict]) -> None:
    """Display switches in a formatted table."""
    if not switches:
        print("No unassigned switches found.")
        return
    
    print(f"\nFound {len(switches)} unassigned switches:")
    
    # Format switches for display using mistrs print_table
    formatted_switches = []
    for i, switch in enumerate(switches):
        formatted_switch = {
            'Index': i + 1,
            'MAC': switch.get('mac', 'N/A'),
            'Serial': switch.get('serial', 'N/A'),
            'Model': switch.get('model', 'N/A'),
            'Connected': 'Yes' if switch.get('connected') else 'No',
            'Adopted': 'Yes' if switch.get('adopted') else 'No'
        }
        formatted_switches.append(formatted_switch)
    
    print(print_table(formatted_switches))

def display_sites(sites: List[Dict]) -> None:
    """Display sites in a formatted table."""
    if not sites:
        print("No sites found.")
        return
    
    print(f"\nFound {len(sites)} sites:")
    
    # Format sites for display using mistrs print_table
    formatted_sites = []
    for i, site in enumerate(sites):
        address = site.get('address', 'N/A')
        if len(address) > 40:
            address = address[:37] + "..."
            
        formatted_site = {
            'Index': i + 1,
            'Name': site.get('name', 'N/A'),
            'ID': site.get('id', 'N/A')[:8] + '...' if site.get('id') else 'N/A',
            'Country': site.get('country_code', 'N/A'),
            'Address': address
        }
        formatted_sites.append(formatted_site)
    
    print(print_table(formatted_sites))

def select_switches(switches: List[Dict]) -> List[Dict]:
    """Allow user to select switches to move."""
    if not switches:
        return []
    
    while True:
        try:
            selection = input(f"\nEnter switch indices to move (1-{len(switches)}, comma-separated, or 'all'): ").strip()
            
            if selection.lower() == 'all':
                return switches
            
            if not selection:
                print("Please enter a valid selection.")
                continue
            
            # Parse comma-separated indices
            indices = [int(x.strip()) for x in selection.split(',')]
            
            # Validate indices
            if all(1 <= i <= len(switches) for i in indices):
                selected_switches = [switches[i-1] for i in indices]
                
                # Show selected switches for confirmation
                print(f"\nSelected {len(selected_switches)} switches:")
                for switch in selected_switches:
                    print(f"  - {switch.get('mac')} ({switch.get('model')}) - Serial: {switch.get('serial')}")
                
                confirm = input("\nConfirm selection? (y/n): ").lower()
                if confirm == 'y':
                    return selected_switches
            else:
                print(f"Please enter indices between 1 and {len(switches)}")
                
        except ValueError:
            print("Please enter valid numbers separated by commas.")
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return []

def select_site(sites: List[Dict]) -> Optional[Dict]:
    """Allow user to select a target site."""
    if not sites:
        return None
    
    while True:
        try:
            selection = input(f"\nEnter site index (1-{len(sites)}): ").strip()
            
            if not selection:
                print("Please enter a valid selection.")
                continue
            
            index = int(selection)
            
            if 1 <= index <= len(sites):
                selected_site = sites[index-1]
                
                print(f"\nSelected site: {selected_site.get('name')}")
                print(f"Site ID: {selected_site.get('id')}")
                print(f"Address: {selected_site.get('address', 'N/A')}")
                
                confirm = input("\nConfirm selection? (y/n): ").lower()
                if confirm == 'y':
                    return selected_site
            else:
                print(f"Please enter an index between 1 and {len(sites)}")
                
        except ValueError:
            print("Please enter a valid number.")
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return None

def get_switch_details(switches: List[Dict]) -> Dict[str, Dict]:
    """Get names and optional roles for selected switches."""
    switch_details = {}
    
    print("\nPlease provide details for each switch:")
    
    for switch in switches:
        mac = switch.get('mac')
        model = switch.get('model', 'Unknown')
        serial = switch.get('serial', 'Unknown')
        
        print(f"\nSwitch: {mac} ({model}) - Serial: {serial}")
        
        # Get switch name (required)
        while True:
            name = input(f"Enter name for switch {mac}: ").strip()
            if name:
                break
            print("Name is required. Please enter a valid name.")
        
        # Get optional role
        role = input(f"Enter role for switch {mac} (optional, press Enter to skip): ").strip()
        role = role if role else None
        
        switch_details[mac] = {
            'name': name,
            'role': role
        }
    
    return switch_details

def assign_device_to_site(baseurl: str, org_id: str, headers: dict, device: Dict, site_id: str, device_details: Dict) -> bool:
    """
    Assign a single device to a site using the Mist API installer provision endpoint.
    
    Uses the PUT /installer/orgs/{org_id}/devices/{device_mac} endpoint
    as documented at: https://www.juniper.net/documentation/us/en/software/mist/api/http/api/installer/provision-installer-devices
    """
    device_mac = device.get('mac')
    device_name = device_details.get('name')
    device_role = device_details.get('role')
    
    try:
        # Build provision data according to API documentation
        provision_data = {
            'site_id': site_id,
            'name': device_name
        }
        
        # Add role if provided
        if device_role:
            provision_data['role'] = device_role
        
        # Use the installer provision endpoint with mistrs put function
        provision_url = f"{baseurl}installer/orgs/{org_id}/devices/{device_mac}"
        
        print(f"      Request URL: {provision_url}")
        print(f"      Request data: {json.dumps(provision_data, indent=2)}")
        
        response = put(provision_data, provision_url, headers)
        
        # Check if response indicates success
        # The mistrs put function returns [success_bool, response_data] for some endpoints
        if response is not None:
            print(f"      API response: {json.dumps(response, indent=2) if response else 'Empty response'}")
            
            # Handle different response formats
            if isinstance(response, list) and len(response) >= 2:
                # Format: [success_bool, response_data]
                success_flag = response[0]
                response_data = response[1] if len(response) > 1 else {}
                
                if success_flag:
                    return True
                else:
                    error_detail = response_data.get('detail', 'Unknown error') if isinstance(response_data, dict) else str(response_data)
                    print(f"      API Error: {error_detail}")
                    
                    # Provide specific guidance for common errors
                    if error_detail == "site not allowed":
                        print(f"      Troubleshooting 'site not allowed':")
                        print(f"        - Verify the API token has installer permissions for this site")
                        print(f"        - Check that site {site_id} belongs to organization {org_id}")
                        print(f"        - Ensure the site is not in a different organization or MSP")
                    
                    return False
            elif isinstance(response, dict):
                # Standard response object - check for error indicators
                if 'error' in response or 'detail' in response:
                    error_msg = response.get('detail') or response.get('error', 'Unknown error')
                    print(f"      API Error: {error_msg}")
                    return False
                else:
                    return True
            else:
                # Other response types - assume success if not None
                return True
        else:
            print(f"      API returned empty response")
            return False
            
    except Exception as e:
        error_msg = str(e)
        print(f"      Exception details: {error_msg}")
        
        # Try to extract more details from the error
        if "HTTP Error" in error_msg:
            print(f"      This is an HTTP error - check API permissions and data validity")
            print(f"      Common HTTP 400 causes:")
            print(f"        - Invalid site_id: {site_id}")
            print(f"        - Device already assigned or not in inventory")
            print(f"        - Invalid role value: {device_role}")
            print(f"        - Missing installer permissions")
        return False

def assign_devices_to_site(baseurl: str, org_id: str, headers: dict, devices: List[Dict], site: Dict, device_details: Dict[str, Dict]) -> bool:
    """Assign multiple devices to a site."""
    print(f"\nAssigning {len(devices)} switches to site '{site.get('name')}'...")
    print(f"Target site ID: {site.get('id')}")
    print(f"Organization ID: {org_id}")
    
    site_id = site.get('id')
    successful_assignments = 0
    failed_assignments = 0
    
    for device in devices:
        device_mac = device.get('mac')
        details = device_details.get(device_mac, {})
        
        print(f"\n  Assigning device {device_mac} as '{details.get('name')}'...")
        if details.get('role'):
            print(f"    Role: {details.get('role')}")
        
        # Debug device info
        print(f"    Device details: MAC={device_mac}, Model={device.get('model')}, Serial={device.get('serial')}")
        print(f"    Current site_id: {device.get('site_id')} (should be None/null)")
        
        success = assign_device_to_site(baseurl, org_id, headers, device, site_id, details)
        
        if success:
            print(f"    ✓ Successfully assigned {device_mac}")
            successful_assignments += 1
        else:
            print(f"    ✗ Failed to assign {device_mac}")
            failed_assignments += 1
    
    print(f"\nAssignment Summary:")
    print(f"  Successful: {successful_assignments}")
    print(f"  Failed: {failed_assignments}")
    
    return successful_assignments > 0

def main():
    """Main function to orchestrate the switch assignment process."""
    try:
        print("=== Mist Switch Assignment Tool ===\n")
        
        # Get credentials and setup
        credentials = get_credentials(otp=True)
        org_id = credentials["org_id"]
        baseurl = credentials["api_url"]
        headers = get_headers(credentials["api_token"])
        
        org_name = get_org_name(baseurl, org_id, headers)
        print(f"Working with organization: {org_name} ({org_id})")
        
        # Step 1: Get unassigned switches
        switches = get_unassigned_switches(baseurl, org_id, headers)
        if not switches:
            print("No unassigned switches found in inventory.")
            print("Make sure switches are claimed but not assigned to any site.")
            return
        
        display_switches(switches)
        
        # Step 2: Get sites
        sites = get_sites(baseurl, org_id, headers)
        if not sites:
            print("No sites found in organization.")
            return
        
        display_sites(sites)
        
        # Step 3: User selects switches
        selected_switches = select_switches(switches)
        if not selected_switches:
            print("No switches selected. Exiting.")
            return
        
        # Step 4: User selects target site
        selected_site = select_site(sites)
        if not selected_site:
            print("No site selected. Exiting.")
            return
        
        # Step 5: Get device details (names and optional roles)
        device_details = get_switch_details(selected_switches)
        
        # Final confirmation
        print(f"\n=== FINAL CONFIRMATION ===")
        print(f"Organization: {org_name}")
        print(f"Moving {len(selected_switches)} switches to site: {selected_site.get('name')}")
        print(f"Target Site ID: {selected_site.get('id')}")
        print(f"\nSwitches to move:")
        for switch in selected_switches:
            mac = switch.get('mac')
            details = device_details.get(mac, {})
            role_text = f" (Role: {details.get('role')})" if details.get('role') else ""
            print(f"  - {mac} -> '{details.get('name')}'{role_text}")
            print(f"    Model: {switch.get('model')} - Serial: {switch.get('serial')}")
        
        final_confirm = input(f"\nProceed with assignment? Type 'yes' to confirm: ").strip()
        if final_confirm.lower() != 'yes':
            print("Operation cancelled.")
            return
        
        # Step 6: Execute the assignment
        success = assign_devices_to_site(baseurl, org_id, headers, selected_switches, selected_site, device_details)
        
        if success:
            print(f"\n✓ Assignment process completed!")
            print(f"Check the Mist dashboard to verify the switches appear in site '{selected_site.get('name')}'")
            print(f"It may take a few minutes for the changes to be reflected in the dashboard.")
        else:
            print(f"\n✗ Assignment process failed or completed with errors.")
            print("Please check the error messages above and contact support if needed.")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        print("Please check your network connection and API credentials.")
        sys.exit(1)

if __name__ == "__main__":
    main()