#!/usr/bin/env python3

'''
This script clones Mist organizations for multiple users and creates admin invites.

Usage:
    python clone_org.py --csv <path_to_csv>
    python clone_org.py  # Interactive mode

CSV Format:
    email,first_name,last_name[,org_name]
    pparker606@yahoo.com,peter,parker
    user@example.com,john,doe,CustomOrgName
    
Note: org_name column is optional. If not provided, defaults to {first_name}_{last_name}
'''

from mistrs import get_credentials, get_headers, get, post, jprint, read_csv, print_table
from typing import Dict, Any, List, Optional
import sys
import argparse
from dataclasses import dataclass
from pathlib import Path

@dataclass
class AdminUser:
    """Data class for admin user information"""
    email: str
    first_name: str
    last_name: str
    custom_org_name: Optional[str] = None
    
    @property
    def org_name(self) -> str:
        """Get organization name - custom if provided, otherwise generated from user info"""
        if self.custom_org_name:
            return self.custom_org_name
        return f"{self.first_name}_{self.last_name}"

@dataclass
class APIConfig:
    """Configuration for API calls"""
    baseurl: str
    headers: Dict
    source_org_id: str

class TokenValidationError(Exception):
    """Raised when token is not a user-level token"""
    pass

class APIError(Exception):
    """Raised when API call fails"""
    pass

def validate_user_token(baseurl: str, headers: Dict) -> Dict[str, Any]:
    """
    Validate that the token is a user-level token by checking /self endpoint.
    
    Args:
        baseurl: Base API URL
        headers: Request headers with auth token
        
    Returns:
        User information from /self endpoint
        
    Raises:
        TokenValidationError: If token is not user-level
        APIError: If API call fails
    """
    try:
        response = get(f'{baseurl}self', headers)
        
        if not response:
            raise APIError("Failed to retrieve user information from /self endpoint")
        
        # Check if this is a user token (should have email)
        if not response.get('email'):
            raise TokenValidationError(
                "This appears to be an organization token, not a user token. "
                "Please use a user-level API token."
            )
        
        print(f"\n✓ Token validated for user: {response.get('email')}")
        print(f"  Name: {response.get('first_name', '')} {response.get('last_name', '')}")
        
        return response
        
    except Exception as e:
        if isinstance(e, (TokenValidationError, APIError)):
            raise
        raise APIError(f"Error validating token: {str(e)}")

def get_source_org_id() -> str:
    """
    Get the source organization ID from user input.
    
    Returns:
        Organization ID to clone
    """
    print("\n" + "="*60)
    print("SOURCE ORGANIZATION")
    print("="*60)
    
    while True:
        org_id = input("\nEnter the Organization ID to clone: ").strip()
        
        if not org_id:
            print("❌ Organization ID cannot be empty")
            continue
            
        # Confirm the org_id
        confirm = input(f"Confirm organization ID '{org_id}'? (y/n): ").lower()
        if confirm == 'y':
            return org_id
        print("Please re-enter the organization ID")

def clone_organization(org_name: str, config: APIConfig) -> Optional[Dict[str, Any]]:
    """
    Clone an organization with the specified name.
    
    Args:
        org_name: Name for the new organization
        config: API configuration
        
    Returns:
        Response containing new org details including org_id, or None on failure
    """
    try:
        url = f'{config.baseurl}orgs/{config.source_org_id}/clone'
        payload = {"name": org_name}
        
        print(f"\n  Cloning organization as '{org_name}'...")
        result = post(payload, url, config.headers)
        
        # mistrs.post() returns (success, response_data) tuple
        if isinstance(result, tuple):
            success, response = result
            
            if not success or not response:
                raise APIError(f"Failed to clone organization '{org_name}' - API returned failure")
        else:
            # Fallback if not a tuple (shouldn't happen with mistrs.post)
            response = result
            if not response:
                raise APIError(f"Failed to clone organization '{org_name}' - No response received")
        
        new_org_id = response.get('id')
        if not new_org_id:
            raise APIError(f"No organization ID in response for '{org_name}'")
        
        print(f"  ✓ Organization cloned successfully")
        print(f"    New Org ID: {new_org_id}")
        
        return response
        
    except Exception as e:
        print(f"  ❌ Error cloning organization: {str(e)}")
        return None

def create_admin_invite(admin: AdminUser, org_id: str, config: APIConfig) -> bool:
    """
    Create an admin invite for the new organization.
    
    Args:
        admin: Admin user information
        org_id: Organization ID for the invite
        config: API configuration
        
    Returns:
        True if invite created successfully, False otherwise
    """
    try:
        url = f'{config.baseurl}orgs/{org_id}/invites'
        payload = {
            "email": admin.email,
            "first_name": admin.first_name,
            "last_name": admin.last_name,
            "privileges": [
                {
                    "role": "write",
                    "view": "org_admin",
                    "scope": "org"
                }
            ],
            "hours": 168  # 7 days
        }
        
        print(f"  Creating admin invite for {admin.email}...")
        result = post(payload, url, config.headers)
        
        # mistrs.post() returns (success, response_data) tuple
        if isinstance(result, tuple):
            success, response = result
            
            if not success:
                raise APIError(f"Failed to create invite for {admin.email} - API returned failure status")
            
            # Note: Invite endpoint may return empty dict on success, which is valid
        else:
            # Fallback if not a tuple (shouldn't happen with mistrs.post)
            response = result
            if response is None:
                raise APIError(f"Failed to create invite for {admin.email} - No response received")
        
        print(f"  ✓ Admin invite created successfully")
        print(f"    Valid for: 168 hours (7 days)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error creating admin invite: {str(e)}")
        return False

def process_admin(admin: AdminUser, config: APIConfig) -> Dict[str, Any]:
    """
    Process a single admin: clone org and create invite.
    
    Args:
        admin: Admin user information
        config: API configuration
        
    Returns:
        Dictionary with processing results
    """
    result = {
        'admin': admin,
        'org_name': admin.org_name,
        'org_id': None,
        'clone_success': False,
        'invite_success': False
    }
    
    print(f"\n{'='*60}")
    print(f"Processing: {admin.first_name} {admin.last_name} ({admin.email})")
    print(f"{'='*60}")
    
    # Clone organization
    clone_response = clone_organization(admin.org_name, config)
    if not clone_response:
        return result
    
    result['org_id'] = clone_response.get('id')
    result['clone_success'] = True
    
    # Create admin invite
    invite_success = create_admin_invite(admin, result['org_id'], config)
    result['invite_success'] = invite_success
    
    return result

def load_admins_from_csv(csv_path: str) -> List[AdminUser]:
    """
    Load admin users from CSV file.
    
    CSV format: email,first_name,last_name[,org_name]
    
    The org_name column is optional. If provided and non-empty, it will be used
    as the organization name. Otherwise, the name defaults to {first_name}_{last_name}.
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        List of AdminUser objects
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV format is invalid
    """
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    # Read CSV using mistrs (returns list of dicts)
    csv_data = read_csv(str(csv_file))
    
    if not csv_data:
        raise ValueError("CSV file is empty")
    
    # Validate required fields exist in first row
    if not isinstance(csv_data[0], dict):
        raise ValueError("Invalid CSV format")
    
    required_headers = ['email', 'first_name', 'last_name']
    
    # Case-insensitive field check
    first_row_keys = {k.lower().strip() for k in csv_data[0].keys()}
    missing_headers = [h for h in required_headers if h not in first_row_keys]
    
    if missing_headers:
        raise ValueError(f"CSV missing required columns: {', '.join(missing_headers)}")
    
    # Parse admin users
    admins = []
    for i, row in enumerate(csv_data, start=2):  # Start at 2 for user-friendly row numbering
        if not row:
            print(f"Warning: Skipping empty row {i}")
            continue
        
        try:
            # Get required fields
            email = row.get('email', '').strip()
            first_name = row.get('first_name', '').strip()
            last_name = row.get('last_name', '').strip()
            
            # Validate required fields
            if not email or '@' not in email:
                print(f"Warning: Invalid email on row {i}, skipping")
                continue
            
            if not first_name or not last_name:
                print(f"Warning: Missing name on row {i}, skipping")
                continue
            
            # Get optional org_name field
            custom_org_name = row.get('org_name', '').strip() if row.get('org_name') else None
            # Only use custom_org_name if it's not None and not empty string
            custom_org_name = custom_org_name if custom_org_name else None
            
            admin = AdminUser(
                email=email,
                first_name=first_name,
                last_name=last_name,
                custom_org_name=custom_org_name
            )
                
            admins.append(admin)
            
        except (KeyError, AttributeError) as e:
            print(f"Warning: Error parsing row {i}: {e}")
            continue
    
    if not admins:
        raise ValueError("No valid admin users found in CSV")
    
    return admins

def get_admin_from_user_input() -> AdminUser:
    """
    Get admin user information from interactive input.
    
    Returns:
        AdminUser object
    """
    print("\n" + "="*60)
    print("ADMIN USER INFORMATION")
    print("="*60)
    
    while True:
        email = input("\nEmail address: ").strip()
        if not email or '@' not in email:
            print("❌ Please enter a valid email address")
            continue
        
        first_name = input("First name: ").strip()
        if not first_name:
            print("❌ First name cannot be empty")
            continue
        
        last_name = input("Last name: ").strip()
        if not last_name:
            print("❌ Last name cannot be empty")
            continue
        
        # Ask for optional custom org name
        default_org_name = f"{first_name}_{last_name}"
        print(f"\nDefault organization name: {default_org_name}")
        custom_org_input = input("Custom organization name (press Enter to use default): ").strip()
        custom_org_name = custom_org_input if custom_org_input else None
        
        # Determine final org name for display
        final_org_name = custom_org_name if custom_org_name else default_org_name
        
        # Confirm information
        print(f"\nAdmin Information:")
        print(f"  Email: {email}")
        print(f"  Name: {first_name} {last_name}")
        print(f"  Organization Name: {final_org_name}")
        
        confirm = input("\nConfirm this information? (y/n): ").lower()
        if confirm == 'y':
            return AdminUser(
                email=email, 
                first_name=first_name, 
                last_name=last_name,
                custom_org_name=custom_org_name
            )
        
        print("\nLet's try again...")

def print_summary(results: List[Dict[str, Any]]):
    """
    Print summary of processing results.
    
    Args:
        results: List of result dictionaries from process_admin
    """
    print("\n" + "="*60)
    print("PROCESSING SUMMARY")
    print("="*60)
    
    total = len(results)
    successful_clones = sum(1 for r in results if r['clone_success'])
    successful_invites = sum(1 for r in results if r['invite_success'])
    fully_successful = sum(1 for r in results if r['clone_success'] and r['invite_success'])
    
    print(f"\nTotal admins processed: {total}")
    print(f"Organizations cloned: {successful_clones}/{total}")
    print(f"Invites created: {successful_invites}/{total}")
    print(f"Fully successful: {fully_successful}/{total}")
    
    # Detailed results
    print("\n" + "-"*60)
    print("DETAILED RESULTS")
    print("-"*60)
    
    for i, result in enumerate(results, 1):
        admin = result['admin']
        status = "✓" if result['clone_success'] and result['invite_success'] else "⚠" if result['clone_success'] else "❌"
        
        print(f"\n{i}. {status} {admin.first_name} {admin.last_name}")
        print(f"   Email: {admin.email}")
        print(f"   Org Name: {result['org_name']}")
        
        if result['org_id']:
            print(f"   Org ID: {result['org_id']}")
        
        if result['clone_success'] and not result['invite_success']:
            print(f"   ⚠ Warning: Organization cloned but invite failed")
        elif not result['clone_success']:
            print(f"   ❌ Failed to clone organization")
    
    print("\n" + "="*60)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Clone Mist organizations and create admin invites',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --csv admins.csv          Clone orgs for users in CSV
  %(prog)s                            Interactive mode for single user
        '''
    )
    
    parser.add_argument(
        '--csv',
        type=str,
        help='Path to CSV file with admin information'
    )
    
    return parser.parse_args()

def main():
    try:
        # Parse arguments
        args = parse_arguments()
        
        print("\n" + "="*60)
        print("MIST ORGANIZATION CLONING SCRIPT")
        print("="*60)
        
        # Step 1: Get credentials and authenticate
        print("\n[1/5] Authenticating...")
        credentials = get_credentials(otp=False)
        headers = get_headers(credentials["api_token"])
        baseurl = credentials["api_url"]
        
        # Step 2: Validate token is user-level
        print("\n[2/5] Validating token...")
        try:
            validate_user_token(baseurl, headers)
        except TokenValidationError as e:
            print(f"\n❌ {str(e)}")
            sys.exit(1)
        
        # Step 3: Get source organization ID
        print("\n[3/5] Getting source organization...")
        source_org_id = get_source_org_id()
        
        # Create API config
        config = APIConfig(
            baseurl=baseurl,
            headers=headers,
            source_org_id=source_org_id
        )
        
        # Step 4: Get admin users (from CSV or input)
        print("\n[4/5] Loading admin users...")
        if args.csv:
            print(f"\nLoading users from CSV: {args.csv}")
            try:
                admins = load_admins_from_csv(args.csv)
                print(f"✓ Loaded {len(admins)} admin user(s)")
            except (FileNotFoundError, ValueError) as e:
                print(f"❌ Error loading CSV: {str(e)}")
                sys.exit(1)
        else:
            print("\nNo CSV file provided, using interactive mode")
            admins = [get_admin_from_user_input()]
        
        # Display organizations to be created
        print(f"\n{'='*60}")
        print(f"Organizations to be Created")
        print(f"{'='*60}")
        
        org_table = []
        for admin in admins:
            org_table.append({
                'Organization Name': admin.org_name,
                'Admin Email': admin.email,
                'Admin Name': f"{admin.first_name} {admin.last_name}"
            })
        
        print(print_table(org_table))
        
        # Confirm before proceeding
        print(f"\n{'='*60}")
        print(f"Ready to clone {len(admins)} organization(s) from source org")
        print(f"Source Org ID: {source_org_id}")
        print(f"{'='*60}")
        confirm = input("\nProceed with cloning? (y/n): ").lower()
        if confirm != 'y':
            print("\n❌ Operation cancelled")
            sys.exit(0)
        
        # Step 5: Process each admin
        print("\n[5/5] Processing organizations...")
        results = []
        for admin in admins:
            result = process_admin(admin, config)
            results.append(result)
        
        # Print summary
        print_summary(results)
        
        # Exit with appropriate code
        fully_successful = sum(1 for r in results if r['clone_success'] and r['invite_success'])
        if fully_successful == len(results):
            print("\n✓ All organizations cloned and invites created successfully!")
            sys.exit(0)
        elif fully_successful > 0:
            print("\n⚠ Some operations completed with warnings")
            sys.exit(0)
        else:
            print("\n❌ All operations failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
