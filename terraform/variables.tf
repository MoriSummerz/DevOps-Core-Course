variable "cloud_id" {
  description = "Yandex Cloud ID"
  type        = string
}

variable "folder_id" {
  description = "Yandex Cloud Folder ID"
  type        = string
}

variable "zone" {
  description = "Yandex Cloud availability zone"
  type        = string
  default     = "ru-central1-a"
}

variable "vm_name" {
  description = "Name of the compute instance"
  type        = string
  default     = "lab4-vm"
}

variable "platform_id" {
  description = "Yandex Compute platform ID"
  type        = string
  default     = "standard-v3"
}

variable "cores" {
  description = "Number of CPU cores"
  type        = number
  default     = 2
}

variable "memory" {
  description = "Memory in GB"
  type        = number
  default     = 2
}

variable "core_fraction" {
  description = "CPU core fraction (percent)"
  type        = number
  default     = 20
}

variable "disk_size" {
  description = "Boot disk size in GB"
  type        = number
  default     = 10
}

variable "image_id" {
  description = "Boot disk image ID (Ubuntu 24.04)"
  type        = string
  default     = "fd8s4a9mnca2bmgol2r8"
}

variable "ssh_key_path" {
  description = "Path to SSH public key"
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "subnet_cidr" {
  description = "CIDR block for the subnet"
  type        = list(string)
  default     = ["10.5.0.0/24"]
}