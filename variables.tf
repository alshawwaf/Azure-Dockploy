variable "resource_group_name" {
  type    = string
  default = "dokploy-rg-20260126-2310"
}

variable "naming_suffix" {
  type    = string
  default = "20260126-2310"
}

variable "location" {
  type    = string
  default = "Canada Central"
}

variable "subscription_id" {
  type      = string
  sensitive = true
}

variable "client_id" {
  type      = string
  sensitive = true
}

variable "client_secret" {
  type      = string
  sensitive = true
}

variable "tenant_id" {
  type      = string
  sensitive = true
}

variable "vm_size" {
  type        = string
  description = "Size of the virtual machine"
  default     = "Standard_B4ms" # 4 vCPUs, 16GB RAM (Guaranteed capacity)
}

variable "admin_username" {
  type        = string
  description = "Admin username for the VM"
  default     = "adminuser"
}

variable "admin_ssh_key" {
  type        = string
  description = "SSH public key for the VM (optional, will use ~/.ssh/id_rsa.pub if empty)"
  default     = ""
}

variable "data_disk_size" {
  type        = number
  description = "Size of the persistent data disk in GB"
  default     = 64
}

variable "dokploy_admin_email" {
  type    = string
  default = "admin@alshawwaf.ca"
}

variable "dokploy_admin_password" {
  type      = string
  sensitive = true
}

variable "enable_dokploy_setup" {
  type        = bool
  description = "Whether to run the Dokploy automation script"
  default     = true
}

