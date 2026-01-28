import os
import sys
import json
import logging
import argparse
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("automation/godaddy_dns.log"),
    ],
)
logger = logging.getLogger("godaddy_dns")


class GoDaddyDNS:
    def __init__(self, api_key, api_secret, ote=False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = (
            "https://api.ote-godaddy.com" if ote else "https://api.godaddy.com"
        )
        self.headers = {
            "Authorization": f"sso-key {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json",
        }

    def set_a_record(self, domain, subdomain, ip_address):
        """Creates or updates an A record."""
        url = f"{self.base_url}/v1/domains/{domain}/records/A/{subdomain}"
        payload = [{"data": ip_address, "ttl": 600}]

        logger.info(f"Setting A record for {subdomain}.{domain} to {ip_address}...")
        try:
            # GoDaddy PUT replaces all records for that type/name
            response = requests.put(url, headers=self.headers, json=payload, timeout=30)
            if response.status_code == 200:
                logger.info(f"Successfully set A record for {subdomain}.{domain}")
                return True
            else:
                logger.error(
                    f"Failed to set A record: {response.status_code} - {response.text}"
                )
                return False
        except Exception as e:
            logger.error(f"Error calling GoDaddy API: {e}")
            return False

    def remove_a_records(self, domain, subdomain):
        """
        Removes A records for a subdomain.
        """
        url = f"{self.base_url}/v1/domains/{domain}/records/A/{subdomain}"

        logger.info(f"Removing A records for {subdomain}.{domain}...")
        try:
            response = requests.delete(url, headers=self.headers, timeout=30)
            if response.status_code in [200, 204]:
                logger.info(f"Successfully removed A records for {subdomain}.{domain}")
                return True
            elif response.status_code == 404:
                logger.warning(
                    f"No A record found for {subdomain}.{domain} (already clean)"
                )
                return True
            else:
                logger.error(
                    f"Failed to remove A record: {response.status_code} - {response.text}"
                )
                return False
        except Exception as e:
            logger.error(f"Error calling GoDaddy API: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Manage GoDaddy DNS A records.")
    parser.add_argument(
        "--domain", required=True, help="Root domain (e.g., example.com)"
    )
    parser.add_argument("--subdomain", required=True, help="Subdomain (e.g., app or @)")
    parser.add_argument("--ip", help="IP address for the A record (required for --set)")
    parser.add_argument(
        "--set", action="store_true", help="Set (create/update) the record"
    )
    parser.add_argument("--remove", action="store_true", help="Remove the record")
    parser.add_argument(
        "--ote", action="store_true", help="Use GoDaddy OTE (Testing) environment"
    )

    args = parser.parse_args()

    api_key = os.environ.get("GODADDY_API_KEY")
    api_secret = os.environ.get("GODADDY_API_SECRET")

    if not api_key or not api_secret:
        logger.error(
            "GODADDY_API_KEY and GODADDY_API_SECRET environment variables must be set."
        )
        sys.exit(1)

    dns = GoDaddyDNS(api_key, api_secret, ote=args.ote)

    if args.set:
        if not args.ip:
            logger.error("--ip is required when using --set")
            sys.exit(1)
        success = dns.set_a_record(args.domain, args.subdomain, args.ip)
    elif args.remove:
        success = dns.remove_a_records(args.domain, args.subdomain)
    else:
        logger.error("Either --set or --remove must be specified.")
        parser.print_help()
        sys.exit(1)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
