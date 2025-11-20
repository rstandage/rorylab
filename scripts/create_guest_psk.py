#!/usr/bin/env python3

'''
This script will create guest pre-shared keys (PSKs) with the following features:
- Generates guest ID with 10 random numbers
- Creates 3-word random passphrase
- Sets default role as 'guest'
- SSID: Haven-WPA2-PPSK
- Default duration: 7 days
- Generates QR code for easy WiFi connection
'''

from mistrs import get_credentials, get_headers, post, jprint
from datetime import datetime, timedelta
from pathlib import Path
import random
import string
import sys
import argparse
from dataclasses import dataclass
import wifi_qrcode_generator.generator as qr_generator

@dataclass
class APIConfig:
    baseurl: str
    headers: dict
    org_id: str
    config_dir: Path = Path.home() / "created_files" / "guest_psks"

class APIError(Exception):
    pass

# Word list for passphrase generation (can be expanded)
WORD_LIST = [
    'welcome', 'hello', 'happy', 'sunny', 'bright', 'gentle', 'quick', 'smart',
    'forest', 'ocean', 'mountain', 'river', 'garden', 'meadow', 'valley', 'island',
    'apple', 'banana', 'cherry', 'orange', 'mango', 'grape', 'peach', 'melon',
    'tiger', 'eagle', 'dolphin', 'panda', 'falcon', 'wolf', 'bear', 'lion',
    'red', 'blue', 'green', 'yellow', 'purple', 'silver', 'golden', 'crystal',
    'summer', 'spring', 'winter', 'autumn', 'dawn', 'sunset', 'twilight', 'morning',
    'cloud', 'storm', 'breeze', 'lightning', 'thunder', 'rainbow', 'sunshine', 'moonlight',
    'piano', 'guitar', 'violin', 'flute', 'drum', 'harp', 'trumpet', 'saxophone',
    'book', 'pencil', 'paper', 'canvas', 'brush', 'paint', 'sketch', 'drawing',
    'coffee', 'tea', 'chocolate', 'honey', 'sugar', 'vanilla', 'cinnamon', 'pepper',
    'castle', 'bridge', 'tower', 'palace', 'temple', 'chapel', 'cottage', 'manor',
    'dragon', 'phoenix', 'unicorn', 'griffin', 'pegasus', 'sphinx', 'hydra', 'kraken',
    'sword', 'shield', 'arrow', 'spear', 'axe', 'hammer', 'dagger', 'lance',
    'ruby', 'emerald', 'sapphire', 'diamond', 'pearl', 'jade', 'opal', 'topaz',
    'breeze', 'whisper', 'echo', 'melody', 'harmony', 'rhythm', 'tempo', 'cadence',
    'forty', 'brocolli', 'eleven', 'twelve', 'twenty', 'thirty', 'sixty', 'ninety'
]

def generate_guest_id() -> str:
    """Generate guest ID with format guestid_[10 random numbers]"""
    random_numbers = ''.join(random.choices(string.digits, k=10))
    return f"guestid_{random_numbers}"

def generate_passphrase() -> str:
    """Generate a random 3-word passphrase"""
    words = random.sample(WORD_LIST, 3)
    return ''.join(words)

def get_org_id(credentials: dict) -> str:
    """Get organization ID from credentials or user input"""
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

def calculate_expire_time(days: int = 7) -> int:
    """Calculate Unix timestamp for expiration time"""
    expire_date = datetime.now() + timedelta(days=days)
    return int(expire_date.timestamp())

def generate_qr_code(ssid: str, passphrase: str, output_path: Path, guest_id: str) -> bool:
    """Generate QR code for WiFi connection"""
    try:
        qr_code = qr_generator.wifi_qrcode(
            ssid=ssid,
            hidden=False,
            authentication_type='WPA',
            password=passphrase
        )
        
        # Save QR code as image
        qr_filename = output_path / f"{guest_id}_qr.png"
        qr_code.make_image().save(str(qr_filename))
        print(f"\n✓ QR code saved to: {qr_filename}")
        return True
    except Exception as e:
        print(f"Warning: Could not generate QR code: {e}")
        return False

def create_guest_psk(config: APIConfig, vlan_id: int, ssid: str = "Haven-WPA2-PPSK",
                    role: str = "guest", duration_days: int = 7, 
                    guest_name: str = None, passphrase: str = None) -> dict:
    """
    Create a guest PSK in Mist
    
    Args:
        config: API configuration
        vlan_id: VLAN ID for the guest network
        ssid: SSID name (default: Haven-WPA2-PPSK)
        role: User role (default: guest)
        duration_days: Number of days until expiration (default: 7)
        guest_name: Optional custom guest name (otherwise auto-generated)
        passphrase: Optional custom passphrase (otherwise auto-generated)
    """
    try:
        # Generate guest ID and passphrase if not provided
        if guest_name is None:
            guest_name = generate_guest_id()
        else:
            # Ensure it follows the naming convention
            if not guest_name.startswith("guestid_"):
                guest_name = f"guestid_{guest_name}"
        
        if passphrase is None:
            passphrase = generate_passphrase()
        
        expire_time = calculate_expire_time(duration_days)
        
        # Prepare payload
        payload = {
            "vlan_id": vlan_id,
            "name": guest_name,
            "for_site": False,
            "ssid": ssid,
            "passphrase": passphrase,
            "role": role,
            "expire_time": expire_time
        }
        
        # Display PSK details
        print("\n" + "="*60)
        print("Guest PSK Details:")
        print("="*60)
        print(f"Guest ID:    {guest_name}")
        print(f"Passphrase:  {passphrase}")
        print(f"SSID:        {ssid}")
        print(f"VLAN ID:     {vlan_id}")
        print(f"Role:        {role}")
        print(f"Duration:    {duration_days} days")
        print(f"Expires:     {datetime.fromtimestamp(expire_time).strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Confirm before creating
        confirm = input("\nCreate this guest PSK? (y/n): ").lower()
        if confirm != 'y':
            print("Operation cancelled.")
            return None
        
        # Make API call
        url = f'{config.baseurl}orgs/{config.org_id}/psks'
        response = post(payload, url, config.headers)
        
        if response:
            print("\n✓ Successfully created guest PSK!")
            jprint(response)
            
            # Generate QR code
            config.config_dir.mkdir(parents=True, exist_ok=True)
            generate_qr_code(ssid, passphrase, config.config_dir, guest_name)
            
            # Save details to text file
            details_file = config.config_dir / f"{guest_name}_details.txt"
            with open(details_file, 'w') as f:
                f.write(f"Guest PSK Details\n")
                f.write(f"="*60 + "\n")
                f.write(f"Guest ID:    {guest_name}\n")
                f.write(f"Passphrase:  {passphrase}\n")
                f.write(f"SSID:        {ssid}\n")
                f.write(f"VLAN ID:     {vlan_id}\n")
                f.write(f"Role:        {role}\n")
                f.write(f"Created:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Expires:     {datetime.fromtimestamp(expire_time).strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"="*60 + "\n")
            print(f"✓ Details saved to: {details_file}")
            
            return response
        else:
            print("\n✗ Failed to create guest PSK")
            return None
            
    except Exception as e:
        print(f"Error creating guest PSK: {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(
        description='Create guest pre-shared keys (PSKs) in Mist',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Interactive mode (recommended)
  python create_guest_psk.py
  
  # With command line arguments
  python create_guest_psk.py --vlan 130 --duration 7
  
  # With custom name and passphrase
  python create_guest_psk.py --vlan 130 --name "1234567890" --passphrase "custompassword123"
  
  # Different SSID
  python create_guest_psk.py --vlan 130 --ssid "Guest-Network"
        '''
    )
    
    parser.add_argument('--vlan', type=int, help='VLAN ID for guest network')
    parser.add_argument('--ssid', type=str, default='Haven-WPA2-PPSK', 
                       help='SSID name (default: Haven-WPA2-PPSK)')
    parser.add_argument('--role', type=str, default='guest',
                       help='User role (default: guest)')
    parser.add_argument('--duration', type=int, default=7,
                       help='Duration in days until expiration (default: 7)')
    parser.add_argument('--name', type=str, help='Custom guest name (will add guestid_ prefix)')
    parser.add_argument('--passphrase', type=str, help='Custom passphrase (otherwise auto-generated)')
    parser.add_argument('--batch', type=int, help='Create multiple PSKs (specify count)')
    
    args = parser.parse_args()
    
    try:
        # Get credentials using mistrs
        print("Authenticating with Mist API...")
        credentials = get_credentials(otp=True)
        headers = get_headers(credentials["api_token"])
        baseurl = credentials["api_url"]
        org_id = get_org_id(credentials)
        
        # Create API config
        config = APIConfig(
            baseurl=baseurl,
            headers=headers,
            org_id=org_id
        )
        
        print(f"\n✓ Authenticated to organization: {org_id}")
        
        # Get VLAN ID if not provided
        vlan_id = args.vlan
        if vlan_id is None:
            while True:
                try:
                    vlan_input = input("\nEnter VLAN ID for guest network (e.g., 130): ").strip()
                    vlan_id = int(vlan_input)
                    if vlan_id > 0 and vlan_id < 4096:
                        break
                    print("VLAN ID must be between 1 and 4095")
                except ValueError:
                    print("Please enter a valid number")
        
        # Batch creation
        if args.batch and args.batch > 1:
            print(f"\n📦 Creating {args.batch} guest PSKs...")
            successful = 0
            failed = 0
            
            for i in range(args.batch):
                print(f"\n--- Creating PSK {i+1}/{args.batch} ---")
                result = create_guest_psk(
                    config=config,
                    vlan_id=vlan_id,
                    ssid=args.ssid,
                    role=args.role,
                    duration_days=args.duration
                )
                if result:
                    successful += 1
                else:
                    failed += 1
            
            print(f"\n{'='*60}")
            print(f"Batch Creation Summary:")
            print(f"✓ Successful: {successful}")
            print(f"✗ Failed:     {failed}")
            print(f"{'='*60}")
        else:
            # Single PSK creation
            result = create_guest_psk(
                config=config,
                vlan_id=vlan_id,
                ssid=args.ssid,
                role=args.role,
                duration_days=args.duration,
                guest_name=args.name,
                passphrase=args.passphrase
            )
            
            if result:
                sys.exit(0)
            else:
                sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
