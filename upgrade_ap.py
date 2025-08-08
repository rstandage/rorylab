from http.client import responses

from mistrs import get_credentials, get_headers, get, post, clean_mac, print_table, jprint
from typing import Dict, Any, Optional
import sys

def get_ap_data(mac: str, baseurl: str, orgid: str, headers: Dict) -> Optional[Dict]:
    try:
        mac = clean_mac(mac)
        data = get(f'{baseurl}orgs/{orgid}/inventory?mac={mac}', headers)
        if not data:
            print("No AP found with the given MAC address")
            return None
        return data
    except Exception as e:
        print(f"Error fetching AP data: {str(e)}")
        return None

def upgrade_ap(siteid: str, deviceid: str, version: str, headers: Dict,
               baseurl: str, reboot: bool = False) -> bool:
    try:
        data = {
            'version': version,
            'reboot': reboot
        }
        postresp = post(data, f'{baseurl}sites/{siteid}/devices/{deviceid}/upgrade', headers)
        jprint(postresp)
        return True
    except Exception as e:
        print(f"Error upgrading AP: {str(e)}")
        return False

def main():
    try:
        # Get credentials and setup
        credentials = get_credentials(otp=True)
        headers = get_headers(credentials["api_token"])
        baseurl = credentials["api_url"]
        orgid = credentials["org_id"]

        # Get MAC address
        mac = input("Please enter MAC address: ").strip()
        ap_data = get_ap_data(mac, baseurl, orgid, headers)
        if not ap_data:
            sys.exit(1)

        # Print AP info
        ap_info = {
            'Name': ap_data[0].get('name'),
            'MAC': ap_data[0].get('mac'),
            'Model': ap_data[0].get('model'),
            'Status': 'Connected' if ap_data[0].get('connected') else 'Disconnected'
        }
        print("\nAP Details:")
        print(print_table([ap_info]))

        # Confirm upgrade
        check = input('\nPlease confirm AP Name to proceed: ').strip()
        if check.lower() != ap_data[0].get('name', '').lower():
            print('AP name does not match, aborting.')
            sys.exit(1)

        # Get upgrade parameters
        version = input('Please enter target version: ').strip()
        if not version:
            print("Version cannot be empty")
            sys.exit(1)

        reboot = input('Would you like to reboot (Y/N): ').strip().upper() == 'Y'

        # Perform upgrade
        success = upgrade_ap(
            ap_data[0].get('site_id'),
            ap_data[0].get('id'),
            version,
            headers,
            baseurl,
            reboot
        )

        if success:
            print(f"\nSuccessfully initiated upgrade to version {version}")
            if reboot:
                print("AP will reboot after upgrade")
        else:
            print("\nFailed to initiate upgrade")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()