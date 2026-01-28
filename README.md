# Azure-Dockploy 🚀

This project provides a **one-click, hardened automation** to deploy a production-ready Dokploy environment on Azure. It handles everything from infrastructure provisioning to application deployment, secret injection, and security configuration.

## ✨ Features

- **One-Click Rebuild**: Infrastructure and applications can be fully destroyed and rebuilt in minutes via Terraform and Python.
- **Hardened Automation**: `dokploy_automate.py` includes robust retry logic, exponential backoff, and extensive debug logging.
- **Secret Management**: Automatic detection and injection of `.env` files into Dokploy containers.
- **Persistent Storage**: Configured with persistent Azure managed disks for Dokploy and Docker data.
- **Dynamic Routing**: Automated Traefik configuration and domain setup (including direct port exposure for immediate access).

## 🏗️ Infrastructure

- **Cloud Provider**: Microsoft Azure
- **Compute**: Ubuntu 22.04 LTS (Standard_B2s)
- **Networking**: NSG allowed ports: 22 (SSH), 80 (HTTP), 443 (HTTPS), 3000 (Dokploy), **9000 (App Port)**.
- **Storage**: Persistent StandardSSD_LRS Managed Disk.

## 🛠️ Getting Started

### Prerequisites

- Terraform
- Python 3.x
- Azure Service Principal with Contributor access.

### 1. Configuration

1. **Credentials**: Add your Azure details to `terraform.tfvars`.
2. **Applications**: Configure your GitHub repositories and domains in `automation/dokploy_config.json`.
3. **Secrets**: Place `.env_<app-name>` files in the root or `automation/` folder; the script will find and inject them automatically.

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

A dedicated script `automation/godaddy_dns.py` is included to manage your GoDaddy DNS records automatically.

### DNS Prerequisites

1. Generate an API Key and Secret at [developer.godaddy.com](https://developer.godaddy.com/keys).
2. Set them as environment variables:

   ```bash
   export GODADDY_API_KEY="your_key"
   export GODADDY_API_SECRET="your_secret"
   ```

### Usage

```bash
# Set an A record for lakera.alshawwaf.ca
python automation/godaddy_dns.py --domain alshawwaf.ca --subdomain lakera --ip 20.151.202.86 --set

# Remove the A record
python automation/godaddy_dns.py --domain alshawwaf.ca --subdomain lakera --remove
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
- **Secrets Protection**: The `.gitignore` is pre-configured to prevent `.env` files and `terraform.tfvars` from being pushed to version control.

## Credits

Developed with Antigravity 🛸
