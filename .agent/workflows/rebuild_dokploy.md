---
description: Fully destroy and rebuild the Dokploy infrastructure on Azure in one click
---

This workflow completely destroys the existing environment and reapplies the Terraform configuration.
The `terraform apply` step now **automatically triggers** the python automation script (`dokploy_automate.py`) once the VM is provisioning, using the `local-exec` provisioner defined in `main.tf`.

1. Destroy Infrastructure
// turbo
terraform destroy -auto-approve

2. Build and Automate
// turbo
terraform apply -auto-approve
