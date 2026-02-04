import time
import argparse
import sys
import subprocess
import json
import os

# Ensure requests is installed (for fresh VM environments)
try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

print("DEBUG: Script started...")


def request_with_retry(
    method, url, max_retries=3, backoff_factor=2, timeout=30, **kwargs
):
    """Makes an HTTP request with retry logic for transient failures."""
    for attempt in range(max_retries):
        try:
            print(f"DEBUG: [REQ] {method} {url} (Attempt {attempt + 1})")
            start_ptr = time.time()
            response = requests.request(method, url, timeout=timeout, **kwargs)
            duration = time.time() - start_ptr
            print(f"DEBUG: [RES] {response.status_code} ({duration:.2f}s)")

            if response.status_code < 500:
                print(f"DEBUG: [BODY] {response.text[:200]}...")
                return response

            print(f"DEBUG: Server error {response.status_code}, retrying...")
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: Request failed: {e}")
            if attempt == max_retries - 1:
                raise

        sleep_time = backoff_factor**attempt
        print(f"DEBUG: Sleeping {sleep_time}s before retry...")
        time.sleep(sleep_time)

    return requests.request(method, url, timeout=timeout, **kwargs)


def wait_for_dokploy(url, timeout=300):
    """Wait for Dokploy service to be accessible."""
    start_time = time.time()
    print(f"Waiting for Dokploy at {url}...")
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print("Dokploy is up and running!")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(5)
    print("Timeout waiting for Dokploy")
    return False


def register_admin(url, email, password, name="Admin", last_name="User"):
    """Register admin user via the Better Auth sign-up endpoint."""
    signup_url = f"{url}/api/auth/sign-up/email"
    headers = {"Content-Type": "application/json", "Accept": "*/*"}
    payload = {
        "email": email,
        "password": password,
        "name": name,
        "lastName": last_name,
    }

    print(f"Checking/Registering admin with email: {email}")
    try:
        response = request_with_retry("POST", signup_url, json=payload, headers=headers)
        if response.status_code in [200, 201]:
            print("SUCCESS! Admin account created successfully!")
            return True
        elif response.status_code == 422 and "USER_ALREADY_EXISTS" in response.text:
            print("Admin account already exists, proceeding to login.")
            return True
        else:
            print(f"Registration status: {response.status_code}")
            print(f"DEBUG: Response Body: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error during registration: {e}")
        return False


def login(url, email, password):
    """Log in to Dokploy and return the session token cookie."""
    login_url = f"{url}/api/auth/sign-in/email"
    payload = {"email": email, "password": password}

    print(f"Logging in as {email}...")
    try:
        response = request_with_retry("POST", login_url, json=payload)
        if response.status_code == 200:
            print("Login successful!")
            return response.cookies
        else:
            print(f"Login failed: {response.status_code}")
            print(f"DEBUG: Response Body: {response.text}")
            return None
    except Exception as e:
        print(f"Error during login: {e}")
        return None


def setup_ssh_and_server(
    url, cookies, ip_address, organization_id, username="adminuser"
):
    """Generate SSH key, add to authorized_keys, and register server."""
    # 1. Generate SSH Key in Dokploy
    trpc_url_gen = f"{url}/api/trpc/sshKey.generate?batch=1"
    payload_gen = {"0": {"json": {}}}

    import time

    timestamp = int(time.time())
    key_name = f"Key-{timestamp}"
    server_name = f"Server-{timestamp}"

    print(f"Generating SSH key ({key_name}) in Dokploy...")
    try:
        resp_gen = request_with_retry(
            "POST", trpc_url_gen, json=payload_gen, cookies=cookies
        )
        keys = resp_gen.json()[0]["result"]["data"]["json"]
        private_key = keys["privateKey"]
        public_key = keys["publicKey"]

        # 2. Add public key to authorized_keys on VM (both adminuser and root)
        # Purge Azure's restricted root authorized_keys and enable root login
        print(f"Authorizing public key on VM ({ip_address}) for adminuser and root...")
        ssh_cmd = [
            "ssh",
            "-i",
            "~/.ssh/id_rsa",
            "-o",
            "StrictHostKeyChecking=no",
            f"{username}@{ip_address}",
            f"echo '{public_key}' | tee -a /home/{username}/.ssh/authorized_keys > /dev/null && "
            f"sudo sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config && "
            f"sudo sed -i 's/PermitRootLogin no/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config && "
            f"sudo systemctl reload ssh && "
            f"sudo mkdir -p /root/.ssh && "
            f"echo '{public_key}' | sudo tee /root/.ssh/authorized_keys > /dev/null",
        ]
        subprocess.run(ssh_cmd, check=True)

        # 3. Create SSH Key record in Dokploy
        trpc_url_key = f"{url}/api/trpc/sshKey.create?batch=1"
        payload_key = {
            "0": {
                "json": {
                    "name": key_name,
                    "description": "Automated key for local deployment",
                    "privateKey": private_key,
                    "publicKey": public_key,
                    "organizationId": organization_id,
                }
            }
        }
        print(f"Registering SSH key record ({key_name}) in Dokploy...")
        request_with_retry("POST", trpc_url_key, json=payload_key, cookies=cookies)

        # 4. Fetch the created SSH key ID by name
        trpc_url_all_keys = f"{url}/api/trpc/sshKey.all?batch=1&input=%7B%220%22%3A%7B%22json%22%3Anull%7D%7D"
        resp_all = request_with_retry("GET", trpc_url_all_keys, cookies=cookies)
        keys_list = resp_all.json()[0]["result"]["data"]["json"]
        ssh_key_id = next(
            (k["sshKeyId"] for k in keys_list if k["name"] == key_name), None
        )

        if not ssh_key_id:
            print(f"Error: Could not find created SSH key with name {key_name}")
            return None

        print(f"Found SSH Key ID: {ssh_key_id}")

        # 4. Create Server record in Dokploy (using ROOT)
        trpc_url_srv = f"{url}/api/trpc/server.create?batch=1"
        payload_srv = {
            "0": {
                "json": {
                    "name": server_name,
                    "description": "Primary deployment server",
                    "ipAddress": ip_address,
                    "port": 22,
                    "username": "root",
                    "sshKeyId": ssh_key_id,
                    "serverType": "deploy",
                    "organizationId": organization_id,
                }
            }
        }
        print(f"Initializing server ({server_name}) in Dokploy...")
        resp_srv = request_with_retry(
            "POST", trpc_url_srv, json=payload_srv, cookies=cookies
        )
        data_srv = resp_srv.json()

        if isinstance(data_srv, list) and len(data_srv) > 0:
            res_srv = data_srv[0].get("result", {})
            if "error" in res_srv:
                print(f"Server creation error: {res_srv['error']}")
                return None
            server_id = res_srv.get("data", {}).get("json", {}).get("serverId")
        else:
            print(f"DEBUG: Unexpected server creation response: {data_srv}")
            return None

        # 5. Start server setup
        print("Triggering server setup...")
        trpc_url_setup = f"{url}/api/trpc/server.setup?batch=1"
        request_with_retry(
            "POST",
            trpc_url_setup,
            json={"0": {"json": {"serverId": server_id}}},
            cookies=cookies,
            timeout=60,  # Increased timeout for initial setup trigger
        )

        return server_id
    except Exception as e:
        print(f"Error during SSH/Server setup: {e}")
        return None


def delete_all_services(url, cookies, env_id):
    """Delete all services (apps and compose) in the environment using environment.one."""
    trpc_url_one = f"{url}/api/trpc/environment.one?batch=1&input=%7B%220%22%3A%7B%22json%22%3A%7B%22environmentId%22%3A%22{env_id}%22%7D%7D%7D"
    try:
        resp = request_with_retry("GET", trpc_url_one, cookies=cookies)
        env_data = resp.json()[0]["result"]["data"]["json"]

        # Delete Compose Applications
        composes = env_data.get("compose", [])
        for comp in composes:
            print(f"Deleting compose app: {comp['name']}...")
            trpc_url_del = f"{url}/api/trpc/compose.delete?batch=1"
            request_with_retry(
                "POST",
                trpc_url_del,
                json={"0": {"json": {"composeId": comp["composeId"], "deleteVolumes": True}}},
                cookies=cookies,
            )

        # Delete Single Applications
        apps = env_data.get("applications", [])
        for app in apps:
            print(f"Deleting application: {app['name']}...")
            trpc_url_del = f"{url}/api/trpc/application.delete?batch=1"
            request_with_retry(
                "POST",
                trpc_url_del,
                json={"0": {"json": {"applicationId": app["applicationId"]}}},
                cookies=cookies,
            )
    except Exception as e:
        print(f"DEBUG: Warning - could not cleanup services: {e}")
        pass


def get_all_project_ids(url, cookies):
    """Find all existing projects and return their IDs and a list of all Env IDs."""
    trpc_url = f"{url}/api/trpc/project.all?batch=1&input=%7B%220%22%3A%7B%22json%22%3Anull%2C%22meta%22%3A%7B%22values%22%3A%5B%22undefined%22%5D%7D%7D%7D"
    matches = []
    try:
        response = requests.get(trpc_url, cookies=cookies, timeout=30)
        data = response.json()
        projects = data[0]["result"]["data"]["json"]
        for p in projects:
            projectId = p["projectId"]
            env_ids = get_all_environment_ids(url, cookies, projectId)
            matches.append((projectId, env_ids, p["name"]))
    except Exception as e:
        print(f"DEBUG: Error listing all projects: {e}")
    return matches


def get_all_environment_ids(url, cookies, project_id):
    """Get all environment IDs for the project."""
    trpc_url = f"{url}/api/trpc/project.one?batch=1&input=%7B%220%22%3A%7B%22json%22%3A%7B%22projectId%22%3A%22{project_id}%22%7D%7D%7D"
    ids = []
    try:
        response = requests.get(trpc_url, cookies=cookies, timeout=30)
        data = response.json()
        environments = data[0]["result"]["data"]["json"]["environments"]
        for env in environments:
            ids.append(env["environmentId"])
    except Exception:
        pass
    return ids


def get_environment_id(url, cookies, project_id):
    """Get the production environment ID for the project."""
    trpc_url = f"{url}/api/trpc/project.one?batch=1&input=%7B%220%22%3A%7B%22json%22%3A%7B%22projectId%22%3A%22{project_id}%22%7D%7D%7D"
    try:
        response = requests.get(trpc_url, cookies=cookies, timeout=30)
        data = response.json()
        environments = data[0]["result"]["data"]["json"]["environments"]
        for env in environments:
            if env["name"] == "production":
                return env["environmentId"]
    except Exception:
        pass
    return None


def delete_project(url, cookies, project_id):
    """Delete a project and all its resources."""
    print(f"Deleting project {project_id}...")
    trpc_url_del = f"{url}/api/trpc/project.delete?batch=1"
    payload = {"0": {"json": {"projectId": project_id}}}
    try:
        resp = requests.post(trpc_url_del, json=payload, cookies=cookies, timeout=30)
        if resp.status_code == 200:
            print("Project deleted.")
            return True
        else:
            print(f"Failed to delete project: {resp.status_code}")
            return False
    except Exception as e:
        print(f"Error deleting project: {e}")
        return False


def force_cleanup_ports(ip_address, username, key_path, ports):
    """Forcefully remove docker containers binding specific ports via SSH."""
    print(f"Force-cleaning ports {ports} on {ip_address}...")

    # Construct command to find and kill containers mapping these ports
    # We loop through each port to be safe
    commands = []

    # Check for docker ps filtering for published ports
    for port in ports:
        # Docker formatting: 0.0.0.0:9000->... or :::9000->...
        # We look for containers publishing this port
        cmd = f"docker ps -a --format '{{{{.ID}}}} {{{{.Ports}}}}' | grep ':{port}->' | awk '{{print $1}}' | xargs -r docker rm -f"
        commands.append(cmd)

    full_command = " && ".join(commands)

    ssh_cmd = [
        "ssh",
        "-i",
        key_path,
        "-o",
        "StrictHostKeyChecking=no",
        f"{username}@{ip_address}",
        full_command,
    ]

    try:
        subprocess.run(
            ssh_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print("Port cleanup commands executed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Warning: Port cleanup failed (may be harmless if empty): {e}")
        return False


def create_project(url, cookies, organization_id, name="Agentic Demos"):
    """Create a new project in Dokploy."""
    trpc_url = f"{url}/api/trpc/project.create?batch=1"
    payload = {
        "0": {
            "json": {
                "name": name,
                "description": "Automated Project",
                "projectId": "",
                "organizationId": organization_id,
            }
        }
    }
    print(f"Creating project: {name}...")
    try:
        response = requests.post(trpc_url, json=payload, cookies=cookies, timeout=30)
        data = response.json()
        print(f"DEBUG: Create project response structure: {list(data[0].keys())}")
        result = data[0].get("result", {})
        if "error" in result:
             print(f"Error creating project: {result['error']}")
             return None, None
             
        project_data = result["data"]["json"]["project"]
        env_data = result["data"]["json"]["environment"]
        print(f"DEBUG: Created Project ID: {project_data.get('projectId')}, Env ID: {env_data.get('environmentId')}")
        return project_data["projectId"], env_data["environmentId"]
    except Exception as e:
        print(f"Exception creating project: {e}")
        return None, None


def create_compose(url, cookies, project_id, environment_id, name, server_id):
    """Create a Compose application."""
    trpc_url = f"{url}/api/trpc/compose.create?batch=1"
    payload = {
        "0": {
            "json": {
                "name": name,
                "description": f"Compose deployment of {name}",
                "environmentId": environment_id,
                "serverId": server_id,
                "composeType": "docker-compose",
                "appName": name.lower().replace(" ", "-"),
            }
        }
    }
    print(f"Creating compose application: {name}...")
    try:
        resp = request_with_retry("POST", trpc_url, json=payload, cookies=cookies)
        data = resp.json()
        return data[0]["result"]["data"]["json"]["composeId"]
    except Exception as e:
        print(f"Error creating compose: {e}")
        return None


def get_all_compose_ids(url, cookies, environment_id):
    """Fetch all compose apps for a given environment."""
    trpc_url = f"{url}/api/trpc/compose.all?batch=1&input=%7B%220%22%3A%7B%22json%22%3A%7B%22environmentId%22%3A%22{environment_id}%22%7D%7D%7D"
    try:
        resp = requests.get(trpc_url, cookies=cookies, timeout=10).json()
        apps = resp[0]["result"]["data"]["json"]
        return [{"name": a["name"], "composeId": a["composeId"]} for a in apps]
    except Exception as e:
        print(f"Error fetching compose apps: {e}")
        return []


def get_compose_app_name(url, cookies, compose_id):
    """Fetch the full appName (with suffix) for a compose service."""
    trpc_url = f"{url}/api/trpc/compose.one?batch=1&input=%7B%220%22%3A%7B%22json%22%3A%7B%22composeId%22%3A%22{compose_id}%22%7D%7D%7D"
    try:
        resp = requests.get(trpc_url, cookies=cookies, timeout=10).json()
        return resp[0]["result"]["data"]["json"]["appName"]
    except Exception as e:
        print(f"Error fetching app name: {e}")
        return None


def update_compose_git(
    url, cookies, compose_id, github_url, env_vars=None, ssh_key_id=None, branch="main", compose_command=None
):
    """Connect GitHub repo to Compose app."""
    trpc_url = f"{url}/api/trpc/compose.update?batch=1"

    json_payload = {
        "customGitBranch": branch,
        "customGitUrl": github_url,
        "customGitSSHKeyId": ssh_key_id,
        "composeId": compose_id,
        "sourceType": "git",
        "composePath": "./docker-compose.yml",
        "composeStatus": "idle",
        "watchPaths": [],
        "enableSubmodules": False,
        "randomize": True,  # Ensure no port conflicts
    }

    if compose_command:
        json_payload["command"] = compose_command
        print(f"Setting compose command: {compose_command}")

    if env_vars:
        json_payload["env"] = env_vars
        json_payload["envVars"] = env_vars

    meta_payload = {"values": {}}
    if ssh_key_id is None:
        meta_payload["values"]["customGitSSHKeyId"] = ["undefined"]

    payload = {
        "0": {
            "json": json_payload,
            "meta": meta_payload,
        }
    }
    print(f"Connecting GitHub (sourceType: git): {github_url}...")
    try:
        request_with_retry("POST", trpc_url, json=payload, cookies=cookies, timeout=30)
    except Exception as e:
        print(f"Error updating compose git: {e}")


def create_domain(url, cookies, compose_id, host, port, service_name):
    """Create a domain for a Compose service."""
    trpc_url = f"{url}/api/trpc/domain.create?batch=1"
    payload = {
        "0": {
            "json": {
                "host": host,
                "path": "/",
                "port": port,
                "https": True,
                "composeId": compose_id,
                "serviceName": service_name,
                "certificateType": "letsencrypt",
                "domainType": "compose",
            }
        }
    }
    print(f"Setting up domain: {host} (service: {service_name}, port: {port})...")
    try:
        request_with_retry("POST", trpc_url, json=payload, cookies=cookies, timeout=30)
    except Exception as e:
        print(f"Error creating domain: {e}")


def update_compose_file(url, cookies, compose_id, compose_content, source_type=None):
    """Update the docker-compose.yml content for a Compose application."""
    trpc_url = f"{url}/api/trpc/compose.update?batch=1"
    json_data = {
        "composeId": compose_id,
    }
    if compose_content is not None:
        json_data["composeFile"] = compose_content
    if source_type:
        json_data["sourceType"] = source_type
        
    payload = {
        "0": {
            "json": json_data
        }
    }
    print(f"Updating compose file for {compose_id} (sourceType={source_type})...")
    try:
        request_with_retry("POST", trpc_url, json=payload, cookies=cookies, timeout=30)
    except Exception as e:
        print(f"Error updating compose file: {e}")


def update_compose_env(url, cookies, compose_id, env_content):
    """Update environment variables for a Compose application."""
    trpc_url = f"{url}/api/trpc/compose.update?batch=1"

    # In Dokploy, env vars are often sent as a single string field 'envVars'
    # in the compose update payload.
    payload = {"0": {"json": {"composeId": compose_id, "envVars": env_content}}}
    print(f"Injecting environment variables for compose {compose_id}...")
    try:
        request_with_retry("POST", trpc_url, json=payload, cookies=cookies, timeout=30)
    except Exception as e:
        print(f"Error updating environment variables: {e}")


def detect_env_file(app_name):
    # 1. Try exact slugs
    slugs = [
        app_name.lower().replace(" ", "-"),
        app_name.lower().replace(" ", "_"),
        app_name.lower().replace("-", "_"),
        app_name.lower(),
    ]

    search_dirs = [".", "automation", os.path.join("automation", "envs")]

    for directory in search_dirs:
        for slug in slugs:
            # Check for .env_<slug>
            path = os.path.join(directory, f".env_{slug}")
            if os.path.exists(path):
                return path

    # 2. Try keyword matching if no exact slug matches
    # For "CP Agentic MCP Playground", keywords might be ["agentic", "mcp"]
    keywords = [w.lower() for w in app_name.split() if len(w) > 3]
    for directory in search_dirs:
        try:
            files = os.listdir(directory)
            for f in files:
                if f.startswith(".env_"):
                    # Check if any keyword is in the filename
                    for kw in keywords:
                        if kw in f.lower():
                            return os.path.join(directory, f)
        except Exception:
            continue

    return None


def deploy_compose(url, cookies, compose_id):
    """Trigger deployment for Compose app."""
    trpc_url = f"{url}/api/trpc/compose.deploy?batch=1"
    payload = {"0": {"json": {"composeId": compose_id, "title": "Automated Setup"}}}
    print(f"Triggering deployment for compose {compose_id}...")
    try:
        request_with_retry("POST", trpc_url, json=payload, cookies=cookies, timeout=60)
    except Exception as e:
        print(f"Error deploying compose: {e}")


def manual_git_clone_and_inject(ip_address, full_app_name, repo_url, ssh_private_path):
    """Manually clone the repo and inject customizations via SSH."""
    print(f"Manually cloning {repo_url} for {full_app_name}...")
    code_dir = f"/etc/dokploy/compose/{full_app_name}/code"
    
    commands = [
        f"sudo rm -rf {code_dir}",
        f"sudo mkdir -p {code_dir}",
        f"sudo git clone {repo_url} {code_dir}",
        f"sudo chown -R adminuser:adminuser {code_dir}"
    ]
    
    try:
        for cmd in commands:
            ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-i", ssh_private_path, f"adminuser@{ip_address}", cmd]
            subprocess.run(ssh_cmd, check=True)
            
        # Now inject
        inject_dev_hub_customizations(ip_address, full_app_name, ssh_private_path, wait=False)
        return True
    except Exception as e:
        print(f"Error during manual clone and inject: {e}")
        return False


def inject_dev_hub_customizations(ip_address, full_app_name, ssh_private_path, wait=True):
    """Inject custom UI files into the Dev-Hub deployment."""
    print(f"Injecting Dev-Hub UI customizations for {full_app_name}...")
    
    directory = f"/etc/dokploy/compose/{full_app_name}/code/frontend/src/pages"
    
    if wait:
        print(f"Waiting for target directory to be created: {directory}")
        max_retries = 12
        for i in range(max_retries):
            check_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-i", ssh_private_path, f"adminuser@{ip_address}", f"test -d {directory} && echo 'exists'"]
            try:
                result = subprocess.run(check_cmd, capture_output=True, text=True)
                if "exists" in result.stdout:
                    print("Directory found!")
                    break
            except:
                pass
            print(f"Waiting... ({i+1}/{max_retries})")
            time.sleep(5)
        else:
            print("Timeout waiting for directory creation. Skipping injection.")
            return

    local_files = {
        "automation/LandingPage_new.tsx": f"/etc/dokploy/compose/{full_app_name}/code/frontend/src/pages/LandingPage.tsx",
        "automation/AppCard_new.tsx": f"/etc/dokploy/compose/{full_app_name}/code/frontend/src/components/AppCard.tsx",
        "automation/index_update.css": f"/tmp/index_update.css"
    }
    
    try:
        for local, remote in local_files.items():
            if os.path.exists(local):
                print(f"Uploading {local} to {remote}...")
                scp_cmd = ["scp", "-o", "StrictHostKeyChecking=no", "-i", ssh_private_path, local, f"adminuser@{ip_address}:{remote}"]
                subprocess.run(scp_cmd, check=True)
        
        # Append CSS
        append_css_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no", "-i", ssh_private_path, f"adminuser@{ip_address}",
            f"sudo bash -c 'cat /tmp/index_update.css >> /etc/dokploy/compose/{full_app_name}/code/frontend/src/index.css'"
        ]
        subprocess.run(append_css_cmd, check=True)
        print("UI customizations injected successfully.")
    except Exception as e:
        print(f"Warning: Failed to inject UI customizations: {e}")


def wait_for_server_ready(url, cookies, server_id, timeout=300):
    """Wait for server status to become active."""
    print(f"Waiting for server {server_id} to be active...")
    start_time = time.time()
    trpc_url = f"{url}/api/trpc/server.one?batch=1&input=%7B%220%22%3A%7B%22json%22%3A%7B%22serverId%22%3A%22{server_id}%22%7D%7D%7D"
    while time.time() - start_time < timeout:
        try:
            resp = requests.get(trpc_url, cookies=cookies, timeout=10).json()
            status = resp[0]["result"]["data"]["json"]["serverStatus"]
            if status == "active":
                print("Server is active!")
                return True
            print(f"Server status: {status} (waiting...)")
        except Exception as e:
            print(f"Error checking server status: {e}")
        time.sleep(10)
    return False


def sanitize_compose_file(content, app_name):
    """Remove problematic lines like bind mounts that hide image code."""
    # Common fixes for all apps:
    # 1. Replace ~ with a relative path to avoid "invalid proto" errors in some Docker versions
    content = content.replace("~/.flowise", "./flowise_data")
    content = content.replace("~/.n8n", "./n8n_data")
    content = content.replace("~/.docker", "./docker_config")
    
    if "Lakera" in app_name:
        # Remove common bind mount that blinds the container: .:/app
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            if ".:/app" in line:
                print(f"Sanitizing line in {app_name}: {line.strip()}")
                continue
            new_lines.append(line)
        return "\n".join(new_lines)
    return content

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automate Dokploy setup with Compose and Domains"
    )
    parser.add_argument("--url", required=True, help="Dokploy URL")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password")
    parser.add_argument("--ip", help="VM Public IP (default: derived from URL)")
    parser.add_argument(
        "--config", default="dokploy_config.json", help="Path to apps config JSON"
    )
    parser.add_argument(
        "--ssh-private",
        default="~/.ssh/id_rsa",
        help="Path to private SSH key (default: ~/.ssh/id_rsa)",
    )
    parser.add_argument(
        "--ssh-public",
        default="~/.ssh/id_rsa.pub",
        help="Path to public SSH key (default: ~/.ssh/id_rsa.pub)",
    )
    parser.add_argument(
        "--project",
        default="Agentic Demos",
        help="Project name (default: Agentic Demos)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete existing project before starting (Fresh Rebuild)",
    )
    parser.add_argument("--app", help="Filter: Only process this specific app name")

    args = parser.parse_args()
    url = args.url.rstrip("/")
    ip_address = args.ip or url.split("//")[-1].split(":")[0]

    # Helper to find local env files
    def find_env_file(app_name):
        slugs = [
            app_name.lower().replace(" ", "-"),
            app_name.lower().replace(" ", "_"),
            app_name.lower(),
        ]
        search_dirs = [".", "automation"]
        for directory in search_dirs:
            for slug in slugs:
                path = os.path.join(directory, f".env_{slug}")
                if os.path.exists(path):
                    return path
        return None

    # Helper to copy env file to remote
    def copy_env_file_to_remote(local_path, remote_ip, app_slug):
        try:
            target_path = f"/etc/dokploy/compose/{app_slug}/code/.env"
            print(f"Ensuring {target_path} on {remote_ip}...")
            
            # Check if we're running locally on the target VM
            is_local = False
            try:
                import socket
                hostname = os.uname()[1] if hasattr(os, 'uname') else socket.gethostname()
                # Simple check: if ip is reachable on loopback or matches hostname/etc
                # But safer to just check if the directory exists locally
                if os.path.exists(f"/etc/dokploy/compose/{app_slug}"):
                    is_local = True
            except:
                pass

            if is_local:
                print(f"Detected local execution. Copying {local_path} to {target_path}...")
                subprocess.run(["sudo", "mkdir", "-p", os.path.dirname(target_path)], check=True)
                subprocess.run(["sudo", "cp", local_path, target_path], check=True)
                subprocess.run(["sudo", "chown", "root:root", target_path], check=True)
                subprocess.run(["sudo", "chmod", "644", target_path], check=True)
            else:
                scp_cmd = [
                    "scp", "-o", "StrictHostKeyChecking=no", "-i", ssh_private_path,
                    local_path, f"adminuser@{remote_ip}:{target_path}"
                ]
                subprocess.run(scp_cmd, check=True)
                # Fix permissions
                ssh_cmd = [
                    "ssh", "-o", "StrictHostKeyChecking=no", "-i", ssh_private_path,
                    f"adminuser@{remote_ip}",
                    f"sudo chown root:root {target_path} && sudo chmod 644 {target_path}"
                ]
                subprocess.run(ssh_cmd, check=True)
            print("Env file copied successfully.")
        except Exception as e:
            print(f"Error copying env file: {e}")
    import os

    ssh_private_path = os.path.expanduser(args.ssh_private)
    ssh_public_path = os.path.expanduser(args.ssh_public)

    if not os.path.exists(ssh_private_path) or not os.path.exists(ssh_public_path):
        print(f"Error: SSH keys not found at {ssh_private_path} or {ssh_public_path}")
        sys.exit(1)

    # Load Config
    try:
        with open(args.config, "r") as f:
            app_configs = json.load(f)
    except Exception as e:
        print(f"Error loading config file {args.config}: {e}")
        sys.exit(1)

    if wait_for_dokploy(url):
        register_admin(url, args.email, args.password)
        cookies = login(url, args.email, args.password)
        if not cookies:
            sys.exit(1)

        # Organization
        trpc_url_org_all = f"{url}/api/trpc/organization.all?batch=1&input=%7B%220%22%3A%7B%22json%22%3Anull%7D%7D"
        org_data = requests.get(trpc_url_org_all, cookies=cookies).json()
        try:
            org_id = org_data[0]["result"]["data"]["json"][0]["id"]
            print(f"Using Organization ID: {org_id}")
        except (IndexError, KeyError, TypeError):
            print(f"Error fetching Organization ID. Response: {org_data}")
            sys.exit(1)

        # Server Management
        trpc_url_srv_all = f"{url}/api/trpc/server.all?batch=1&input=%7B%220%22%3A%7B%22json%22%3Anull%7D%7D"
        srv_data = requests.get(trpc_url_srv_all, cookies=cookies).json()
        servers = srv_data[0].get("result", {}).get("data", {}).get("json", [])

        server_id = None
        needs_setup = False
        if servers:
            existing_srv = servers[0]
            # Verify if the existing server is actually setup with root (to avoid permission errors)
            if existing_srv.get("username") == "root" and existing_srv.get("sshKeyId"):
                server_id = existing_srv["serverId"]
                print(
                    f"Using existing root server: {existing_srv['name']} ({server_id})"
                )
            else:
                print(
                    f"Existing server {existing_srv['name']} is not root or has no key. Forcing new setup..."
                )
                needs_setup = True
                server_id = setup_ssh_and_server(url, cookies, ip_address, org_id)
        else:
            needs_setup = True
            server_id = setup_ssh_and_server(url, cookies, ip_address, org_id)

        if not server_id:
            print("Critical: No server available or server setup failed.")
            sys.exit(1)

        if needs_setup:
            wait_for_server_ready(url, cookies, server_id)

        print(f"Final Server ID for deployment: {server_id}")

        # Git SSH Key Registration
        git_ssh_key_id = None
        try:
            with open(ssh_private_path, "r") as f:
                user_private_key = f.read()
            with open(ssh_public_path, "r") as f:
                user_public_key = f.read()

            print("Registering User SSH Key in Dokploy for Git...")
            trpc_url_key = f"{url}/api/trpc/sshKey.create?batch=1"
            payload_git_key = {
                "0": {
                    "json": {
                        "name": "UserGitHubKey",
                        "description": "User's local SSH key for Git",
                        "privateKey": user_private_key,
                        "publicKey": user_public_key,
                        "organizationId": org_id,
                    }
                }
            }
            requests.post(
                trpc_url_key, json=payload_git_key, cookies=cookies, timeout=30
            )

            # Fetch the ID
            trpc_url_all_keys = f"{url}/api/trpc/sshKey.all?batch=1&input=%7B%220%22%3A%7B%22json%22%3Anull%7D%7D"
            resp_all = requests.get(trpc_url_all_keys, cookies=cookies, timeout=30)
            keys_list = resp_all.json()[0]["result"]["data"]["json"]
            git_ssh_key_id = next(
                (k["sshKeyId"] for k in keys_list if k["name"] == "UserGitHubKey"), None
            )
            print(f"Git SSH Key ID: {git_ssh_key_id}")
        except Exception as e:
            print(f"Warning: Could not register user SSH key for Git: {e}")

        all_projects = get_all_project_ids(url, cookies)

        project_id = None
        env_id = None

        if args.clean and all_projects:
            print(
                f"Clean mode: Found {len(all_projects)} total projects. Deleting ALL to ensure fresh state..."
            )
            for pid, eids, pname in all_projects:
                print(f"Purging project: {pname} ({pid})...")
                for eid in eids:
                    print(f"  Cleaning environment: {eid}")
                    delete_all_services(url, cookies, eid)
                
                delete_project(url, cookies, pid)

            # Aggressive cleanup via SSH (Disabled)
            # print("Performing NUCLEAR Docker cleanup via SSH...")
            # Delete ALL containers, prune networks, volumes, and images
            cleanup_cmd = (
                "sudo docker stop $(sudo docker ps -aq) 2>/dev/null || true; "
                "sudo docker rm -f $(sudo docker ps -aq) 2>/dev/null || true; "
                "sudo docker system prune -af --volumes"
            )
            try:
                ssh_cmd = [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-i", ssh_private_path,
                    f"adminuser@{ip_address}",
                    cleanup_cmd
                ]
                # subprocess.run(ssh_cmd, check=True)
                # print("SSH Nuclear cleanup completed.")
            except Exception as e:
                print(f"Warning: SSH Cleanup encountered an error: {e}")

            print("Waiting for Dokploy to stabilize...")
            time.sleep(10)
            all_projects = []

        # Find or create our target project
        existing_target = [p for p in all_projects if p[2] == args.project]
        if existing_target:
            project_id, env_ids, _ = existing_target[0]
            print(f"Found existing project: {args.project} ({project_id}) with env_ids: {env_ids}")
            # Handle env_ids being a list from get_all_project_ids modification
            if isinstance(env_ids, list) and len(env_ids) > 0:
                env_id = env_ids[0]
            else:
                env_id = env_ids if env_ids else None
                
            if not env_id:
                print(f"Warning: env_id is null for project {args.project}. Fetching manually...")
                env_id = get_environment_id(url, cookies, project_id)
        else:
            project_id, env_id = create_project(url, cookies, org_id, name=args.project)

        if not project_id or not env_id:
            print(f"CRITICAL: Failed to establish project/environment context. project_id={project_id}, env_id={env_id}")
            sys.exit(1)

        if not args.app:
            print("Cleaning up existing deployments...")
            delete_all_services(url, cookies, env_id)

        # Fetch existing apps in the environment
        existing_apps = get_all_compose_ids(url, cookies, env_id)
        
        for cfg in app_configs:
            if args.app and args.app.lower() not in cfg["name"].lower():
                print(f"Skipping {cfg['name']} (filter: {args.app})")
                continue

            # Check if exists
            target_app = next((a for a in existing_apps if a["name"] == cfg["name"]), None)
            
            if target_app:
                cid = target_app["composeId"]
                print(f"Using existing compose application: {cfg['name']} ({cid})")
            else:
                cid = create_compose(
                    url, cookies, project_id, env_id, cfg["name"], server_id
                )
            if cid:
                repo_url = cfg["repo"]
                ssh_key_to_use = git_ssh_key_id

                if repo_url.startswith("https://"):
                    print(
                        f"Detected HTTPS URL for {cfg['name']}, skipping SSH key attachment."
                    )
                    ssh_key_to_use = None

                # Detect .env file early to combine with git update
                env_file = detect_env_file(cfg["name"])
                env_content = None
                if env_file:
                    print(f"Found environment file for {cfg['name']}: {env_file}")
                    try:
                        with open(env_file, "r") as f:
                            env_content = f.read()
                    except Exception as e:
                        print(f"Warning: Could not read env file {env_file}: {e}")
                else:
                    print(f"No environment file found for {cfg['name']}.")

                # Get branch if specified
                branch = cfg.get("branch", "main")
                
                # Get compose command if specified (e.g., "--profile cpu")
                compose_command = cfg.get("composeCommand", None)
                
                update_compose_git(
                    url, cookies, cid, repo_url, env_content, ssh_key_to_use,
                    branch=branch,
                    compose_command=compose_command
                )
                
                # Double-check env vars are injected via API
                if env_content:
                    update_compose_env(url, cookies, cid, env_content)

                # Keep sourceType as "git" - let Dokploy pull the docker-compose.yml from GitHub
                # This is consistent with how other apps in this project are deployed
                print(f"Using GitHub-linked docker-compose.yml for {cfg['name']}...")

                if "exposures" in cfg:
                    print(f"Setting up multiple domains for {cfg['name']}...")
                    for exp in cfg["exposures"]:
                        create_domain(
                            url,
                            cookies,
                            cid,
                            exp["domain"],
                            exp["port"],
                            exp["service"],
                        )
                elif "domain" in cfg:
                    create_domain(
                        url, cookies, cid, cfg["domain"], cfg["port"], cfg["service"]
                    )

                if "Dev-Hub" in cfg["name"]:
                    full_app_name = get_compose_app_name(url, cookies, cid)
                    if full_app_name:
                        manual_git_clone_and_inject(ip_address, full_app_name, repo_url, ssh_private_path)
                        
                        # Read the local compose file
                        local_compose_path = "automation/dev_hub_compose.yml"
                        if os.path.exists(local_compose_path):
                            with open(local_compose_path, "r") as f:
                                compose_content = f.read()
                            print(f"Switching {cfg['name']} to sourceType: compose (Local)")
                            update_compose_file(url, cookies, cid, compose_content, source_type="compose")

                deploy_compose(url, cookies, cid)

                # Ensure .env file is present on the server (robustness)
                if env_file:
                    full_app_name = get_compose_app_name(url, cookies, cid)
                    if full_app_name:
                        print(f"Ensuring .env file for {full_app_name}...")
                        import time
                        time.sleep(5)  # Give Dokploy a moment to create the directory
                        copy_env_file_to_remote(env_file, ip_address, full_app_name)

        print("\n" + "=" * 60 + "\nDOKPLOY COMPOSE AUTOMATION COMPLETE!\n" + "=" * 60)
