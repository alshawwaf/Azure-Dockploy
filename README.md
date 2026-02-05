# Azure-Dockploy 🚀

This project provides a **one-click, hardened automation** to deploy a production-ready Dokploy environment on Azure. It handles everything from infrastructure provisioning to application deployment, secret injection, and security configuration.

## ✨ Features

- **One-Click Rebuild**: Infrastructure and applications can be fully destroyed and rebuilt in minutes via Terraform and Python.
- **Hardened Automation**: `dokploy_automate.py` includes robust retry logic, exponential backoff, and extensive debug logging.
- **Cross-Platform Support**: Works on macOS, Windows, and Linux with automatic path resolution.
- **Smart Secret Management**: Automatic detection and injection of `.env` files with keyword-based matching (e.g., `.env_agentic` matches "CP Agentic MCP Playground").
- **Clean Rebuild Mode**: The `--clean` flag resets SSH keys, removes stale servers, and ensures fresh deployments without container name conflicts.
- **Persistent Storage**: Configured with persistent Azure managed disks for Dokploy and Docker data.
- **Dynamic Routing**: Automated Traefik configuration and domain setup supporting multiple subdomains (e.g., `hub`, `lakera`, `training`, `n8n`, `swagger`).

## 🏗️ Infrastructure

- **Cloud Provider**: Microsoft Azure
- **Compute**: Ubuntu 22.04 LTS (Standard_B4ms recommended for Agentic workloads)
- **Networking**: NSG allowed ports: 22 (SSH), 80 (HTTP), 443 (HTTPS), 3000 (Dokploy), 5678 (n8n), 9000+ (App Ports).
- **Storage**: Persistent StandardSSD_LRS Managed Disk.

## 🏢 Services

| Service | Description | Domain | Repository |
| :--- | :--- | :--- | :--- |
| **AI Dev-Hub** | Central management dashboard for all playground applications. | `hub.cpdemo.ca` | [dev-hub](https://github.com/alshawwaf/dev-hub) |
| **Training Portal** | Enterprise blueprint for virtualized hands-on learning with Guacamole. | `training.cpdemo.ca` | [training-portal](https://github.com/alshawwaf/training-portal) |
| **Lakera Demo** | Interactive playground for testing LLM guardrails. | `lakera.cpdemo.ca` | [Lakera-Demo](https://github.com/alshawwaf/Lakera-Demo) |
| **CP Agentic MCP Playground** | Full-stack AI automation with n8n, Ollama, Open WebUI, Flowise & Langflow. | `n8n.cpdemo.ca`, `chat.cpdemo.ca`, `flowise.cpdemo.ca`, `langflow.cpdemo.ca` | [cp-agentic-mcp-playground](https://github.com/alshawwaf/cp-agentic-mcp-playground) |
| **Docs-to-Swagger** | Automated conversion of documentation to OpenAPI/Swagger specifications. | `swagger.cpdemo.ca` | [cp-docs-to-swagger](https://github.com/alshawwaf/cp-docs-to-swagger) |

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
3. **Secrets**: Place `.env_<app-name>` files in the `automation/envs/` folder. The script uses keyword matching:
   - `.env_agentic` → matches "CP Agentic MCP Playground"
   - `.env_lakera-demo` → matches "Lakera Demo"
   - `.env_training-portal` → matches "Training Portal"
   - `.env_dev-hub` → matches "Dev Hub"
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
# Full Application Sync (incremental update)
python automation/dokploy_automate.py --url http://<PUBLIC_IP>:3000 --email admin@example.com --password "PASSWORD" --ip <PUBLIC_IP>

# Clean Rebuild (deletes all apps, resets SSH keys, fresh deployment)
python automation/dokploy_automate.py --url http://<PUBLIC_IP>:3000 --email admin@example.com --password "PASSWORD" --ip <PUBLIC_IP> --clean
```

### 4. Troubleshooting

**Container Name Conflicts**: If you see "container name already in use" errors, SSH to the VM and clean up:
```bash
ssh -i ~/.ssh/id_rsa adminuser@<PUBLIC_IP> "sudo docker stop \$(sudo docker ps -aq); sudo docker rm \$(sudo docker ps -aq)"
```

Then re-run the automation script.

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

- **SSH Keys**: The script automatically generates and registers SSH keys in Dokploy for secure server communication. In `--clean` mode, stale keys are purged and fresh ones created.
- **Disk Persistence**: Docker data is symlinked to a managed disk at `/mnt/dokploy-data`, ensuring your data survives VM reboots or rebuilds.
- **Inter-Container Networking**: Applications join the `dokploy-network` to enable proper Traefik routing without exposing ports.
- **Custom Branch Support**: The automation script supports custom default branches (e.g., `master` for `Docs-to-Swagger`) via the `branch` config option.
- **Secrets Protection**: The `.gitignore` is pre-configured to prevent `.env` files and `terraform.tfvars` from being pushed to version control.

## 📁 Project Structure

```
Azure-Dockploy/
├── main.tf                 # Terraform infrastructure definition
├── variables.tf            # Terraform variable declarations
├── terraform.tfvars        # Your Azure credentials (gitignored)
├── outputs.tf              # Terraform outputs (public IP, etc.)
├── automation/
│   ├── dokploy_automate.py # Main deployment automation script
│   ├── dokploy_config.json # Application configuration
│   ├── godaddy_dns.py      # DNS management script
│   ├── verify_deployment.py # Deployment verification
│   ├── seed_expanded.py    # Dev-Hub database seeder
│   └── envs/               # Environment files
│       ├── .env_agentic
│       ├── .env_lakera-demo
│       ├── .env_training-portal
│       └── .env_dev-hub
└── README.md
```

## Credits

Developed with Antigravity 🛸
