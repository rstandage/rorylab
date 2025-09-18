#!/usr/bin/env python3

'''
This script will create an MSP using mistrs authentication and best practices
'''

from mistrs import get_credentials, get_headers, post, jprint
from typing import Dict, Any
import sys

def create_msp(name: str, baseurl: str, headers: Dict) -> bool:
    try:
        data = {"name": name}
        response = post(data, f'{baseurl}msps', headers)
        
        if response:
            print(f"\nSuccessfully created MSP: {name}")
            jprint(response)
            return True
        else:
            print(f"\nFailed to create MSP: {name}")
            return False
            
    except Exception as e:
        print(f"Error creating MSP: {str(e)}")
        return False

def main():
    try:
        # Get credentials using mistrs interactive auth
        credentials = get_credentials(otp=False)
        headers = get_headers(credentials["api_token"])
        baseurl = credentials["api_url"]
        
        # Get MSP name from user
        print()
        name = input("Name of New MSP: ").strip()
        
        if not name:
            print("MSP name cannot be empty")
            sys.exit(1)
        
        # Confirm the action
        confirm = input(f"\nConfirm creation of MSP '{name}'? (y/n): ").lower()
        if confirm != 'y':
            print("Operation cancelled")
            sys.exit(0)
        
        # Create the MSP
        success = create_msp(name, baseurl, headers)
        
        if not success:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()