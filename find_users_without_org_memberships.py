#!/usr/bin/env python3
"""
Snyk Group Membership and Organization Membership Checker

This script finds Snyk group memberships filtered by role name and checks
if those users have any organization memberships.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class SnykAPIClient:
    """Client for interacting with the Snyk API."""
    
    def __init__(self, token: str, region: str = "SNYK-US-01", version: str = "2025-11-05"):
        """
        Initialize the Snyk API client.
        
        Args:
            token: Snyk API token
            region: Snyk region (SNYK-US-01, SNYK-US-02, SNYK-EU-01, SNYK-AU-01)
            version: API version
        """
        self.token = token
        self.version = version
        self.region = region
        
        # Determine API base URL based on region
        region_map = {
            "SNYK-US-01": "https://api.snyk.io",
            "SNYK-US-02": "https://api.us.snyk.io",
            "SNYK-EU-01": "https://api.eu.snyk.io",
            "SNYK-AU-01": "https://api.au.snyk.io",
        }
        
        self.base_url = region_map.get(region, "https://api.snyk.io")
        self.headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json"
        }
        
        # Create a session with retry strategy for better reliability
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make an API request to Snyk.
        
        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response as dictionary, or None if error
        """
        url = f"{self.base_url}{endpoint}"
        
        if params is None:
            params = {}
        
        # Always include version parameter
        params["version"] = self.version
        
        try:
            response = self.session.request(method, url, params=params, timeout=30)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logging.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                # Retry once after rate limit
                response = self.session.request(method, url, params=params, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 204:
                return {"status": "success", "message": "No content"}
            elif response.status_code == 404:
                logging.warning(f"Resource not found: {endpoint}")
                return None
            else:
                logging.error(f"API request failed: {response.status_code} - {response.text}")
                response.raise_for_status()
                return None
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Request exception: {str(e)}")
            return None
    
    def get_group_memberships(self, group_id: str, role_name: Optional[str] = None) -> List[Dict]:
        """
        Get group memberships, optionally filtered by role name.
        Handles pagination to fetch all results.
        
        Args:
            group_id: Snyk group ID
            role_name: Optional role name to filter by
            
        Returns:
            List of membership objects
        """
        endpoint = f"/rest/groups/{group_id}/memberships"
        params = {}
        
        if role_name:
            params["role_name"] = role_name
        
        # Use a higher limit to reduce number of pagination requests
        params["limit"] = 100
        
        all_memberships = []
        next_url = None
        
        while True:
            # Use next_url if available, otherwise make initial request
            if next_url:
                # next_url is a relative path like /groups/{group_id}/memberships?version=...&limit=10&starting_after=...
                # We need to prepend /rest to make it a full endpoint path
                if next_url.startswith("/groups/"):
                    next_url = "/rest" + next_url
                url = f"{self.base_url}{next_url}"
                try:
                    response = requests.request("GET", url, headers=self.headers, timeout=30)
                    if response.status_code == 200:
                        response_data = response.json()
                    else:
                        logging.error(f"Pagination request failed: {response.status_code} - {response.text}")
                        break
                except requests.exceptions.RequestException as e:
                    logging.error(f"Pagination request exception: {str(e)}")
                    break
            else:
                response_data = self._make_request("GET", endpoint, params)
                if not response_data:
                    break
            
            if response_data and "data" in response_data:
                all_memberships.extend(response_data["data"])
                logging.info(f"Fetched {len(response_data['data'])} memberships (total so far: {len(all_memberships)})")
            
            # Check for next page
            links = response_data.get("links", {})
            next_url = links.get("next")
            
            if not next_url:
                logging.info("No more pages to fetch")
                break
            else:
                logging.info(f"Found next page URL: {next_url}")
        
        logging.info(f"Total group memberships fetched: {len(all_memberships)}")
        return all_memberships
    
    def get_org_memberships(self, group_id: str, user_id: Optional[str] = None) -> List[Dict]:
        """
        Get organization memberships for a group, optionally filtered by user ID.
        Handles pagination to fetch all results.
        
        Args:
            group_id: Snyk group ID
            user_id: Optional user ID to filter by
            
        Returns:
            List of organization membership objects
        """
        endpoint = f"/rest/groups/{group_id}/org_memberships"
        params = {}
        
        if user_id:
            params["user_id"] = user_id
        
        # Use a higher limit to reduce number of pagination requests
        params["limit"] = 100
        
        all_org_memberships = []
        next_url = None
        
        while True:
            # Use next_url if available, otherwise make initial request
            if next_url:
                # next_url is a relative path like /groups/{group_id}/org_memberships?version=...&limit=10&starting_after=...
                # We need to prepend /rest to make it a full endpoint path
                if next_url.startswith("/groups/"):
                    next_url = "/rest" + next_url
                url = f"{self.base_url}{next_url}"
                try:
                    response = requests.request("GET", url, headers=self.headers, timeout=30)
                    if response.status_code == 200:
                        response_data = response.json()
                    else:
                        logging.error(f"Pagination request failed: {response.status_code} - {response.text}")
                        break
                except requests.exceptions.RequestException as e:
                    logging.error(f"Pagination request exception: {str(e)}")
                    break
            else:
                response_data = self._make_request("GET", endpoint, params)
                if not response_data:
                    break
            
            if response_data and "data" in response_data:
                all_org_memberships.extend(response_data["data"])
                logging.debug(f"Fetched {len(response_data['data'])} org memberships for user {user_id} (total so far: {len(all_org_memberships)})")
            
            # Check for next page
            links = response_data.get("links", {})
            next_url = links.get("next")
            
            if not next_url:
                break
        
        return all_org_memberships


class MembershipChecker:
    """Main class for checking group and organization memberships."""
    
    def __init__(self, client: SnykAPIClient, group_id: str, role_name: Optional[str] = None):
        """
        Initialize the membership checker.
        
        Args:
            client: SnykAPIClient instance
            group_id: Snyk group ID
            role_name: Optional role name to filter group memberships
        """
        self.client = client
        self.group_id = group_id
        self.role_name = role_name
        self.results = {
            "group_memberships": [],
            "users_without_org_memberships": [],
            "users_with_org_memberships": [],
            "group_admins_excluded": [],
            "errors": []
        }
    
    def check_memberships(self) -> Dict[str, Any]:
        """
        Check group memberships and their associated org memberships.
        
        Returns:
            Dictionary containing results
        """
        logging.info(f"Fetching group memberships for group {self.group_id}")
        if self.role_name:
            logging.info(f"Filtering by role_name: {self.role_name}")
        
        # Get group memberships
        group_memberships = self.client.get_group_memberships(self.group_id, self.role_name)
        
        if not group_memberships:
            logging.warning("No group memberships found")
            return self.results
        
        logging.info(f"Found {len(group_memberships)} group membership(s)")
        self.results["group_memberships"] = group_memberships
        
        # Check org memberships for each user
        total_users = len(group_memberships)
        for idx, membership in enumerate(group_memberships, 1):
            # Extract user data from relationships
            relationships = membership.get("relationships", {})
            user_data = relationships.get("user", {}).get("data", {})
            user_id = user_data.get("id")
            user_attributes = user_data.get("attributes", {})
            
            # Extract user email and name
            user_email = user_attributes.get("email", "Unknown")
            user_name = user_attributes.get("name", "Unknown")
            
            # Extract role from relationships
            role_data = relationships.get("role", {}).get("data", {})
            if role_data:
                role_name = role_data.get("attributes", {}).get("name", "Unknown")
            else:
                role_name = "Unknown"
            
            if not user_id:
                logging.warning(f"Could not extract user ID from membership: {membership.get('id')}")
                continue
            
            logging.info(f"Checking org memberships for user {idx}/{total_users}: {user_email} (ID: {user_id}), Role: {role_name}")
            
            # Get org memberships for this user
            org_memberships = self.client.get_org_memberships(self.group_id, user_id)
            
            # Small delay to avoid rate limiting when processing many users
            if idx < total_users:
                time.sleep(0.1)
            logging.debug(f"User {user_email} org memberships count: {len(org_memberships) if org_memberships else 0}")
            
            user_info = {
                "user_id": user_id,
                "email": user_email,
                "name": user_name,
                "role": role_name,
                "org_memberships": org_memberships,
                "org_membership_count": len(org_memberships) if org_memberships else 0
            }
            
            if not org_memberships or len(org_memberships) == 0:
                # Group Admins have access to all org memberships by virtue of their role,
                # so they should not be included in users without org memberships
                if role_name == "Group Admin":
                    logging.info(f"User {user_email} is a Group Admin - excluding from users without org memberships (Group Admins have access to all orgs)")
                    self.results["group_admins_excluded"].append(user_info)
                else:
                    logging.warning(f"User {user_email} has no organization memberships")
                    self.results["users_without_org_memberships"].append(user_info)
            else:
                logging.info(f"User {user_email} has {len(org_memberships)} organization membership(s)")
                self.results["users_with_org_memberships"].append(user_info)
        
        return self.results
    
    def get_results_summary(self) -> str:
        """Generate formatted results summary as a string."""
        lines = []
        lines.append("\n" + "="*80)
        lines.append("SNYK MEMBERSHIP CHECK RESULTS")
        lines.append("="*80)
        
        lines.append(f"\nGroup ID: {self.group_id}")
        if self.role_name:
            lines.append(f"Role Filter: {self.role_name}")
        
        lines.append(f"\nTotal Group Memberships Found: {len(self.results['group_memberships'])}")
        lines.append(f"Users WITH Org Memberships: {len(self.results['users_with_org_memberships'])}")
        lines.append(f"Users WITHOUT Org Memberships: {len(self.results['users_without_org_memberships'])}")
        if self.results["group_admins_excluded"]:
            lines.append(f"Group Admins Excluded (have access to all orgs): {len(self.results['group_admins_excluded'])}")
        
        if self.results["group_admins_excluded"]:
            lines.append("\n" + "-"*80)
            lines.append("GROUP ADMINS EXCLUDED (Have Access to All Organizations):")
            lines.append("-"*80)
            for user in self.results["group_admins_excluded"]:
                lines.append(f"  • {user['email']} ({user['name']})")
                lines.append(f"    User ID: {user['user_id']}")
                lines.append(f"    Role: {user['role']}")
                lines.append(f"    Note: Group Admins have access to all organizations by virtue of their role")
                lines.append("")
        
        if self.results["users_without_org_memberships"]:
            lines.append("\n" + "-"*80)
            lines.append("USERS WITHOUT ORGANIZATION MEMBERSHIPS:")
            lines.append("-"*80)
            for user in self.results["users_without_org_memberships"]:
                lines.append(f"  • {user['email']} ({user['name']})")
                lines.append(f"    User ID: {user['user_id']}")
                lines.append(f"    Role: {user['role']}")
                lines.append("")
        
        if self.results["users_with_org_memberships"]:
            lines.append("\n" + "-"*80)
            lines.append("USERS WITH ORGANIZATION MEMBERSHIPS:")
            lines.append("-"*80)
            for user in self.results["users_with_org_memberships"]:
                lines.append(f"  • {user['email']} ({user['name']})")
                lines.append(f"    User ID: {user['user_id']}")
                lines.append(f"    Role: {user['role']}")
                lines.append(f"    Org Memberships: {user['org_membership_count']}")
                if user['org_memberships']:
                    for org_membership in user['org_memberships']:
                        # Extract org name from relationships.org.data.attributes.name
                        org_relationships = org_membership.get('relationships', {})
                        org_data = org_relationships.get('org', {}).get('data', {})
                        org_name = org_data.get('attributes', {}).get('name', 'Unknown')
                        lines.append(f"      - {org_name}")
                lines.append("")
        
        lines.append("="*80)
        return "\n".join(lines)
    
    def print_results(self, log_file: Optional[str] = None):
        """Print formatted results to console and log file."""
        summary = self.get_results_summary()
        print(summary)
        # Write the summary directly to the log file (not through logging)
        if log_file:
            try:
                with open(log_file, 'a') as f:
                    f.write(summary + "\n")
            except Exception as e:
                logging.warning(f"Could not write summary to log file: {str(e)}")


def setup_logging(log_dir: str = "logs", verbose: bool = False) -> str:
    """
    Set up logging to both console and file.
    
    Args:
        log_dir: Directory for log files
        verbose: If True, include DEBUG, INFO, and WARNING logs in file. If False, only WARNING and above.
        
    Returns:
        Path to the log file
    """
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"membership_check_{timestamp}.log")
    
    # Console handler - always show INFO and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    # File handler - WARNING and above by default, DEBUG and above if verbose
    file_handler = logging.FileHandler(log_file)
    file_level = logging.DEBUG if verbose else logging.WARNING
    file_handler.setLevel(file_level)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all levels, handlers filter
    root_logger.handlers = []  # Clear any existing handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    return log_file


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Find Snyk group memberships and check for organization memberships",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check all group memberships
  python find_users_without_org_memberships.py --token YOUR_TOKEN --group-id GROUP_ID
  
  # Check memberships filtered by role
  python find_users_without_org_memberships.py --token YOUR_TOKEN --group-id GROUP_ID --role-name "group-admin"
  
  # Use EU region
  python find_users_without_org_memberships.py --token YOUR_TOKEN --group-id GROUP_ID --region SNYK-EU-01
        """
    )
    
    parser.add_argument(
        "--token",
        default=os.environ.get("SNYK_TOKEN") or os.environ.get("PERSONAL_SNYK_TOKEN"),
        help="Snyk API token (can also be set via SNYK_TOKEN or PERSONAL_SNYK_TOKEN environment variable)"
    )
    
    parser.add_argument(
        "--group-id",
        default=os.environ.get("GROUP_ID"),
        help="Snyk group ID (can also be set via GROUP_ID environment variable)"
    )
    
    parser.add_argument(
        "--role-name",
        default=None,
        help="Optional role name to filter group memberships"
    )
    
    parser.add_argument(
        "--region",
        default="SNYK-US-01",
        choices=["SNYK-US-01", "SNYK-US-02", "SNYK-EU-01", "SNYK-AU-01"],
        help="Snyk region (default: SNYK-US-01)"
    )
    
    parser.add_argument(
        "--version",
        default="2025-11-05",
        help="API version (default: 2025-11-05)"
    )
    
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path for JSON results (optional)"
    )
    
    parser.add_argument(
        "--verbose",
        "--debug",
        action="store_true",
        dest="verbose",
        help="Include detailed INFO logs in the log file (default: only WARNING and above)"
    )
    
    args = parser.parse_args()
    
    # Validate token
    if not args.token:
        parser.error("Snyk API token is required. Provide --token or set SNYK_TOKEN/PERSONAL_SNYK_TOKEN environment variable.")
    
    # Validate group ID
    if not args.group_id:
        parser.error("Group ID is required. Provide --group-id or set GROUP_ID environment variable.")
    
    # Set up logging
    log_file = setup_logging(verbose=args.verbose)
    logging.info("Starting Snyk membership check")
    logging.info(f"Group ID: {args.group_id}")
    if args.role_name:
        logging.info(f"Role Name Filter: {args.role_name}")
    logging.info(f"Region: {args.region}")
    logging.info(f"API Version: {args.version}")
    
    try:
        # Initialize API client
        client = SnykAPIClient(args.token, args.region, args.version)
        
        # Initialize membership checker
        checker = MembershipChecker(client, args.group_id, args.role_name)
        
        # Perform checks
        results = checker.check_memberships()
        
        # Print results
        checker.print_results(log_file=log_file)
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            logging.info(f"Results saved to {args.output}")
        
        logging.info(f"Log file: {log_file}")
        
        # Exit with appropriate code
        if results["users_without_org_memberships"]:
            sys.exit(1)  # Exit with error if users without org memberships found
        else:
            sys.exit(0)  # Success
        
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

