terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
  client_id       = var.client_id
  client_secret   = var.client_secret
  tenant_id       = var.tenant_id
}



resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
}

resource "azurerm_virtual_network" "vnet" {
  name                = "dokploy-vnet-${var.naming_suffix}"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_subnet" "subnet" {
  name                 = "dokploy-subnet-${var.naming_suffix}"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_public_ip" "pip" {
  name                = "dokploy-pip-${var.naming_suffix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_network_security_group" "nsg" {
  name                = "dokploy-nsg-${var.naming_suffix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  security_rule {
    name                       = "SSH"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "HTTP"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "HTTPS"
    priority                   = 120
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    # ... previous rules ...
    name                       = "App-9000"
    priority                   = 140
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "9000"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "Dokploy"
    priority                   = 150
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "3000"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_network_interface_security_group_association" "nsg_assoc" {
  network_interface_id      = azurerm_network_interface.nic.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

resource "azurerm_network_interface" "nic" {
  name                = "dokploy-nic-${var.naming_suffix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.pip.id
  }
}

resource "azurerm_managed_disk" "data" {
  name                 = "dokploy-data-disk-${var.naming_suffix}"
  location             = azurerm_resource_group.rg.location
  resource_group_name  = azurerm_resource_group.rg.name
  storage_account_type = "StandardSSD_LRS"
  create_option        = "Empty"
  disk_size_gb         = var.data_disk_size
}

resource "azurerm_virtual_machine_data_disk_attachment" "data_attach" {
  managed_disk_id    = azurerm_managed_disk.data.id
  virtual_machine_id = azurerm_linux_virtual_machine.vm.id
  lun                = "10"
  caching            = "ReadWrite"
}

resource "azurerm_linux_virtual_machine" "vm" {
  name                            = "dokploy-vm-${var.naming_suffix}"
  resource_group_name             = azurerm_resource_group.rg.name
  location                        = azurerm_resource_group.rg.location
  size                            = var.vm_size
  admin_username                  = var.admin_username
  disable_password_authentication = true

  network_interface_ids = [
    azurerm_network_interface.nic.id,
  ]

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.admin_ssh_key != "" ? var.admin_ssh_key : file("~/.ssh/id_rsa.pub")
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts"
    version   = "latest"
  }

  custom_data = base64encode(<<-EOF
    #!/bin/bash
    set -e

    # 1. Wait for data disk to be attached
    DISK_ID="/dev/disk/azure/scsi1/lun10"
    timeout=300
    elapsed=0
    while [ ! -e $DISK_ID ] && [ $elapsed -lt $timeout ]; do
      echo "Waiting for disk..."
      sleep 5
      elapsed=$((elapsed+5))
    done

    # 2. Format disk if not already formatted
    if ! blkid $DISK_ID; then
      mkfs.ext4 $DISK_ID
    fi

    # 3. Mount disk
    MOUNT_POINT="/dokploy-data"
    mkdir -p $MOUNT_POINT
    if ! grep -q "$MOUNT_POINT" /etc/fstab; then
      echo "$DISK_ID $MOUNT_POINT ext4 defaults,nofail 0 2" >> /etc/fstab
    fi
    mount -a

    # 4. Create directories on persistent disk
    mkdir -p $MOUNT_POINT/etc-dokploy
    mkdir -p $MOUNT_POINT/var-lib-docker
    mkdir -p $MOUNT_POINT/var-lib-containerd
    mkdir -p $MOUNT_POINT/root-docker

    # 5. Backup/clean existing dirs and symlink
    if [ ! -L /etc/dokploy ]; then
      systemctl stop docker || true
      systemctl stop containerd || true

      [ -d /etc/dokploy ] && mv /etc/dokploy /etc/dokploy.bak
      [ -d /var/lib/docker ] && mv /var/lib/docker /var/lib/docker.bak
      [ -d /var/lib/containerd ] && mv /var/lib/containerd /var/lib/containerd.bak
      [ -d /root/.docker ] && mv /root/.docker /root/.docker.bak
      
      ln -s $MOUNT_POINT/etc-dokploy /etc/dokploy
      ln -s $MOUNT_POINT/var-lib-docker /var/lib/docker
      ln -s $MOUNT_POINT/var-lib-containerd /var/lib/containerd
      ln -s $MOUNT_POINT/root-docker /root/.docker
    fi

    # 6. Install Docker
    if ! command -v docker &> /dev/null; then
      curl -fsSL https://get.docker.com | sh
      systemctl start docker
      systemctl enable docker
    fi

    # 7. Install Dokploy
    if ! [ -f /etc/dokploy/dokploy.sh ]; then
      curl -sSL https://dokploy.com/install.sh | sudo sh
    fi

    # 8. Install Python3 and requests for automation script
    apt-get update
    apt-get install -y python3 python3-pip
    pip3 install requests
  EOF
  )
}

resource "null_resource" "dokploy_setup" {
  count      = var.enable_dokploy_setup ? 1 : 0
  depends_on = [azurerm_linux_virtual_machine.vm, azurerm_virtual_machine_data_disk_attachment.data_attach]

  triggers = {
    vm_id            = azurerm_linux_virtual_machine.vm.id
    automation_script = filesha256("automation/dokploy_automate.py")
    automation_config = filesha256("automation/dokploy_config.json")
    # env_agentic       = filesha256("automation/.env_agentic")
    # env_dev_hub       = filesha256("automation/.env_dev-hub")
    # env_lakera        = filesha256("automation/.env_lakera-demo")
    # env_training      = filesha256("automation/.env_training-portal")
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "Waiting 90s for VM cloud-init and Dokploy startup..."
      powershell -Command "Start-Sleep -Seconds 90"
      echo "Copying automation files to VM..."
      scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa automation/dokploy_automate.py automation/dokploy_config.json ${var.admin_username}@${azurerm_public_ip.pip.ip_address}:/tmp/
      # echo "Copying env files to VM..."
      # scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa automation/.env_agentic automation/.env_lakera-demo automation/.env_training-portal automation/.env_dev-hub ${var.admin_username}@${azurerm_public_ip.pip.ip_address}:/tmp/
      echo "Running automation script on VM..."
      ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ${var.admin_username}@${azurerm_public_ip.pip.ip_address} "cd /tmp && python3 dokploy_automate.py --url http://localhost:3000 --email ${var.dokploy_admin_email} --password ${var.dokploy_admin_password} --config dokploy_config.json --ip ${azurerm_public_ip.pip.ip_address}"
    EOT
  }
}



resource "azurerm_dev_test_global_vm_shutdown_schedule" "shutdown" {
  virtual_machine_id = azurerm_linux_virtual_machine.vm.id
  location           = azurerm_resource_group.rg.location
  enabled            = true

  daily_recurrence_time = "1900"                  # 7:00 PM
  timezone              = "Eastern Standard Time" # Adjust as needed

  notification_settings {
    enabled = false
  }
}
