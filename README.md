# Snyk Group Membership and Organization Membership Checker

A Python script to find Snyk group memberships (optionally filtered by role name) and check if those users have any organization memberships.

## Features

* 🔍 **Group Membership Discovery**: Find all group memberships or filter by role name
* 🏢 **Organization Membership Check**: Verify if users have organization memberships
* 📊 **Detailed Reporting**: Clear console output and optional JSON export
* 🌍 **Multi-Region Support**: Works with all Snyk regions
* 📝 **Comprehensive Logging**: Detailed logs of all operations
* ✅ **Error Handling**: Robust error handling and reporting
* 🔒 **Safe by Design**: Read-only operations, no data modification

## Prerequisites

* Python 3.6 or higher
* Snyk API token with group and organization read permissions
* Snyk group ID (can be set via `GROUP_ID` environment variable)

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Quick Start

### Basic Usage

```bash
python find_users_without_org_memberships.py \
  --token YOUR_TOKEN \
  --group-id GROUP_ID
```

### Using Environment Variable for Group ID

```bash
export GROUP_ID="your-group-id"
python find_users_without_org_memberships.py --token YOUR_TOKEN
```

### Filter by Role Name

```bash
python find_users_without_org_memberships.py \
  --token YOUR_TOKEN \
  --group-id GROUP_ID \
  --role-name "group-admin"
```

## Configuration

### Get Required Information

* **Snyk Token**: Generate from Snyk Account Settings → API Token
* **Group ID**: Found in Snyk UI or via API (or set `GROUP_ID` environment variable)
* **Region**: Your Snyk region (default: SNYK-US-01)

## Usage

### Command Line Arguments

| Argument      | Required | Description                             | Default    |
| ------------- | -------- | --------------------------------------- | ---------- |
| `--token`     | Yes      | Snyk API token                          | -          |
| `--group-id`  | Yes*      | Snyk group ID                           | `GROUP_ID` env var |
| `--role-name` | No       | Filter group memberships by role name   | None       |
| `--region`    | No       | Snyk region                             | SNYK-US-01 |
| `--version`   | No       | API version                             | 2025-11-05 |
| `--output`    | No       | Output file path for JSON results       | None       |

\* `--group-id` is required if `GROUP_ID` environment variable is not set.

### Supported Regions

* `SNYK-US-01` (default) - US East
* `SNYK-US-02` - US West
* `SNYK-EU-01` - Europe
* `SNYK-AU-01` - Australia

## Output

### Console Output

The script provides a formatted summary showing:
* Total group memberships found
* Users with organization memberships
* Users without organization memberships
* Detailed information for each user including:
  * Email address
  * Name
  * User ID
  * Role
  * Organization membership count and names

### Log Files

* Stored in `logs/` directory
* Timestamped filenames (e.g., `membership_check_20241201_143022.log`)
* Detailed information about all API operations
* Error details and troubleshooting information

### JSON Output (Optional)

If `--output` is specified, results are saved as JSON with the following structure:

```json
{
  "group_memberships": [...],
  "users_without_org_memberships": [...],
  "users_with_org_memberships": [...],
  "errors": [...]
}
```

## Exit Codes

* `0` - Success (all users have org memberships)
* `1` - Users without org memberships found or error occurred
* `130` - Interrupted by user (Ctrl+C)

## Examples

### Example 1: Check All Memberships

```bash
python find_users_without_org_memberships.py \
  --token "abc123-def456-ghi789" \
  --group-id "group-12345"
```

### Example 2: Check Specific Role

```bash
python find_users_without_org_memberships.py \
  --token "abc123-def456-ghi789" \
  --group-id "group-12345" \
  --role-name "group-admin"
```

### Example 3: EU Region with JSON Output

```bash
python find_users_without_org_memberships.py \
  --token "abc123-def456-ghi789" \
  --group-id "group-67890" \
  --region "SNYK-EU-01" \
  --output "eu_results.json"
```

### Example 4: Using Environment Variables

```bash
export GROUP_ID="2c258cd4-000b-4230-b55f-e2fd014fde05"
export PERSONAL_SNYK_TOKEN="your-token-here"
python find_users_without_org_memberships.py --token "$PERSONAL_SNYK_TOKEN"
```


## Security Considerations

* **Token Security**: Never commit API tokens to version control
* **Permissions**: Use tokens with minimal necessary permissions
* **Audit Trail**: All operations are logged for audit purposes
* **Read-Only**: This script only reads data and does not modify anything

## File Structure

```
find_users_without_org_memberships.py  # Main script
README.md                               # This documentation
requirements.txt                        # Python dependencies
LICENSE                                 # Apache 2.0 License
CONTRIBUTING.md                         # Contribution guidelines
SECURITY.md                             # Security policy
.github/workflows/ci.yml                # CI/CD workflow
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

This repository is closed to public contributions. For more information, please see [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

For security-related issues, please see [SECURITY.md](SECURITY.md) for reporting procedures.

## Disclaimer

The authors are not responsible for any unintended consequences from using this script. Always test thoroughly and ensure proper permissions before running in production environments.
