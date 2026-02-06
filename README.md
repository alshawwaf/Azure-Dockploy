# Azure-Dockploy

A **production-ready, one-click automation** to deploy [Dokploy](https://dokploy.com/) on Azure with full application orchestration. This project handles everything from infrastructure provisioning to application deployment, secret injection, SSL certificates, and Traefik routing.

## Features

- **One-Click Deployment**: Infrastructure and applications fully deployed via Terraform + Python automation
- **Hardened Automation**: Robust retry logic, exponential backoff, and extensive debug logging
- **Cross-Platform**: Works on macOS, Windows, and Linux
- **Smart Secret Management**: Automatic `.env` file injection with keyword-based matching
- **Clean Rebuild Mode**: `--clean` flag resets everything for fresh deployments
- **Persistent Storage**: Azure managed disks for Docker data persistence
- **Dynamic Routing**: Automated Traefik configuration with Let's Encrypt SSL
- **Multi-Domain Support**: Deploy multiple services with custom subdomains

## Infrastructure

| Component | Specification |
|-----------|---------------|
| **Cloud** | Microsoft Azure |
| **OS** | Ubuntu 22.04 LTS |
| **VM Size** | Standard_B4ms (4 vCPU, 16GB RAM) |
| **Storage** | 128GB StandardSSD managed disk |
| **Ports** | 22, 80, 443, 3000, 5678, 9000+ |

## Included Services

| Service | Description | Example Domain |
|---------|-------------|----------------|
| **AI Dev-Hub** | Central management dashboard | `hub.example.com` |
| **Training Portal** | Hands-on learning platform | `training.example.com` |
| **Lakera Demo** | LLM guardrails testing | `lakera.example.com` |
| **Agentic Playground** | n8n, Ollama, Open WebUI, Flowise, Langflow | `workflow.example.com` |
| **Docs-to-Swagger** | API docs to OpenAPI conversion | `swagger.example.com` |

## Quick Start

### Prerequisites

- [Terraform](https://terraform.io/) >= 1.0
- Python 3.8+
- Azure CLI (for creating Service Principal)
- Azure subscription with Contributor access

### 1. Clone & Configure

```bash
git clone https://github.com/alshawwaf/Azure-Dockploy.git
cd Azure-Dockploy

# Copy example files
cp terraform.tfvars.example terraform.tfvars
cp automation/envs/.env_*.example automation/envs/  # Remove .example suffix
```

### 2. Create Azure Service Principal

```bash
az login
az ad sp create-for-rbac --name "dokploy-sp" --role Contributor \
  --scopes /subscriptions/<YOUR_SUBSCRIPTION_ID>
```

Copy the output values to `terraform.tfvars`:
- `appId` → `client_id`
- `password` → `client_secret`
- `tenant` → `tenant_id`

### 3. Configure Variables

Edit `terraform.tfvars` with your Azure credentials:

```hcl
subscription_id        = "your-subscription-id"
client_id              = "your-client-id"
client_secret          = "your-client-secret"
tenant_id              = "your-tenant-id"
dokploy_admin_password = "YourSecurePassword123!"
enable_dokploy_setup   = true
```

### 4. Configure Applications

Edit `automation/dokploy_config.json` to define your applications:

```json
{
  "name": "My App",
  "repo": "https://github.com/username/repo",
  "service": "app",
  "exposures": [
    {"domain": "app.example.com", "port": 3000}
  ]
}
```

### 5. Add Secrets (Optional)

Place environment files in `automation/envs/`:
- `.env_agentic` → matches "CP Agentic MCP Playground"
- `.env_lakera-demo` → matches "Lakera Demo"
- `.env_training-portal` → matches "Training Portal"
- `.env_dev-hub` → matches "Dev Hub"

### 6. Deploy

```bash
terraform init
terraform apply -auto-approve
```

The automation will:
1. Create Azure VM with managed disk
2. Install Docker & Dokploy
3. Deploy all configured applications
4. Configure Traefik routing & SSL
5. Inject environment secrets

## 🔧 Manual Operations

### Re-run Automation Only

```bash
# Incremental update
python automation/dokploy_automate.py \
  --url http://<PUBLIC_IP>:3000 \
  --email admin@example.com \
  --password "PASSWORD" \
  --ip <PUBLIC_IP>

# Clean rebuild (deletes all apps, resets SSH keys)
python automation/dokploy_automate.py \
  --url http://<PUBLIC_IP>:3000 \
  --email admin@example.com \
  --password "PASSWORD" \
  --ip <PUBLIC_IP> \
  --clean
```

### Troubleshooting

**Container name conflicts:**
```bash
ssh -i ~/.ssh/id_rsa adminuser@<PUBLIC_IP> \
  "sudo docker stop \$(sudo docker ps -aq); sudo docker rm \$(sudo docker ps -aq)"
```

**Check deployment status:**
```bash
python automation/verify_deployment.py \
  --url http://<PUBLIC_IP>:3000 \
  --email admin@example.com \
  --password "PASSWORD"
```

## DNS Configuration

After deployment, configure your DNS provider to point your domains to the VM's public IP address.

**Required DNS Records (A Records):**
```
hub.example.com      → <PUBLIC_IP>
training.example.com → <PUBLIC_IP>
lakera.example.com   → <PUBLIC_IP>
workflow.example.com → <PUBLIC_IP>
chat.example.com     → <PUBLIC_IP>
flowise.example.com  → <PUBLIC_IP>
langflow.example.com → <PUBLIC_IP>
swagger.example.com  → <PUBLIC_IP>
```

Traefik will automatically provision SSL certificates via Let's Encrypt once DNS is configured.

## Security Notes

 **Important**: The following files contain sensitive data and are excluded from Git:

- `terraform.tfvars` - Azure credentials
- `automation/envs/.env_*` - Application secrets
- `*.tfstate` - Terraform state (contains resource IDs)

**Never commit these files to version control!**

Use the provided `.example` files as templates.

## Project Structure

```
Azure-Dockploy/
├── main.tf                     # Terraform infrastructure
├── variables.tf                # Variable declarations
├── outputs.tf                  # Terraform outputs
├── terraform.tfvars.example    # Example credentials (safe to commit)
├── .gitignore                  # Excludes sensitive files
├── automation/
│   ├── dokploy_automate.py     # Main deployment script
│   ├── dokploy_config.json     # Application definitions
│   ├── verify_deployment.py    # Health checks
│   ├── seed_expanded.py        # Database seeder
│   └── envs/
│       ├── .env_*.example      # Example env files (safe to commit)
│       └── .env_*              # Real secrets (gitignored)
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Never commit real credentials
4. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details.
