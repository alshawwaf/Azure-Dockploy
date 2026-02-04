# Azure-Dockploy 🚀

This project provides a **one-click, hardened automation** to deploy a production-ready Dokploy environment on Azure. It handles everything from infrastructure provisioning to application deployment, secret injection, and security configuration.

## ✨ Features

- **One-Click Rebuild**: Infrastructure and applications can be fully destroyed and rebuilt in minutes via Terraform and Python.
- **Hardened Automation**: `dokploy_automate.py` includes robust retry logic, exponential backoff, and extensive debug logging.
- **Secret Management**: Automatic detection and injection of `.env` files into Dokploy containers.
- **Persistent Storage**: Configured with persistent Azure managed disks for Dokploy and Docker data.
- **Dynamic Routing**: Automated Traefik configuration and domain setup supporting multiple subdomains (e.g., `hub`, `lakera`, `training`, `n8n`, `swagger`).

## 🏗️ Infrastructure

- **Cloud Provider**: Microsoft Azure
- **Compute**: Ubuntu 22.04 LTS (Standard_B2s)
- **Networking**: NSG allowed ports: 22 (SSH), 80 (HTTP), 443 (HTTPS), 3000 (Dokploy), **9000 (App Port)**.
- **Storage**: Persistent StandardSSD_LRS Managed Disk.

## 🏢 Services

| Service | Description | Repository |
| :--- | :--- | :--- |
| **AI Dev-Hub** | Central management dashboard for all playground applications. | [dev-hub](https://github.com/alshawwaf/dev-hub) |
| **Training Portal** | Enterprise blueprint for virtualized hands-on learning. | [training-portal](https://github.com/alshawwaf/training-portal) |
| **Lakera Demo** | Interactive playground for testing LLM guardrails. | [Lakera-Demo](https://github.com/alshawwaf/Lakera-Demo) |
| **n8n Automation** | Workflow automation tool for linking LLMs and services. | [cp-agentic-mcp-playground](https://github.com/alshawwaf/cp-agentic-mcp-playground) |
| **Docs-to-Swagger** | Automated conversion of documentation to OpenAPI/Swagger specifications. | [cp-docs-to-swagger](https://github.com/alshawwaf/cp-docs-to-swagger) |

## 🛠️ Getting Started

### Prerequisites

- Terraform
- Python 3.x
- Azure Service Principal with Contributor access.

### 1. Configuration

1. **Credentials**: Add your Azure details to `terraform.tfvars`.
2. **Applications**: Configure your GitHub repositories and domains in `automation/dokploy_config.json`. Supports multi-domain deployments!

    ```json
    {
      "name": "My App",
      "repo": "https://github.com/...",
      "service": "app",
      "exposures": [
        {"domain": "app.example.com", "port": 3000},
        {"domain": "api.example.com", "port": 8080}
      ]
    }

    ```
3. **Secrets**: Place `.env_<app-name>` files in the root or `automation/` folder; the script will find and inject them automatically.
4. **Seeding**: For the Dev-Hub, run `python automation/seed_expanded.py` within the backend container to populate the application list.

### 2. Deployment (One-Click)

To build the entire environment from scratch:

```bash
terraform init
terraform apply -auto-approve
```

The `terraform apply` command is integrated with the Python automation script. Once the VM is ready, it will automatically:

- Install Docker & Dokploy.
- Create your Project and Environments.
- Register your local SSH key.
- Deploy all applications defined in your config.

### 3. Manual Automation & Management

You can trigger the automation independently or perform a "Clean Rebuild" of the applications without destroying the Azure infrastructure:

```bash
# Full Application Sync/Rebuild
python automation/dokploy_automate.py --url http://<PUBLIC_IP>:3000 --email admin@example.com --password "PASSWORD" --clean
```

## 🌐 DNS Management (GoDaddy)

DNS management is now integrated directly into the Terraform lifecycle. When enabled, Terraform will automatically create/update the A record on `apply` and remove it on `destroy`.

### 1. Configuration (terraform.tfvars)

Add your GoDaddy credentials and domain settings to your `terraform.tfvars`:

```hcl
enable_godaddy_dns = true  # Toggle DNS automation (default: true)
godaddy_api_key    = "your_api_key"
godaddy_api_secret = "your_api_secret"
godaddy_domain     = "example.com"
godaddy_subdomain  = "app"
```

### 2. Manual Usage (Optional)

You can still run the script manually if needed:

```bash
python automation/godaddy_dns.py --domain example.com --subdomain app --ip <IP> --set
```

Logs are stored in `automation/godaddy_dns.log`.

## 🔍 Verification

Check the status of your deployments:

```bash
python automation/verify_deployment.py --url http://<PUBLIC_IP>:3000 --email admin@example.com --password "PASSWORD"
```

## 🔐 Security & Persistence

- **SSH Keys**: The script automatically registers your local public key in Dokploy for secure Git cloning.
- **Disk Persistence**: Docker data is symlinked to a managed disk at `/mnt/dokploy-data`, ensuring your data survives VM reboots or rebuilds.
- **Inter-Container Networking**: Applications like `Dev-Hub` and `Docs-to-Swagger` join the `dokploy-network` to enable proper Traefik routing without exposing ports.
- **Custom Branch Support**: The automation script now supports custom default branches (e.g., `master` for `Docs-to-Swagger`).
- **Secrets Protection**: The `.gitignore` is pre-configured to prevent `.env` files and `terraform.tfvars` from being pushed to version control.

## Credits

Developed with Antigravity 🛸
