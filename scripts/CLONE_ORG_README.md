# Clone Organization Script

## Overview

The `clone_org.py` script automates the process of cloning Mist organizations and creating admin invites for multiple users. It follows the same structure and best practices as other scripts in this directory.

## Features

- ✅ Clones Mist organizations from a source organization
- ✅ Creates admin invites with org_admin privileges
- ✅ Supports batch processing via CSV file
- ✅ Interactive mode for single user
- ✅ Token validation (ensures user-level token, not org token)
- ✅ Comprehensive error handling
- ✅ Detailed summary report

## Usage

### With CSV File (Batch Mode)

```bash
python scripts/clone_org.py --csv data/sample_admins.csv
```

### Interactive Mode (Single User)

```bash
python scripts/clone_org.py
```

## CSV Format

The CSV file must contain the following headers (case-insensitive):

```csv
email,first_name,last_name
rory.standage@gmail.com,rory,standage
pparker584@yahoo.com,peter,parker
```

- **email**: Admin email address (must contain @)
- **first_name**: Admin's first name
- **last_name**: Admin's last name

The organization name will be automatically generated as `{first_name}_{last_name}`.

## Process Flow

1. **Authentication**: Uses `mistrs.get_credentials()` to authenticate
2. **Token Validation**: Validates token is user-level via `/self` endpoint
3. **Source Org Selection**: Prompts for source organization ID to clone
4. **User Loading**: Loads users from CSV or interactive input
5. **Processing**: For each user:
   - Clones the source organization with name `{first_name}_{last_name}`
   - Creates admin invite with org_admin privileges (valid for 7 days)
6. **Summary**: Displays detailed results for all operations

## API Endpoints Used

- `GET /api/v1/self` - Validate user token
- `POST /api/v1/orgs/{org_id}/clone` - Clone organization
- `POST /api/v1/orgs/{org_id}/invites` - Create admin invite

## Admin Invite Details

Each invite is created with:
- **Role**: `write`
- **View**: `org_admin`
- **Scope**: `org`
- **Validity**: 168 hours (7 days)

## Error Handling

The script includes comprehensive error handling for:
- Invalid or missing CSV files
- Invalid CSV format or missing required headers
- Token validation failures (org tokens not allowed)
- API call failures during cloning
- API call failures during invite creation
- Network errors and timeouts

## Exit Codes

- `0`: Success (all operations completed)
- `1`: Failure (errors occurred)

## Example Output

```
============================================================
MIST ORGANIZATION CLONING SCRIPT
============================================================

[1/5] Authenticating...
✓ Token validated for user: rory.standage@gmail.com
  Name: Rory Standage

[2/5] Validating token...
✓ Token validated

[3/5] Getting source organization...
Enter the Organization ID to clone: abc123-def456-...

[4/5] Loading admin users...
Loading users from CSV: data/sample_admins.csv
✓ Loaded 2 admin user(s)

[5/5] Processing organizations...

============================================================
Processing: rory standage (rory.standage@gmail.com)
============================================================

  Cloning organization as 'rory_standage'...
  ✓ Organization cloned successfully
    New Org ID: xyz789-abc123-...
  Creating admin invite for rory.standage@gmail.com...
  ✓ Admin invite created successfully
    Valid for: 168 hours (7 days)

============================================================
PROCESSING SUMMARY
============================================================

Total admins processed: 2
Organizations cloned: 2/2
Invites created: 2/2
Fully successful: 2/2

✓ All organizations cloned and invites created successfully!
```

## Requirements

- Python 3.6+
- `mistrs` library
- Valid Mist user-level API token (not org token)

## Notes

- The script requires a **user-level API token**, not an organization token
- Organization names are automatically generated from first and last names
- Admin invites are valid for 7 days (168 hours)
- The source organization is not modified; only clones are created
- Each cloned organization is independent

## Troubleshooting

### "This appears to be an organization token"

Make sure you're using a user-level API token, not an organization-scoped token. You can verify this in the Mist dashboard under your profile settings.

### CSV Parsing Errors

Ensure your CSV file:
- Has headers: `email`, `first_name`, `last_name`
- Uses proper CSV format (comma-separated)
- Has valid email addresses (containing @)
- Has no empty required fields

### API Call Failures

Check that:
- Your API token has sufficient permissions
- The source organization ID exists and you have access to it
- You have permission to create organizations
- Network connectivity is stable
