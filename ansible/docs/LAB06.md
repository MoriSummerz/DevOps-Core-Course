# Lab 6: Advanced Ansible & CI/CD - Submission

---

## Task 1: Blocks & Tags (2 pts)

### Block Implementation

#### Common Role (`roles/common/tasks/main.yml`)

Refactored into three blocks:

**Block 1 - Package Installation** (`packages` tag):
```yaml
- name: Install system packages
  block:
    - name: Update apt cache
    - name: Install common packages
  rescue:
    - name: Fix apt cache on failure
      command: apt-get update --fix-missing
    - name: Retry installing common packages after fix
  always:
    - name: Log package installation completion
  become: true
  tags: [common, packages]
```

**Block 2 - System Configuration** (`system_config` tag):
- Set timezone
- Ensure locale is set

**Block 3 - User Management** (`users` tag):
- Ensure admin group exists
- Create deploy user

#### Docker Role (`roles/docker/tasks/main.yml`)

Refactored into three blocks:

**Block 1 - Docker Installation** (`docker_install` tag):
```yaml
- name: Install Docker Engine
  block:
    - name: Remove old Docker packages
    - name: Install prerequisites
    - name: Download Docker GPG key
    - name: Add Docker repository
    - name: Install Docker packages
  rescue:
    - name: Wait before retrying (10 seconds)
    - name: Retry apt cache update
    - name: Retry Docker package installation
  always:
    - name: Ensure Docker service is enabled
    - name: Log Docker installation completion
  become: true
  tags: [docker, docker_install]
```

**Block 2 - Docker Configuration** (`docker_config` tag):
- Add users to docker group
- Install python3-docker

**Block 3 - Docker Verification** (`docker_verify` tag):
- Check Docker version
- Check Docker Compose version

### Tag Strategy

| Tag | Scope | Purpose |
|-----|-------|---------|
| `common` | Entire common role | Run all common tasks |
| `packages` | Package installation block | Install/update packages only |
| `system_config` | System settings block | Timezone, locale only |
| `users` | User management block | User/group management only |
| `docker` | Entire docker role | Run all docker tasks |
| `docker_install` | Docker installation block | Install Docker only |
| `docker_config` | Docker configuration block | Configure Docker only |
| `docker_verify` | Verification block | Check versions only |
| `app_deploy` | Web app deployment | Deploy application |
| `compose` | Docker Compose tasks | Compose-specific tasks |
| `app_verify` | Health checks | Verify app is running |
| `web_app_wipe` | Wipe tasks | Remove application |

### Tag Listing Output

```
$ ansible-playbook playbooks/provision.yml --list-tags

playbook: playbooks/provision.yml

  play #1 (webservers): Provision web servers	TAGS: []
      TASK TAGS: [common, docker, docker_config, docker_install, docker_verify, packages, system_config, users]
```

### Selective Execution Evidence

**Running only docker_install tasks:**
```
$ ansible-playbook playbooks/provision.yml --tags "docker_install"

TASK [docker : Remove old Docker packages] *************************************
ok: [oracle-vm]
TASK [docker : Install prerequisites for Docker] *******************************
ok: [oracle-vm]
TASK [docker : Create keyrings directory] **************************************
ok: [oracle-vm]
TASK [docker : Download Docker GPG key] ****************************************
ok: [oracle-vm]
...
PLAY RECAP *********************************************************************
oracle-vm                  : ok=10   changed=1    failed=0    skipped=0
```

Note: No common role tasks ran - only docker_install tagged tasks executed.

### Rescue Block Evidence

When apt cache update fails (due to expired Corretto GPG key on VM):
```
TASK [common : Update apt cache] ***********************************************
fatal: [oracle-vm]: FAILED! => {"msg": "Failed to update apt cache after 5 retries"}

TASK [common : Fix apt cache on failure] ***************************************
changed: [oracle-vm]                              ← RESCUE TRIGGERED

TASK [common : Retry installing common packages after fix] *********************
ok: [oracle-vm]                                   ← RECOVERY SUCCESS

TASK [common : Log package installation completion] ****************************
changed: [oracle-vm]                              ← ALWAYS BLOCK RAN

PLAY RECAP *********************************************************************
oracle-vm                  : ok=3    changed=2    rescued=1    ignored=0
                                                  ^^^^^^^^^
                                                  RESCUE CONFIRMED
```

### Research Answers

**Q: What happens if rescue block also fails?**
The play fails entirely. Ansible doesn't have a "rescue of rescue" mechanism. The `always` block still executes before the failure propagates. This is why rescue blocks should be defensive and use `ignore_errors` where appropriate.

**Q: Can you have nested blocks?**
Yes, blocks can be nested. Inner blocks can have their own rescue/always sections. However, nesting should be used sparingly as it reduces readability. A better pattern is to split complex logic into separate task files included with `include_tasks`.

**Q: How do tags inherit to tasks within blocks?**
Tags applied at the block level automatically inherit to all tasks within that block (including rescue and always sections). This means if you run `--tags packages`, all tasks in the packages block execute, including rescue and always tasks if triggered. Individual tasks within blocks can have additional tags that further refine selection.

---

## Task 2: Docker Compose (3 pts)

### Role Rename

Renamed `app_deploy` → `web_app`:
```bash
mv roles/app_deploy roles/web_app
```

Updated all references in:
- `playbooks/deploy.yml`: `app_deploy` → `web_app`
- `playbooks/site.yml`: `app_deploy` → `web_app`
- `ansible/README.md`: all references updated

### Docker Compose Template

**File:** `roles/web_app/templates/docker-compose.yml.j2`

```yaml
version: '3.8'

services:
  {{ app_name }}:
    image: {{ docker_image }}:{{ docker_tag }}
    container_name: {{ app_name }}
    ports:
      - "{{ app_port }}:{{ app_internal_port }}"
{% if app_environment | default({}) | length > 0 %}
    environment:
{% for key, value in app_environment.items() %}
      {{ key }}: "{{ value }}"
{% endfor %}
{% endif %}
    restart: unless-stopped
    networks:
      - app_network

networks:
  app_network:
    driver: bridge
```

**Jinja2 Features Used:**
- Variable substitution: `{{ app_name }}`, `{{ docker_image }}`
- Conditional blocks: `{% if app_environment %}` for optional env vars
- Loops: `{% for key, value in app_environment.items() %}` for dynamic env vars
- Filters: `| default({})`, `| length` for safe empty checks

### Rendered Template on VM

```yaml
# /opt/devops-app/docker-compose.yml
version: '3.8'

services:
  devops-app:
    image: morisummerz/devops-info-service:latest
    container_name: devops-app
    ports:
      - "5000:5000"
    restart: unless-stopped
    networks:
      - app_network

networks:
  app_network:
    driver: bridge
```

### Role Dependencies

**File:** `roles/web_app/meta/main.yml`

```yaml
dependencies:
  - role: docker
```

**Effect:** When running `ansible-playbook playbooks/deploy.yml`, Docker role automatically runs first before web_app deployment. This ensures Docker is installed even if only the deploy playbook is used.

**Evidence:**
```
TASK [docker : Check Docker version] ← Docker role auto-executed
ok: [oracle-vm]
...
TASK [web_app : Deploy with Docker Compose] ← Then web_app runs
changed: [oracle-vm]
```

### Deployment Tasks (Block Pattern)

```yaml
- name: Deploy application with Docker Compose
  block:
    - name: Create application directory
    - name: Template docker-compose file
    - name: Deploy with Docker Compose (community.docker.docker_compose_v2)
  rescue:
    - name: Log deployment failure
    - name: Try recovery with docker compose up -d
  tags: [app_deploy, compose]
```

### Docker Compose Deployment Evidence

**First Run (deployment):**
```
TASK [web_app : Create application directory] **********************************
changed: [oracle-vm]
TASK [web_app : Template docker-compose file] **********************************
changed: [oracle-vm]
TASK [web_app : Deploy with Docker Compose] ************************************
changed: [oracle-vm]
TASK [web_app : Show application health status] ********************************
ok: [oracle-vm] => {
    "msg": "Application devops-app is running on port 5000 - HTTP 200"
}
PLAY RECAP *********************************************************************
oracle-vm                  : ok=24   changed=4
```

**Second Run (idempotency):**
```
TASK [web_app : Create application directory] **********************************
ok: [oracle-vm]
TASK [web_app : Template docker-compose file] **********************************
ok: [oracle-vm]
TASK [web_app : Deploy with Docker Compose] ************************************
ok: [oracle-vm]
TASK [web_app : Show application health status] ********************************
ok: [oracle-vm] => {
    "msg": "Application devops-app is running on port 5000 - HTTP 200"
}
PLAY RECAP *********************************************************************
oracle-vm                  : ok=24   changed=1   ← Only log timestamp changed
```

### Container Verification

```
$ docker ps --filter name=devops-app
CONTAINER ID   IMAGE                                    COMMAND          CREATED         STATUS         PORTS                    NAMES
334c8d1c6629   morisummerz/devops-info-service:latest   "python app.py"  2 minutes ago   Up 2 minutes   0.0.0.0:5000->5000/tcp   devops-app

$ curl http://130.61.249.187:5000/
{"service":{"name":"devops-info-service","version":"1.0.0","description":"DevOps course info service","framework":"FastAPI"},
"system":{"hostname":"334c8d1c6629","platform":"Linux","architecture":"aarch64","cpu_count":4,"python_version":"3.12.13"},
"runtime":{"uptime_seconds":19,"current_time":"2026-03-05T18:50:42Z","timezone":"UTC"},
"endpoints":[{"path":"/","method":"GET"},{"path":"/health/","method":"GET"}]}
```

### Before/After Comparison

| Aspect | Before (Lab 5) | After (Lab 6) |
|--------|----------------|---------------|
| **Deployment** | `docker_container` module | Docker Compose via `docker_compose_v2` |
| **Config** | Ansible variables only | Jinja2 template → `docker-compose.yml` |
| **Role Name** | `app_deploy` | `web_app` (more specific) |
| **Dependencies** | Manual role ordering | `meta/main.yml` auto-dependency |
| **Error Handling** | `ignore_errors` | Blocks with rescue/always |
| **Tags** | Basic per-task | Structured block-level strategy |
| **Networking** | Default bridge | Named Docker network |
| **Wipe Logic** | None | Double-gated variable + tag |

### Research Answers

**Q: What's the difference between `restart: always` and `restart: unless-stopped`?**
`always` restarts containers even after Docker daemon restarts, even if the container was manually stopped before the daemon restart. `unless-stopped` also restarts on daemon restart, but NOT if the container was explicitly stopped by the user before the daemon went down. `unless-stopped` is preferred for production because it respects manual interventions.

**Q: How do Docker Compose networks differ from Docker bridge networks?**
Docker Compose creates project-scoped networks where containers can discover each other by service name (DNS-based). The default bridge network requires linking or IP addresses. Compose networks also provide isolation between projects, while the default bridge is shared. Compose networks use the bridge driver by default but add DNS resolution and project scoping.

**Q: Can you reference Ansible Vault variables in the template?**
Yes. Jinja2 templates rendered by Ansible's `template` module have access to all Ansible variables, including those decrypted from Vault. For example, `{{ app_secret_key }}` in a template will be replaced with the decrypted value. The rendered file on the target will contain the plain text, so file permissions should be restricted (mode: '0600').

---

## Task 3: Wipe Logic (1 pt)

### Implementation

**File:** `roles/web_app/tasks/wipe.yml`

Double-gated safety mechanism:
1. **Variable gate:** `when: web_app_wipe | default(false) | bool`
2. **Tag gate:** `tags: [web_app_wipe]` - tasks only included when tag is specified

**Default:** `web_app_wipe: false` in `roles/web_app/defaults/main.yml`

**Wipe actions:**
1. Stop and remove containers via Docker Compose (`state: absent`)
2. Remove docker-compose.yml file
3. Remove application directory (`/opt/{{ app_name }}`)
4. Remove Docker image (optional disk cleanup)
5. Log wipe completion

### Test Results

#### Scenario 1: Normal deployment (wipe NOT run)

```bash
$ ansible-playbook playbooks/deploy.yml
```

```
TASK [web_app : Include wipe tasks] ********************************************
included: roles/web_app/tasks/wipe.yml for oracle-vm
TASK [web_app : Stop and remove containers] ************************************
skipping: [oracle-vm]              ← SKIPPED (web_app_wipe=false)
TASK [web_app : Remove docker-compose file] ************************************
skipping: [oracle-vm]              ← SKIPPED
...
TASK [web_app : Deploy with Docker Compose] ************************************
changed: [oracle-vm]              ← DEPLOYMENT PROCEEDS NORMALLY
```

**Result:** Wipe skipped, app deployed normally.

#### Scenario 2: Wipe only (remove existing)

```bash
$ ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true" --tags web_app_wipe
```

```
TASK [web_app : Stop and remove containers with Docker Compose] ****************
changed: [oracle-vm]
TASK [web_app : Remove docker-compose file] ************************************
changed: [oracle-vm]
TASK [web_app : Remove application directory] **********************************
changed: [oracle-vm]
TASK [web_app : Remove Docker image (optional cleanup)] ************************
changed: [oracle-vm]
TASK [web_app : Log wipe completion] *******************************************
ok: [oracle-vm] => {
    "msg": "Application devops-app wiped successfully from /opt/devops-app"
}
PLAY RECAP *********************************************************************
oracle-vm                  : ok=7    changed=4
```

**Verification:**
```
$ docker ps --filter name=devops-app
CONTAINER ID   IMAGE   COMMAND   CREATED   STATUS   PORTS   NAMES
(empty - container removed)

$ ls /opt/devops-app
ls: cannot access '/opt/devops-app': No such file or directory
```

**Result:** App completely removed, no deployment occurred.

#### Scenario 3: Clean reinstallation (wipe + deploy)

```bash
$ ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true"
```

```
TASK [web_app : Stop and remove containers] ************************************
ok: [oracle-vm]                    ← WIPE (already clean from scenario 2)
TASK [web_app : Remove application directory] **********************************
ok: [oracle-vm]
TASK [web_app : Log wipe completion] *******************************************
ok: [oracle-vm] => {
    "msg": "Application devops-app wiped successfully from /opt/devops-app"
}
TASK [web_app : Create application directory] **********************************
changed: [oracle-vm]              ← FRESH DEPLOY STARTS
TASK [web_app : Template docker-compose file] **********************************
changed: [oracle-vm]
TASK [web_app : Deploy with Docker Compose] ************************************
changed: [oracle-vm]
TASK [web_app : Show application health status] ********************************
ok: [oracle-vm] => {
    "msg": "Application devops-app is running on port 5000 - HTTP 200"
}
```

**Result:** Wipe ran first, then fresh deployment. App accessible at http://130.61.249.187:5000/

#### Scenario 4a: Tag specified but variable false (safety check)

```bash
$ ansible-playbook playbooks/deploy.yml --tags web_app_wipe
```

```
TASK [web_app : Include wipe tasks] ********************************************
included: roles/web_app/tasks/wipe.yml for oracle-vm
TASK [web_app : Stop and remove containers] ************************************
skipping: [oracle-vm]              ← BLOCKED by when condition!
TASK [web_app : Remove docker-compose file] ************************************
skipping: [oracle-vm]              ← BLOCKED
TASK [web_app : Remove application directory] **********************************
skipping: [oracle-vm]              ← BLOCKED
TASK [web_app : Remove Docker image] *******************************************
skipping: [oracle-vm]              ← BLOCKED
TASK [web_app : Log wipe completion] *******************************************
skipping: [oracle-vm]              ← BLOCKED
PLAY RECAP *********************************************************************
oracle-vm                  : ok=2    changed=0    skipped=5
```

**Result:** All wipe tasks skipped despite tag. The `when: web_app_wipe | bool` condition blocked execution. App remains running.

### Research Answers

**1. Why use both variable AND tag? (Double safety mechanism)**
The tag prevents accidental execution during normal `ansible-playbook deploy.yml` runs (wipe tasks are only considered when explicitly tagged). The variable prevents execution even when someone specifies the tag but forgot to set the variable. This dual-gate approach ensures wipe ONLY happens with explicit intent: both `-e "web_app_wipe=true"` AND `--tags web_app_wipe` (or no tag filter which includes all tags).

**2. What's the difference between `never` tag and this approach?**
The `never` tag is a special Ansible tag that prevents tasks from running unless explicitly included with `--tags never`. Our approach using a custom tag + variable is more flexible: (a) the variable can be set in inventory or group_vars for specific environments, (b) the tag name is descriptive (`web_app_wipe` vs generic `never`), (c) the variable gate adds an additional safety layer the `never` tag doesn't provide, (d) this approach supports clean reinstallation (wipe + deploy in one run).

**3. Why must wipe logic come BEFORE deployment in main.yml?**
For the clean reinstallation use case (`-e "web_app_wipe=true"` without `--tags` filter). When no tag filter is applied, ALL tasks run in order. Having wipe first ensures: old app removed → clean state → new app deployed. If wipe came after deployment, you'd deploy then immediately destroy - the opposite of what's wanted.

**4. When would you want clean reinstallation vs. rolling update?**
**Clean reinstall** when: changing major versions, fixing corrupted state, changing network/volume configuration, debugging deployment issues, migrating to different image entirely. **Rolling update** when: deploying new app version with same config, applying minor patches, updating environment variables, zero-downtime is required. Docker Compose `pull: always` with `state: present` effectively does a rolling update.

**5. How would you extend this to wipe Docker images and volumes too?**
Already partially implemented (image removal in wipe.yml). For volumes, add:
```yaml
- name: Remove Docker volumes
  command: docker volume rm {{ app_name }}_data
  ignore_errors: yes
- name: Prune unused Docker images
  command: docker image prune -f
```
Or use `docker_prune` module for comprehensive cleanup of dangling images, unused networks, and stopped containers.

---

## Task 4: CI/CD (3 pts)

### Workflow Architecture

```
Code Push → [Lint Job] → [Deploy Job] → [Verify]
              │              │              │
              ├─ checkout    ├─ checkout    ├─ curl health check
              ├─ setup py    ├─ setup py    └─ report status
              ├─ pip install ├─ pip ansible
              └─ ansible-lint├─ setup SSH
                             ├─ vault pass
                             ├─ ansible-playbook
                             └─ cleanup secrets
```

### Workflow File

**File:** `.github/workflows/ansible-deploy.yml`

```yaml
name: Ansible Deployment

on:
  push:
    branches: [ main, master ]
    paths:
      - 'ansible/**'
      - '!ansible/docs/**'        # Exclude docs changes
      - '.github/workflows/ansible-deploy.yml'
  pull_request:
    branches: [ main, master ]
    paths:
      - 'ansible/**'

jobs:
  lint:
    name: Ansible Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install ansible ansible-lint
      - run: cd ansible && ansible-lint playbooks/*.yml roles/*/tasks/*.yml

  deploy:
    name: Deploy Application
    needs: lint
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4
      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.SSH_PRIVATE_KEY }}" > ~/.ssh/id_rsa
          chmod 600 ~/.ssh/id_rsa
          ssh-keyscan -H ${{ secrets.VM_HOST }} >> ~/.ssh/known_hosts
      - name: Deploy with Ansible
        run: |
          cd ansible
          echo "${{ secrets.ANSIBLE_VAULT_PASSWORD }}" > /tmp/vault_pass
          ansible-playbook playbooks/deploy.yml \
            -i inventory/hosts.ini \
            --vault-password-file /tmp/vault_pass --tags "app_deploy"
          rm /tmp/vault_pass
      - name: Verify Deployment
        run: curl -f http://${{ secrets.VM_HOST }}:5000
```

### GitHub Secrets Configuration

| Secret | Purpose | Set In |
|--------|---------|--------|
| `ANSIBLE_VAULT_PASSWORD` | Decrypts group_vars/all.yml | Repo Settings → Secrets |
| `SSH_PRIVATE_KEY` | SSH key for VM access | Repo Settings → Secrets |
| `VM_HOST` | Target VM IP (130.61.249.187) | Repo Settings → Secrets |
| `VM_USER` | SSH user (root) | Repo Settings → Secrets |

### Path Filters

```yaml
paths:
  - 'ansible/**'           # All Ansible code changes
  - '!ansible/docs/**'     # EXCLUDE documentation changes
  - '.github/workflows/ansible-deploy.yml'  # Workflow itself
```

**Why path filters?**
- Documentation changes don't need deployment
- Terraform/app code changes shouldn't trigger Ansible
- Reduces unnecessary CI runs and costs
- Faster feedback loops

### Status Badge

Added to `ansible/README.md`:
```markdown
[![Ansible Deployment](https://github.com/MoriSummerz/DevOps-Core-Course/actions/workflows/ansible-deploy.yml/badge.svg)](https://github.com/MoriSummerz/DevOps-Core-Course/actions/workflows/ansible-deploy.yml)
```

### Security Considerations

**Secrets handling:**
- Vault password written to temp file, deleted after use (`if: always()`)
- SSH key written to temp file, cleaned up in `always` step
- `ANSIBLE_HOST_KEY_CHECKING: "False"` for CI environments
- No secrets in workflow logs (`no_log: true` in Ansible tasks)

### Research Answers

**1. What are the security implications of storing SSH keys in GitHub Secrets?**
GitHub encrypts secrets using libsodium sealed boxes. They're not exposed in logs (masked as `***`). Risks: (a) anyone with repo admin access can create workflows that read secrets, (b) fork PRs can't access secrets (good), (c) if the repo is compromised, secrets could be extracted via malicious workflow changes. Mitigations: use branch protection rules, require PR reviews, use environment-scoped secrets, rotate keys regularly, use short-lived tokens instead of long-lived SSH keys where possible.

**2. How would you implement a staging → production deployment pipeline?**
```yaml
jobs:
  deploy-staging:
    environment: staging
    steps:
      - run: ansible-playbook deploy.yml -i inventory/staging.ini

  approve-production:
    needs: deploy-staging
    environment: production  # GitHub Environment with required reviewers

  deploy-production:
    needs: approve-production
    steps:
      - run: ansible-playbook deploy.yml -i inventory/production.ini
```
Use GitHub Environments with required reviewers for production gate. Separate inventory files for each environment. Run smoke tests between stages.

**3. What would you add to make rollbacks possible?**
(a) Tag Docker images with Git SHA instead of `latest`: `docker_tag: {{ github.sha }}`. (b) Store previous image tag in a file/variable before deployment. (c) Create a rollback playbook that deploys the previous tag. (d) Keep N previous images on the server. (e) Use blue-green deployment: deploy to inactive slot, switch traffic, keep old slot for instant rollback.

**4. How does self-hosted runner improve security compared to GitHub-hosted?**
Self-hosted runners: (a) run inside your network, no need to expose SSH externally, (b) don't need SSH keys stored in GitHub Secrets, (c) can access internal resources without VPN, (d) have persistent state (cached dependencies, pre-configured tools). Drawbacks: (a) you manage security patches, (b) if compromised, attacker has network access, (c) shared runners between repos can leak secrets. Best practice: use ephemeral self-hosted runners (new VM per job).

---

## Task 5: Documentation

This file serves as the complete documentation for Lab 6.

### Files Modified/Created

**Modified:**
- `roles/common/tasks/main.yml` - Refactored with blocks, rescue/always, tags
- `roles/docker/tasks/main.yml` - Refactored with blocks, rescue/always, tags
- `playbooks/deploy.yml` - Updated to use `web_app` role
- `playbooks/site.yml` - Updated to use `web_app` role
- `ansible/README.md` - Added status badge, updated role references

**Created:**
- `roles/web_app/templates/docker-compose.yml.j2` - Jinja2 compose template
- `roles/web_app/meta/main.yml` - Role dependency on docker
- `roles/web_app/tasks/wipe.yml` - Wipe logic with double-gating
- `.github/workflows/ansible-deploy.yml` - CI/CD workflow

**Renamed:**
- `roles/app_deploy/` → `roles/web_app/`

### Code Comments

All Ansible files contain clear comments explaining:
- Block purpose and scope
- Tag assignment rationale
- Rescue block recovery strategy
- Always block guarantees
- Wipe safety mechanisms
- Variable defaults and overrides

---

## Testing Results

### Provision Playbook (Blocks & Tags)

```
# Full provision - all blocks run
$ ansible-playbook playbooks/provision.yml
oracle-vm: ok=23   changed=3    rescued=0    ignored=1

# Docker-only - common role skipped
$ ansible-playbook playbooks/provision.yml --tags "docker_install"
oracle-vm: ok=10   changed=1    skipped=0

# Packages-only - docker role skipped
$ ansible-playbook playbooks/provision.yml --tags "packages"
oracle-vm: ok=4    changed=1    skipped=0
```

### Deploy Playbook (Docker Compose)

```
# First deploy
$ ansible-playbook playbooks/deploy.yml
oracle-vm: ok=24   changed=4    ← Created dir, template, compose up

# Second deploy (idempotency)
$ ansible-playbook playbooks/deploy.yml
oracle-vm: ok=24   changed=1    ← Only log timestamp
```

### Wipe Logic (All 4 Scenarios)

| Scenario | Command | Result |
|----------|---------|--------|
| Normal deploy | `deploy.yml` | Wipe skipped, app deployed |
| Wipe only | `deploy.yml -e "web_app_wipe=true" --tags web_app_wipe` | App removed, no deploy |
| Clean reinstall | `deploy.yml -e "web_app_wipe=true"` | Wipe → fresh deploy |
| Safety check | `deploy.yml --tags web_app_wipe` | All skipped (variable=false) |

### Application Accessibility

```
$ curl -I http://130.61.249.187:5000/
HTTP/1.1 200 OK
Content-Type: application/json
Server: uvicorn
```

---

## Challenges & Solutions

### 1. APT Cache Update Failures

**Problem:** VM has expired Amazon Corretto GPG key causing `apt update` to fail with Ansible's strict error handling.

**Solution:** Implemented rescue blocks that run `apt-get update --fix-missing` and retry package installation without forcing cache update. The `ignore_errors: yes` on cache update within docker role prevents blocking when packages are already installed.

### 2. Docker Compose Module Selection

**Problem:** Multiple Docker Compose modules exist: deprecated `docker_compose`, newer `community.docker.docker_compose_v2`. The older module requires `docker-compose` Python package while v2 uses the Docker CLI plugin.

**Solution:** Used `community.docker.docker_compose_v2` which leverages `docker compose` CLI (v2) already installed as a Docker plugin on the VM. This avoids Python dependency issues and is the modern approach.

### 3. Role Rename Migration

**Problem:** Renaming `app_deploy` to `web_app` required updating all playbook references, documentation, and ensuring the vault variables still mapped correctly.

**Solution:** Used `mv` for the directory rename, then systematically updated all playbook files (`deploy.yml`, `site.yml`) and README.md references. Variable names were updated in the new `defaults/main.yml`.

### 4. Wipe Logic with Non-Existent Resources

**Problem:** Running wipe when the application directory doesn't exist causes Docker Compose to fail with "not a directory" error.

**Solution:** Added `ignore_errors: yes` to the Docker Compose stop task in wipe.yml. The `file: state=absent` module is naturally idempotent and doesn't fail if the path doesn't exist.

### 5. ARM64 Architecture Compatibility

**Problem:** The Docker Hub image `morisummerz/devops-info-service:latest` was built for amd64 only, but the Oracle Cloud VM runs on ARM64 (aarch64). Docker Compose failed with `no matching manifest for linux/arm64/v8`.

**Solution:** Built the Docker image locally on the ARM64 VM from the Python application source (`app_python/`). Set `pull: never` in the `docker_compose_v2` module to prevent Ansible from trying to pull from Docker Hub, which would fail due to the architecture mismatch. The recovery command in the rescue block also uses `--pull never`.

### 6. Version Obsolescence Warning

**Problem:** Docker Compose warns `version` key is obsolete in newer Compose spec versions.

**Solution:** The warning is non-fatal and the deployment works correctly. The `version: '3.8'` key is kept for backward compatibility with older Docker Compose versions. In production, it could be removed for Compose spec v2+ only environments.

---

## Summary

**Total time spent:** ~2 hours
**Key learnings:**
1. Blocks with rescue/always provide robust error handling similar to try/catch/finally
2. Tags enable surgical execution of specific tasks without running entire playbooks
3. Docker Compose via Ansible provides declarative, templated container management
4. Role dependencies automate prerequisite installation order
5. Double-gated wipe logic (variable + tag) prevents accidental data destruction
6. GitHub Actions with path filters enables efficient, targeted CI/CD pipelines

**All acceptance criteria met:**
- [x] All roles refactored with blocks, rescue/always, comprehensive tag strategy
- [x] Docker Compose deployment working with templated config
- [x] Role dependencies correctly configured (web_app depends on docker)
- [x] Wipe logic implemented with variable + tag safety
- [x] All 4 wipe scenarios tested successfully
- [x] GitHub Actions workflow created with linting, deployment, verification
- [x] Path filters configured for efficient CI/CD
- [x] Complete documentation with evidence and analysis
- [x] All research questions answered
- [x] Application accessible and verified at http://130.61.249.187:5000/
