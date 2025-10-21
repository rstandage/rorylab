# Switch Assignment Tool

This directory contains Python scripts for moving switches from inventory and assigning them to sites in the Mist platform.

## Scripts

### `move_switches_integrated.py` (Recommended)
The main production script that uses the mistrs library for authentication and API calls.

**Features:**
- Interactive CLI interface with OTP authentication
- Fetches unassigned switches from inventory
- Lists available sites
- Allows selection of multiple switches and target site
- Collects switch names (required) and optional roles
- Executes assignment via Mist Installer Provision API
- Comprehensive error handling

**Usage:**
```bash
python scripts/move_switches_integrated.py
```

### `move_switches.py`
Alternative implementation using direct API calls with requests library.

### `move_switches_mcp.py`
Demo version showing MCP integration patterns.

## Prerequisites

1. **mistrs library** - For Mist API authentication and utilities
2. **Valid Mist credentials** - API token with installer permissions
3. **Organization access** - Must have permission to manage devices and sites

## Process Flow

1. **Authentication**: Uses mistrs with OTP for secure authentication
2. **Get Inventory**: Fetches unassigned switches from organization inventory
3. **Get Sites**: Retrieves list of available sites
4. **User Selection**: Interactive selection of switches and target site
5. **Device Details**: Collects names (required) and optional roles for each switch
6. **Assignment**: Executes device-to-site assignment via Installer Provision API
7. **Confirmation**: Provides feedback on success/failure

## API Endpoints Used

The script uses the official Mist Installer Provision API endpoint:

- **Installer Provision**: `PUT /installer/orgs/{org_id}/devices/{device_mac}`

This endpoint is documented at: https://www.juniper.net/documentation/us/en/software/mist/api/http/api/installer/provision-installer-devices

## Required Data Fields

- **site_id**: Target site ID (selected by user)
- **name**: Device name (required, prompted for each switch)
- **role**: Device role (optional, prompted for each switch)

## Example Output

```
=== Mist Switch Assignment Tool ===

Working with organization: Demo Organization (9777c1a0-6ef6-11e6-8bbf-02e208b2d34f)
Fetching unassigned switches from inventory...

Found 3 unassigned switches:
Index  MAC             Serial          Model           Connected  Adopted
--------------------------------------------------------------------------------
1      d0dd4985cb3c    JW3619300157    EX2300-48P      No         Yes
2      a1b2c3d4e5f6    JW9876543210    EX4300-48P      Yes        Yes
3      f6e5d4c3b2a1    JW1122334455    EX2300-24P      No         Yes

Found 2 sites:
Index  Name                      ID        Country  Address
---------------------------------------------------------------------------------
1      Main Office               site-123  US       123 Main St, Anytown, USA
2      Branch Office             site-456  US       456 Branch Ave, Other City...

Enter switch indices to move (1-3, comma-separated, or 'all'): 1,2

Selected 2 switches:
  - d0dd4985cb3c (EX2300-48P) - Serial: JW3619300157
  - a1b2c3d4e5f6 (EX4300-48P) - Serial: JW9876543210

Confirm selection? (y/n): y

Enter site index (1-2): 1

Selected site: Main Office
Site ID: site-123
Address: 123 Main St, Anytown, USA

Confirm selection? (y/n): y

Please provide details for each switch:

Switch: d0dd4985cb3c (EX2300-48P) - Serial: JW3619300157
Enter name for switch d0dd4985cb3c: Access-Switch-01
Enter role for switch d0dd4985cb3c (optional, press Enter to skip): access

Switch: a1b2c3d4e5f6 (EX4300-48P) - Serial: JW9876543210
Enter name for switch a1b2c3d4e5f6: Core-Switch-01
Enter role for switch a1b2c3d4e5f6 (optional, press Enter to skip): core

=== FINAL CONFIRMATION ===
Organization: Demo Organization
Moving 2 switches to site: Main Office
Target Site ID: site-123

Switches to move:
  - d0dd4985cb3c -> 'Access-Switch-01' (Role: access)
    Model: EX2300-48P - Serial: JW3619300157
  - a1b2c3d4e5f6 -> 'Core-Switch-01' (Role: core)
    Model: EX4300-48P - Serial: JW9876543210

Proceed with assignment? Type 'yes' to confirm: yes

Assigning 2 switches to site 'Main Office'...
  Assigning device d0dd4985cb3c as 'Access-Switch-01'...
    Role: access
    ✓ Successfully assigned d0dd4985cb3c
  Assigning device a1b2c3d4e5f6 as 'Core-Switch-01'...
    Role: core
    ✓ Successfully assigned a1b2c3d4e5f6

Assignment Summary:
  Successful: 2
  Failed: 0

✓ Assignment process completed!
Check the Mist dashboard to verify the switches appear in site 'Main Office'
It may take a few minutes for the changes to be reflected in the dashboard.
```

## Error Handling

The script includes comprehensive error handling for:
- Network connectivity issues
- Invalid API credentials
- Missing organization/site permissions
- Device assignment failures
- User input validation
- Missing required fields (device names)

## Security Features

- **OTP Authentication**: Uses two-factor authentication for enhanced security
- **Credential Management**: Leverages mistrs secure credential handling
- **Permission Validation**: Checks API permissions before proceeding

## Notes

- Devices must be claimed in the organization inventory before assignment
- Only unassigned switches (site_id = null) will be shown
- Device names are required for proper identification in the dashboard
- Roles are optional but help with network organization
- Assignment changes may take a few minutes to appear in the Mist dashboard
- Uses the official Mist Installer Provision API for reliable device assignment

## Support

For issues related to:
- **Script functionality**: Check error messages and network connectivity
- **API permissions**: Verify installer permissions and API token validity
- **Device assignment**: Confirm devices are properly claimed in inventory
- **Authentication**: Ensure OTP/2FA is properly configured