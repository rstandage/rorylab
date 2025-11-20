#!/usr/bin/env python3

'''
This script invites users to an existing Mist organization.

Usage:
    python invite_users.py --org_id <org_id> --csv <path_to_csv>
    python invite_users.py --org_id <org_id>  # Interactive mode
    python invite_users.py  # Full interactive mode

CSV Format:
    email,first_name,last_name,role,scope
    user@example.com,john,doe,admin,org
    user2@example.com,jane,smith,write,org
    
Note: role defaults to 'admin', scope defaults to 'org' if not provided
Valid roles: admin, write, read, helpdesk, installer
Valid scopes: org, site, sitegroup
'''

from mistrs import get_credentials, get_headers, post, read_csv, print_table
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
    role: str = "admin"  # admin, write, read, helpdesk, installer
    scope: str = "org"   # org, site, sitegroup
    
    def __post_init__(self):
        """Validate role and scope values"""
        valid_roles = ['admin', 'write', 'read', 'helpdesk', 'installer']
        valid_scopes = ['org', 'site', 'sitegroup']
        
        if self.role not in valid_roles:
            print(f"Warning: Invalid role '{self.role}', defaulting to 'admin'")
            self.role = 'admin'
        
        if self.scope not in valid_scopes:
            print(f"Warning: Invalid scope '{self.scope}', defaulting to 'org'")
            self.scope = 'org'

@dataclass
class APIConfig:
    """Configuration for API calls"""
    baseurl: str
    headers: Dict
    org_id: str

class APIError(Exception):
    """Raised when API call fails"""
    pass

def create_admin_invite(admin: AdminUser, config: APIConfig) -> bool:
    """
    Create an admin invite for the organization.
    
    Args:
        admin: Admin user information
        config: API configuration
        
    Returns:
        True if invite created successfully, False otherwise
    """
    try:
        url = f'{config.baseurl}orgs/{config.org_id}/invites'
        
        # Map role to view (for backward compatibility)
        # admin -> org_admin, others use the role name
        if admin.role == 'admin':
            view = 'org_admin'
            role_type = 'write'  # admin gets write privileges
        else:
            view = f'org_{admin.role}'
            role_type = admin.role
        
        payload = {
            "email": admin.email,
            "first_name": admin.first_name,
            "last_name": admin.last_name,
            "privileges": [
                {
                    "role": role_type,
                    "view": view,
                    "scope": admin.scope
                }
            ],
            "hours": 168  # 7 days
        }
        
        print(f"\nCreating invite for {admin.email}...")
        print(f"  Name: {admin.first_name} {admin.last_name}")
        print(f"  Role: {admin.role} (scope: {admin.scope})")
        
        result = post(payload, url, config.headers)
        
        # mistrs.post() returns (success, response_data) tuple
        if isinstance(result, tuple):
            success, response = result
            
            if not success:
                raise APIError(f"Failed to create invite - API returned failure status")
        else:
            # Fallback if not a tuple
            response = result
            if response is None:
                raise APIError(f"Failed to create invite - No response received")
        
        print(f"  ✓ Invite created successfully")
        print(f"    Valid for: 168 hours (7 days)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error creating invite: {str(e)}")
        return False

def load_users_from_csv(csv_path: str) -> List[AdminUser]:
    """
    Load users from CSV file.
    
    CSV format: email,first_name,last_name[,role][,scope]
    
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
    
    # Parse users
    users = []
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
            
            # Get optional fields
            role = row.get('role', '').strip() or 'admin'
            scope = row.get('scope', '').strip() or 'org'
            
            user = AdminUser(
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=role,
                scope=scope
            )
                
            users.append(user)
            
        except (KeyError, AttributeError) as e:
            print(f"Warning: Error parsing row {i}: {e}")
            continue
    
    if not users:
        raise ValueError("No valid users found in CSV")
    
    return users

def get_user_from_input() -> AdminUser:
    """
    Get user information from interactive input.
    
    Returns:
        AdminUser object
    """
    print("\n" + "="*60)
    print("USER INFORMATION")
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
        
        # Role selection
        print("\nAvailable roles:")
        print("  1. admin (full admin access)")
        print("  2. write (read/write access)")
        print("  3. read (read-only access)")
        print("  4. helpdesk (helpdesk access)")
        print("  5. installer (installer access)")
        
        role_choice = input("\nSelect role (1-5) [default: 1]: ").strip()
        role_map = {
            '1': 'admin', '2': 'write', '3': 'read',
            '4': 'helpdesk', '5': 'installer', '': 'admin'
        }
        role = role_map.get(role_choice, 'admin')
        
        # Scope selection
        print("\nAvailable scopes:")
        print("  1. org (organization level)")
        print("  2. site (site level)")
        print("  3. sitegroup (site group level)")
        
        scope_choice = input("\nSelect scope (1-3) [default: 1]: ").strip()
        scope_map = {'1': 'org', '2': 'site', '3': 'sitegroup', '': 'org'}
        scope = scope_map.get(scope_choice, 'org')
        
        # Confirm information
        print(f"\nUser Information:")
        print(f"  Email: {email}")
        print(f"  Name: {first_name} {last_name}")
        print(f"  Role: {role}")
        print(f"  Scope: {scope}")
        
        confirm = input("\nConfirm this information? (y/n): ").lower()
        if confirm == 'y':
            return AdminUser(
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=role,
                scope=scope
            )
        
        print("\nLet's try again...")

def get_org_id_from_input() -> str:
    """
    Get organization ID from user input.
    
    Returns:
        Organization ID
    """
    print("\n" + "="*60)
    print("ORGANIZATION ID")
    print("="*60)
    
    while True:
        org_id = input("\nEnter the Organization ID: ").strip()
        
        if not org_id:
            print("❌ Organization ID cannot be empty")
            continue
            
        # Confirm the org_id
        confirm = input(f"Confirm organization ID '{org_id}'? (y/n): ").lower()
        if confirm == 'y':
            return org_id
        print("Please re-enter the organization ID")

def add_more_users() -> bool:
    """
    Ask if user wants to add more users.
    
    Returns:
        True if user wants to add more users, False otherwise
    """
    while True:
        response = input("\nAdd another user? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'")

def print_summary(results: List[Dict[str, Any]]):
    """
    Print summary of processing results.
    
    Args:
        results: List of result dictionaries
    """
    print("\n" + "="*60)
    print("PROCESSING SUMMARY")
    print("="*60)
    
    total = len(results)
    successful = sum(1 for r in results if r['success'])
    
    print(f"\nTotal users processed: {total}")
    print(f"Invites created successfully: {successful}/{total}")
    
    # Detailed results
    print("\n" + "-"*60)
    print("DETAILED RESULTS")
    print("-"*60)
    
    for i, result in enumerate(results, 1):
        user = result['user']
        status = "✓" if result['success'] else "❌"
        
        print(f"\n{i}. {status} {user.first_name} {user.last_name}")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.role} (scope: {user.scope})")
        
        if not result['success']:
            print(f"   ❌ Failed to create invite")
    
    print("\n" + "="*60)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Invite users to a Mist organization',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --org_id abc123 --csv users.csv    Invite users from CSV
  %(prog)s --org_id abc123                     Interactive mode
  %(prog)s                                     Full interactive mode
        '''
    )
    
    parser.add_argument(
        '--org_id',
        type=str,
        help='Organization ID to invite users to'
    )
    
    parser.add_argument(
        '--csv',
        type=str,
        help='Path to CSV file with user information'
    )
    
    return parser.parse_args()

def main():
    """Main execution function"""
    try:
        print("\n" + "="*60)
        print("MIST USER INVITE SCRIPT")
        print("="*60)
        
        # Parse arguments
        args = parse_arguments()
        
        # Get API credentials
        baseurl, api_token, org_id = get_credentials()
        headers = get_headers(api_token)
        
        # Get org_id from args or input
        if args.org_id:
            target_org_id = args.org_id
            print(f"\nUsing organization ID from arguments: {target_org_id}")
        else:
            target_org_id = get_org_id_from_input()
        
        # Create API config
        config = APIConfig(
            baseurl=baseurl,
            headers=headers,
            org_id=target_org_id
        )
        
        # Get users
        users = []
        if args.csv:
            # Load from CSV
            print(f"\nLoading users from CSV: {args.csv}")
            users = load_users_from_csv(args.csv)
            print(f"✓ Loaded {len(users)} users from CSV")
        else:
            # Interactive mode
            print("\nEntering interactive mode...")
            while True:
                user = get_user_from_input()
                users.append(user)
                
                if not add_more_users():
                    break
        
        # Confirm before processing
        print("\n" + "="*60)
        print(f"Ready to invite {len(users)} user(s) to organization: {target_org_id}")
        print("="*60)
        
        confirm = input("\nProceed with creating invites? (y/n): ").lower()
        if confirm != 'y':
            print("\n❌ Operation cancelled by user")
            sys.exit(0)
        
        # Process each user
        results = []
        for user in users:
            success = create_admin_invite(user, config)
            results.append({
                'user': user,
                'success': success
            })
        
        # Print summary
        print_summary(results)
        
        # Exit with appropriate code
        if all(r['success'] for r in results):
            print("\n✓ All invites created successfully!")
            sys.exit(0)
        elif any(r['success'] for r in results):
            print("\n⚠ Some invites failed - see details above")
            sys.exit(1)
        else:
            print("\n❌ All invites failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠ Operation cancelled by user")
        sys.exit(130)
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
