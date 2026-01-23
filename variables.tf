variable "resource_group_name" {
  type    = string
  default = "dokploy-rg"
}

variable "location" {
  type    = string
  default = "East US"
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
