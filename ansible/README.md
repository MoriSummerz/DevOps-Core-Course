# Ansible Infrastructure Automation

This directory contains Ansible roles and playbooks for automated infrastructure provisioning and application deployment.

## Quick Start

```bash
# Test connectivity
ansible all -m ping

# Provision infrastructure (install Docker, common packages)
ansible-playbook playbooks/provision.yml

# Deploy application
ansible-playbook playbooks/deploy.yml

# Complete setup (provision + deploy)
ansible-playbook playbooks/site.yml
```

## Structure

```
ansible/
├── inventory/hosts.ini      # VM inventory
├── group_vars/all.yml       # Encrypted variables (Ansible Vault)
├── playbooks/               # Ansible playbooks
│   ├── site.yml            # Full infrastructure + app deployment
│   ├── provision.yml       # System provisioning only
│   └── deploy.yml          # Application deployment only
└── roles/                  # Ansible roles
    ├── common/             # Essential packages and system config
    ├── docker/             # Docker installation
    └── app_deploy/         # Container deployment
```

## Roles

### common
- Updates apt cache
- Installs essential packages (git, vim, curl, htop, etc.)
- Configures timezone and locale

### docker
- Installs Docker CE and related packages
- Configures Docker service
- Adds users to docker group
- Installs python3-docker for Ansible

### app_deploy
- Logs into Docker Hub (if credentials provided)
- Pulls Docker images
- Manages container lifecycle
- Performs health checks

## Ansible Vault

Sensitive data is encrypted with Ansible Vault:

```bash
# View encrypted variables
ansible-vault view group_vars/all.yml

# Edit encrypted variables
ansible-vault edit group_vars/all.yml

# Vault password stored in .vault_pass (gitignored)
```

## Target VM

- **Host:** 130.61.249.187
- **User:** root
- **SSH Key:** ~/.ssh/oracle.key
- **OS:** Ubuntu 22.04.4 LTS (ARM64)

## Application Access

After deployment:
- **URL:** http://130.61.249.187:5000/
- **Container:** devops-app (nginx:latest)
- **Port Mapping:** 5000 (host) → 80 (container)

## Documentation

Complete documentation available in:
- **ansible/docs/LAB05.md** - Detailed lab documentation with architecture, idempotency analysis, and design decisions

## Requirements

- Ansible 2.16+
- Python 3.8+
- SSH access to target VM
- Ansible collections: community.docker

## Common Commands

```bash
# Check running containers
ansible webservers -m shell -a "docker ps"

# Verify application health
ansible webservers -m shell -a "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/"

# Check Docker version
ansible webservers -a "docker --version"

# View system facts
ansible webservers -m setup

# Run with increased verbosity
ansible-playbook playbooks/site.yml -v
```

## Idempotency

All playbooks are idempotent - running them multiple times is safe and will only make changes when needed:

```bash
# First run: changes=1 (added user to docker group)
# Second run: changes=0 (everything already in desired state)
ansible-playbook playbooks/provision.yml
```

## Security

- ✅ Vault password in `.vault_pass` (gitignored)
- ✅ Credentials encrypted with AES256
- ✅ `no_log: true` on sensitive tasks
- ✅ SSH key-based authentication
- ✅ No plaintext secrets in repository

---

**Author:** Lab 5 - Ansible Fundamentals
**Date:** 2026-02-23
