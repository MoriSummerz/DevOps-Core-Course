"""Lab 4 — Yandex Cloud VM infrastructure with Pulumi."""

import os

import pulumi
import pulumi_yandex as yandex

config = pulumi.Config()

zone = config.get("zone") or "ru-central1-a"
vm_name = config.get("vmName") or "lab4-vm"
platform_id = config.get("platformId") or "standard-v3"
cores = config.get_int("cores") or 2
memory = config.get_int("memory") or 2
core_fraction = config.get_int("coreFraction") or 20
disk_size = config.get_int("diskSize") or 10
image_id = config.get("imageId") or "fd8s4a9mnca2bmgol2r8"
subnet_cidr = config.get("subnetCidr") or "10.5.0.0/24"
ssh_public_key_path = config.get("sshKeyPath") or "~/.ssh/id_ed25519.pub"

with open(os.path.expanduser(ssh_public_key_path)) as f:
    ssh_public_key = f.read().strip()

# Network
network = yandex.VpcNetwork("lab4-network", name="lab4-network")

subnet = yandex.VpcSubnet(
    "lab4-subnet",
    name="lab4-subnet",
    zone=zone,
    network_id=network.id,
    v4_cidr_blocks=[subnet_cidr],
)

# Security Group
security_group = yandex.VpcSecurityGroup(
    "lab4-sg",
    name="lab4-sg",
    network_id=network.id,
    ingresses=[
        yandex.VpcSecurityGroupIngressArgs(
            description="Allow SSH",
            protocol="TCP",
            port=22,
            v4_cidr_blocks=["0.0.0.0/0"],
        ),
        yandex.VpcSecurityGroupIngressArgs(
            description="Allow HTTP",
            protocol="TCP",
            port=80,
            v4_cidr_blocks=["0.0.0.0/0"],
        ),
        yandex.VpcSecurityGroupIngressArgs(
            description="Allow app port",
            protocol="TCP",
            port=5000,
            v4_cidr_blocks=["0.0.0.0/0"],
        ),
    ],
    egresses=[
        yandex.VpcSecurityGroupEgressArgs(
            description="Allow all outbound",
            protocol="ANY",
            v4_cidr_blocks=["0.0.0.0/0"],
        ),
    ],
)

# Boot Disk
boot_disk = yandex.ComputeDisk(
    "lab4-boot-disk",
    name="lab4-boot-disk",
    zone=zone,
    size=disk_size,
    image_id=image_id,
)

# Compute Instance
instance = yandex.ComputeInstance(
    "lab4-vm",
    name=vm_name,
    platform_id=platform_id,
    zone=zone,
    resources=yandex.ComputeInstanceResourcesArgs(
        cores=cores,
        memory=memory,
        core_fraction=core_fraction,
    ),
    boot_disk=yandex.ComputeInstanceBootDiskArgs(
        disk_id=boot_disk.id,
    ),
    network_interfaces=[
        yandex.ComputeInstanceNetworkInterfaceArgs(
            subnet_id=subnet.id,
            nat=True,
            security_group_ids=[security_group.id],
        ),
    ],
    metadata={
        "ssh-keys": f"ubuntu:{ssh_public_key}",
    },
    labels={
        "project": "devops-course",
        "lab": "lab4",
    },
)

# Outputs
pulumi.export("vm_public_ip", instance.network_interfaces[0].nat_ip_address)
pulumi.export("vm_private_ip", instance.network_interfaces[0].ip_address)
pulumi.export("vm_id", instance.id)
pulumi.export(
    "ssh_command",
    instance.network_interfaces[0].nat_ip_address.apply(
        lambda ip: f"ssh ubuntu@{ip}"
    ),
)
