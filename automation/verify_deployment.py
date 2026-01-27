import requests
import json
import time
import argparse
import sys


def verify(url, email, password):
    # Login
    login_url = f"{url}/api/auth/sign-in/email"
    payload = {"email": email, "password": password}

    # Session handling
    s = requests.Session()

    try:
        print(f"Logging in to {url} as {email}...")
        resp = s.post(login_url, json=payload, timeout=30)
        if resp.status_code != 200:
            print(f"Login failed: {resp.status_code} - {resp.text}")
            return
        print("Login successful.")
    except Exception as e:
        print(f"Error during login: {e}")
        return

    print("\nFetching project status...")

    try:
        # Fetch projects
        trpc_url_proj = f"{url}/api/trpc/project.all?batch=1&input=%7B%220%22%3A%7B%22json%22%3Anull%7D%7D"
        resp_proj = s.get(trpc_url_proj, timeout=30)

        # Handle empty/error responses
        if resp_proj.status_code != 200:
            print(f"Error fetching projects: {resp_proj.status_code}")
            return

        projects_data = resp_proj.json()
        if not projects_data or "error" in projects_data[0]:
            print(f"Error in project response: {projects_data}")
            return

        projects = projects_data[0]["result"]["data"]["json"]

        print("\n" + "=" * 40)
        print("DEPLOYMENT STATUS")
        print("=" * 40)

        for project in projects:
            print(f"\nProject: {project['name']}")
            # Re-fetch project one to get environments if not present
            trpc_url_one = f"{url}/api/trpc/project.one?batch=1&input=%7B%220%22%3A%7B%22json%22%3A%7B%22projectId%22%3A%22{project['projectId']}%22%7D%7D%7D"
            resp_one = s.get(trpc_url_one, timeout=30)
            project_details = resp_one.json()[0]["result"]["data"]["json"]

            for env in project_details.get("environments", []):
                print(f" Environment: {env['name']} ({env['environmentId']})")

                # Compose apps are often listed directly in the environment details in newer Dokploy
                composes = env.get("composes", [])

                if not composes:
                    print("  (No compose applications found in this environment)")
                for c in composes:
                    print(
                        f"  - {c['name']} | Status: {c['composeStatus']} | Created: {c['createdAt']}"
                    )

    except Exception as e:
        print(f"Error during verification: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify Dokploy Deployments")
    parser.add_argument("--url", required=True, help="Dokploy URL")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password")

    args = parser.parse_args()
    verify(args.url.rstrip("/"), args.email, args.password)
