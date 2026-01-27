import requests
import json
import time


def verify():
    url = "http://20.220.210.44:3000"
    email = "admin@alshawwaf.ca"
    password = "Cpwins!1@2026"

    # Login
    login_url = f"{url}/api/auth/sign-in/email"
    payload = {"email": email, "password": password}
    resp = requests.post(login_url, json=payload)
    cookies = resp.cookies

    print("Waiting for final build completion...")
    time.sleep(10)  # Quick check

    # Fetch projects
    trpc_url_proj = f"{url}/api/trpc/project.all?batch=1&input=%7B%220%22%3A%7B%22json%22%3Anull%7D%7D"
    resp_proj = requests.get(trpc_url_proj, cookies=cookies)
    projects = resp_proj.json()[0]["result"]["data"]["json"]

    print("\nFinal Deployment Status:")
    for project in projects:
        print(f"\nProject: {project['name']}")
        # Re-fetch project one to get environments if not present
        trpc_url_one = f"{url}/api/trpc/project.one?batch=1&input=%7B%220%22%3A%7B%22json%22%3A%7B%22projectId%22%3A%22{project['projectId']}%22%7D%7D%7D"
        resp_one = requests.get(trpc_url_one, cookies=cookies)
        project_details = resp_one.json()[0]["result"]["data"]["json"]

        for env in project_details.get("environments", []):
            print(f" Environment: {env['name']} ({env['environmentId']})")
            # Fetch composes for this environment
            trpc_url_comp = f"{url}/api/trpc/compose.all?batch=1&input=%7B%220%22%3A%7B%22json%22%3A%7B%22environmentId%22%3A%22{env['environmentId']}%22%7D%7D%7D"
            resp_comp = requests.get(trpc_url_comp, cookies=cookies)

            try:
                comp_data = resp_comp.json()
                print(
                    f"  Debug Raw Response for {env['name']}: {json.dumps(comp_data)}"
                )
                if isinstance(comp_data, list) and len(comp_data) > 0:
                    composes = (
                        comp_data[0].get("result", {}).get("data", {}).get("json", [])
                    )
                else:
                    print(f"  Unexpected response format: {comp_data}")
                    continue

                if not composes:
                    print("  (No compose applications found)")
                for c in composes:
                    print(f"  - {c['name']} ({c['composeId']}): {c['composeStatus']}")
            except Exception as e:
                print(f"  Error parsing composes: {e}")
                print(f"  Response text: {resp_comp.text}")


if __name__ == "__main__":
    verify()
