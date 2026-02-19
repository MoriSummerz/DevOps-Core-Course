terraform {
  required_version = ">= 1.9.0"

  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = "0.187.0"
    }
  }
}

provider "yandex" {
  service_account_key_file = "sa.json"
  cloud_id                 = var.cloud_id
  folder_id                = var.folder_id
  zone                     = var.zone
}

# Network
resource "yandex_vpc_network" "lab4" {
  name = "lab4-network"
}

resource "yandex_vpc_subnet" "lab4" {
  name           = "lab4-subnet"
  zone           = var.zone
  network_id     = yandex_vpc_network.lab4.id
  v4_cidr_blocks = var.subnet_cidr
}

# Security Group
resource "yandex_vpc_security_group" "lab4" {
  name       = "lab4-sg"
  network_id = yandex_vpc_network.lab4.id

  ingress {
    description    = "Allow SSH"
    protocol       = "TCP"
    port           = 22
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description    = "Allow HTTP"
    protocol       = "TCP"
    port           = 80
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description    = "Allow app port"
    protocol       = "TCP"
    port           = 5000
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description    = "Allow all outbound"
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

# Boot Disk
resource "yandex_compute_disk" "boot" {
  name     = "lab4-boot-disk"
  zone     = var.zone
  size     = var.disk_size
  image_id = var.image_id
}

# Compute Instance
resource "yandex_compute_instance" "default" {
  name        = var.vm_name
  platform_id = var.platform_id
  zone        = var.zone

  resources {
    cores         = var.cores
    memory        = var.memory
    core_fraction = var.core_fraction
  }

  boot_disk {
    disk_id = yandex_compute_disk.boot.id
  }

  network_interface {
    subnet_id          = yandex_vpc_subnet.lab4.id
    nat                = true
    security_group_ids = [yandex_vpc_security_group.lab4.id]
  }

  metadata = {
    ssh-keys = "ubuntu:${file(var.ssh_key_path)}"
  }

  labels = {
    project = "devops-course"
    lab     = "lab4"
  }
}
