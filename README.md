# Azure-Dockploy

This project automates the deployment of an Ubuntu VM on Azure using Terraform, installs Dokploy, and prepares the environment for hosting multiple GitHub applications.

## 🚀 Overview

- **Cloud Provider**: Microsoft Azure
- **Infrastructure as Code**: Terraform
- **Hosting Platform**: [Dokploy](https://dokploy.com/)
- **Target Applications**:
  - [Lakera-Demo](https://github.com/alshawwaf/Lakera-Demo)
  - [se-training-portal](https://github.com/alshawwaf/se-training-portal)
  - [cp-agentic-mcp-playground](https://github.com/alshawwaf/cp-agentic-mcp-playground)

## 🏗️ Infrastructure

The infrastructure includes:

- **Resource Group**: `dokploy-rg`
- **Virtual Network**: `dokploy-vnet` (10.0.0.0/16)
- **Subnet**: `dokploy-subnet` (10.0.1.0/24)
- **Public IP**: `dokploy-pip`
- **Network Security Group**: `dokploy-nsg`
  - Allowed Ports: 22 (SSH), 80 (HTTP), 443 (HTTPS), 3000 (Dokploy Web UI)
- **Virtual Machine**: `dokploy-vm` (Ubuntu 22.04 LTS, Standard_B2s)

## 🛠️ Setup & Deployment

### Prerequisites

- Terraform
- Azure Service Principal (Client ID, Secret, Tenant ID, Subscription ID)

### Configuration

Credentials are managed in `terraform.tfvars` (not committed for security):

```hcl
subscription_id = "..."
client_id       = "..."
client_secret   = "..."
tenant_id       = "..."
```

### Infrastructure Deployment

```bash
terraform init
terraform apply -auto-approve
```

### Dokploy Installation

Once the VM is up, Dokploy is installed via:

```bash
curl -sSL https://dokploy.com/install.sh | sudo sh
```

Access the dashboard at `http://<PUBLIC_IP>:3000`.

## 📖 Documentation Artifacts

Detailed technical details can be found in the [brain/](.gemini/antigravity/brain/) directory:

- [Implementation Plan](.gemini/antigravity/brain/a17bde83-6f48-4464-9e8b-bf92103cd4da/implementation_plan.md)
- [Walkthrough](.gemini/antigravity/brain/a17bde83-6f48-4464-9e8b-bf92103cd4da/walkthrough.md)
- [Task Log](.gemini/antigravity/brain/a17bde83-6f48-4464-9e8b-bf92103cd4da/task.md)

---
*Created by Antigravity*
