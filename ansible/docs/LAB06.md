# Lab 6: Advanced Ansible & CI/CD - Submission

## Task 1: Blocks & Tags (2 pts)

### 1.1 Implementation

#### Common Role Refactoring

The `common` role was refactored to use blocks for logical grouping and error handling

**File:** [`roles/common/tasks/main.yml`](../roles/common/tasks/main.yml)

**Key Changes:**
- Package installation tasks grouped in a block with `packages` tag
- System configuration tasks grouped in a block with `config` tag
- Rescue block handles apt cache failures with `apt-get update --fix-missing`
- Always block logs completion to `/tmp/common_packages_installed.log`
- `become: true` applied at block level (DRY principle)

**Code Structure:**
```yaml
- name: Package installation block
  block:
    - name: Update apt cache
      # ...
    - name: Install common packages
      # ...
  rescue:
    - name: Handle apt cache failure - fix missing packages
      # ...
  always:
    - name: Log package installation completion
      # ...
  become: true
  tags:
    - packages
    - common
```

#### Docker Role Refactoring

The `docker` role was refactored with separate blocks for installation and configuration

**File:** [`roles/docker/tasks/main.yml`](../roles/docker/tasks/main.yml)

**Key Changes:**
- Docker installation tasks in block with `docker_install` tag
- Docker configuration tasks in block with `docker_config` tag
- Rescue block waits 10 seconds and retries on GPG key/network failure
- Always block ensures Docker service is enabled and started

**Code Structure:**
```yaml
- name: Docker installation block
  block:
    - name: Create keyrings directory
    - name: Add Docker GPG key
    - name: Install Docker packages
    # ...
  rescue:
    - name: Wait before retry on GPG key or network failure
    - name: Retry apt update after failure
    # ...
  always:
    - name: Ensure Docker service is enabled and started
  become: true
  tags:
    - docker_install
    - docker
```

### 1.2 Tag Strategy

| Tag | Scope | Description |
|-----|-------|-------------|
| `common` | Role | All common role tasks |
| `packages` | Block | Package installation only |
| `config` | Block | System configuration only |
| `docker` | Role | All docker role tasks |
| `docker_install` | Block | Docker installation only |
| `docker_config` | Block | Docker configuration only |
| `web_app` | Role | All web_app role tasks |
| `app_deploy` | Block | Application deployment |
| `compose` | Block | Docker Compose tasks |
| `web_app_wipe` | Block | Wipe logic tasks |

### 1.3 Testing Results

**List all available tags:**
```bash
$ ansible-playbook playbooks/provision.yml --list-tags

playbook: playbooks/provision.yml

  play #1 (webservers): Provision web servers	TAGS: []
      TASK TAGS: [common, config, docker, docker_config, docker_install, packages]
```

**Selective execution with --tags (docker_install only):**
```bash
$ ansible-playbook playbooks/provision.yml --tags "docker_install" --check

PLAY [Provision web servers] *****************************************************

TASK [Gathering Facts] ***********************************************************
ok: [devops-vm]

TASK [docker : Create keyrings directory] ****************************************
ok: [devops-vm]

TASK [docker : Add Docker GPG key] ***********************************************
changed: [devops-vm]

TASK [docker : Convert GPG key to binary format] *********************************
ok: [devops-vm]

TASK [docker : Set permissions on GPG key] ***************************************
ok: [devops-vm]

TASK [docker : Add Docker repository] ********************************************
ok: [devops-vm]

TASK [docker : Update apt cache after adding Docker repo] ************************
ok: [devops-vm]

TASK [docker : Install Docker packages] ******************************************
ok: [devops-vm]

TASK [docker : Ensure Docker service is enabled and started] *********************
ok: [devops-vm]

PLAY RECAP ***********************************************************************
devops-vm                  : ok=9    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

**Skip specific tags (skip common role):**
```bash
$ ansible-playbook playbooks/provision.yml --skip-tags "common" --check

PLAY [Provision web servers] *****************************************************

TASK [Gathering Facts] ***********************************************************
ok: [devops-vm]

TASK [docker : Create keyrings directory] ****************************************
ok: [devops-vm]

TASK [docker : Add Docker GPG key] ***********************************************
changed: [devops-vm]

TASK [docker : Convert GPG key to binary format] *********************************
ok: [devops-vm]

TASK [docker : Set permissions on GPG key] ***************************************
ok: [devops-vm]

TASK [docker : Add Docker repository] ********************************************
ok: [devops-vm]

TASK [docker : Update apt cache after adding Docker repo] ************************
ok: [devops-vm]

TASK [docker : Install Docker packages] ******************************************
ok: [devops-vm]

TASK [docker : Ensure Docker service is enabled and started] *********************
ok: [devops-vm]

TASK [docker : Add user to docker group] *****************************************
ok: [devops-vm]

TASK [docker : Install Python Docker package for Ansible modules] ****************
ok: [devops-vm]

TASK [docker : Log Docker configuration completion] ******************************
changed: [devops-vm]

PLAY RECAP ***********************************************************************
devops-vm                  : ok=12   changed=2    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

**Note:** Common role tasks are not shown because they were skipped with `--skip-tags "common"`

### 1.4 Research Answers

**Q: What happens if rescue block also fails?**
A: The play fails and Ansible stops execution for that host. The `always` block still runs before failure. You can add `ignore_errors: yes` to continue despite failures, or use `block` within rescue for nested error handling

**Q: Can you have nested blocks?**
A: Yes, blocks can be nested. However, it's generally not recommended as it reduces readability. Better to use separate blocks or `include_tasks` for complex logic

**Q: How do tags inherit to tasks within blocks?**
A: Tags applied to a block are inherited by all tasks within that block. Tasks can also have their own additional tags, creating a union of block tags and task tags. For example, a task inside a block with `tags: [docker]` that also has `tags: [install]` will have both tags

---

## Task 2: Docker Compose (3 pts)

### 2.1 Role Rename

The `app_deploy` role was renamed to `web_app` for better clarity and future extensibility

```bash
$ cd ansible/roles
$ mv app_deploy web_app
```

**Updated references:**
- [`playbooks/deploy.yml`](../playbooks/deploy.yml): `app_deploy` → `web_app`
- [`playbooks/site.yml`](../playbooks/site.yml): `app_deploy` → `web_app`

### 2.2 Docker Compose Template

**File:** [`roles/web_app/templates/docker-compose.yml.j2`](../roles/web_app/templates/docker-compose.yml.j2)

```yaml
version: '{{ docker_compose_version | default("3.8") }}'

services:
  {{ app_name }}:
    image: {{ docker_image }}:{{ docker_tag }}
    container_name: {{ app_name }}
    ports:
      - "{{ app_port }}:{{ app_internal_port }}"
{% if app_env_vars %}
    environment:
{% for key, value in app_env_vars.items() %}
      {{ key }}: "{{ value }}"
{% endfor %}
{% endif %}
    restart: unless-stopped
    networks:
      - {{ app_name }}_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{{ app_internal_port }}{{ health_check_path }}"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

networks:
  {{ app_name }}_network:
    driver: bridge
```

**Template Features:**
- Dynamic service name from `app_name` variable
- Configurable image and tag
- Port mapping with separate host/container ports
- Optional environment variables with Jinja2 loop
- Health check configuration
- Isolated network per application

### 2.3 Role Dependencies

**File:** [`roles/web_app/meta/main.yml`](../roles/web_app/meta/main.yml)

```yaml
dependencies:
  - role: docker
    # Docker role must run first to ensure Docker is available
```

**Why this matters:**
- Automatic dependency resolution
- No need to manually order roles in playbooks
- Running `web_app` role automatically runs `docker` first

### 2.4 Deployment Tasks

**File:** [`roles/web_app/tasks/main.yml`](../roles/web_app/tasks/main.yml)

The deployment uses `community.docker.docker_compose_v2` module:

```yaml
- name: Deploy with docker compose
  community.docker.docker_compose_v2:
    project_src: "{{ compose_project_dir }}"
    state: present
    pull: always
  register: compose_result
```

**Key Features:**
- Creates application directory
- Templates docker-compose.yml
- Logs in to Docker Hub
- Deploys with Docker Compose
- Waits for application readiness
- Verifies health endpoint
- Rescue block shows logs on failure

### 2.5 Variables Configuration

**File:** [`roles/web_app/defaults/main.yml`](../roles/web_app/defaults/main.yml)

| Variable | Default | Description |
|----------|---------|-------------|
| `app_name` | `devops-app` | Application/container name |
| `app_port` | `8000` | Host port |
| `app_internal_port` | `8000` | Container port |
| `docker_image` | `{{ dockerhub_username }}/devops-python-app` | Docker image |
| `docker_tag` | `latest` | Image tag |
| `compose_project_dir` | `/opt/{{ app_name }}` | Compose project directory |
| `docker_compose_version` | `3.8` | Compose file version |
| `health_check_path` | `/health` | Health check endpoint |
| `web_app_wipe` | `false` | Wipe control variable |

### 2.6 Testing Results

**Initial deployment:**
```bash
$ ansible-playbook playbooks/deploy.yml --ask-vault-pass

PLAY [Deploy application] ********************************************************

TASK [Gathering Facts] ***********************************************************
ok: [devops-vm]

TASK [docker : Create keyrings directory] ****************************************
ok: [devops-vm]

TASK [docker : Add Docker GPG key] ***********************************************
ok: [devops-vm]

TASK [docker : Convert GPG key to binary format] *********************************
ok: [devops-vm]

TASK [docker : Set permissions on GPG key] ***************************************
ok: [devops-vm]

TASK [docker : Add Docker repository] ********************************************
ok: [devops-vm]

TASK [docker : Update apt cache after adding Docker repo] ************************
ok: [devops-vm]

TASK [docker : Install Docker packages] ******************************************
ok: [devops-vm]

TASK [docker : Ensure Docker service is enabled and started] *********************
ok: [devops-vm]

TASK [docker : Add user to docker group] *****************************************
ok: [devops-vm]

TASK [docker : Install Python Docker package for Ansible modules] ****************
ok: [devops-vm]

TASK [docker : Log Docker configuration completion] ******************************
changed: [devops-vm]

TASK [web_app : Include wipe tasks] **********************************************
included: /Users/tovarish-dru/Downloads/DevOps-Core-Course/ansible/roles/web_app/tasks/wipe.yml for devops-vm

TASK [web_app : Check if docker-compose file exists] *****************************
skipping: [devops-vm]

TASK [web_app : Stop and remove containers with Docker Compose] ******************
skipping: [devops-vm]

TASK [web_app : Remove docker-compose file] **************************************
skipping: [devops-vm]

TASK [web_app : Remove application directory] ************************************
skipping: [devops-vm]

TASK [web_app : Log wipe completion] *********************************************
skipping: [devops-vm]

TASK [web_app : Create application directory] ************************************
changed: [devops-vm]

TASK [web_app : Template docker-compose file] ************************************
changed: [devops-vm]

TASK [web_app : Log in to Docker Hub] ********************************************
ok: [devops-vm]

TASK [web_app : Deploy with docker compose] **************************************
changed: [devops-vm]

TASK [web_app : Display deployment result] ***************************************
ok: [devops-vm] => {
    "msg": "Application devops-python-app deployed successfully using Docker Compose"
}

TASK [web_app : Wait for application to be ready] ********************************
ok: [devops-vm]

TASK [web_app : Verify health endpoint] ******************************************
ok: [devops-vm]

TASK [web_app : Display health check result] *************************************
ok: [devops-vm] => {
    "msg": "Application health check passed! Status: 200"
}

PLAY RECAP ***********************************************************************
devops-vm                  : ok=21   changed=4    unreachable=0    failed=0    skipped=5    rescued=0    ignored=0
```

**Note:** Wipe tasks show "skipping" because `web_app_wipe` is `false` by default - this is the expected behavior for normal deployment.

**Application verification:**
```bash
$ ssh dryshatu@158.160.95.154 "docker ps"
CONTAINER ID   IMAGE                                COMMAND            CREATED          STATUS                             PORTS                                         NAMES
131dd0620473   tovarishdru/devops-python-app:v1.0   "python3 app.py"   16 seconds ago   Up 15 seconds (health: starting)   0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp   devops-python-app

$ curl http://158.160.95.154:8000
{"endpoints":[{"description":"Service information","method":"GET","path":"/"},{"description":"Health check","method":"GET","path":"/health"}],"request":{"client_ip":"93.158.188.115","method":"GET","path":"/","user_agent":"curl/8.7.1"},"runtime":{"current_time":"2026-03-04T08:58:59.391712+00:00","timezone":"UTC","uptime_human":"0 hours, 0 minutes","uptime_seconds":15},"service":{"description":"DevOps course info service","framework":"Flask","name":"devops-info-service","version":"1.0.0"},"system":{"architecture":"x86_64","cpu_count":2,"hostname":"131dd0620473","platform":"Linux","platform_version":"#100-Ubuntu SMP PREEMPT_DYNAMIC Tue Jan 13 16:40:06 UTC 2026","python_version":"3.13.11"}}

$ curl http://158.160.95.154:8000/health
{"status":"healthy","timestamp":"2026-03-04T08:58:59.483055+00:00","uptime_seconds":15}
```

### 2.7 Research Answers

**Q: What's the difference between `restart: always` and `restart: unless-stopped`?**
A: 
- `always`: Container ALWAYS restarts, even if manually stopped with `docker stop`
- `unless-stopped`: Container restarts automatically UNLESS manually stopped
- `unless-stopped` is better for production as it respects manual intervention

**Q: How do Docker Compose networks differ from Docker bridge networks?**
A: Docker Compose creates isolated networks per project with automatic DNS resolution between services. Bridge networks are Docker's default, shared across all containers. Compose networks provide:
- Better isolation between projects
- Automatic service discovery (containers can reach each other by service name)
- Cleaner network management

**Q: Can you reference Ansible Vault variables in the template?**
A: Yes! Jinja2 templates have access to all Ansible variables, including Vault-encrypted ones. They're decrypted before template rendering. Example: `{{ dockerhub_password }}` in a template will use the decrypted value.

---

## Task 3: Wipe Logic (1 pt)

### 3.1 Implementation

**File:** [`roles/web_app/tasks/wipe.yml`](../roles/web_app/tasks/wipe.yml)

The wipe logic uses double-gating for safety:
1. **Variable gate:** `web_app_wipe` must be `true` (default: `false`)
2. **Tag gate:** `web_app_wipe` tag must be specified or inherited

```yaml
- name: Wipe web application
  block:
    - name: Check if docker-compose file exists
      # ...
    - name: Stop and remove containers with Docker Compose
      community.docker.docker_compose_v2:
        project_src: "{{ compose_project_dir }}"
        state: absent
        remove_orphans: true
      # ...
    - name: Remove docker-compose file
      # ...
    - name: Remove application directory
      # ...
    - name: Log wipe completion
      # ...
  when: web_app_wipe | default(false) | bool
  become: true
  tags:
    - web_app_wipe
```

**Safety Features:**
- `when` condition checks variable (default: false)
- `tags` enables selective execution
- `ignore_errors` prevents failure if already clean
- `| bool` ensures proper boolean evaluation

### 3.2 Wipe Variable Configuration

**File:** [`roles/web_app/defaults/main.yml`](../roles/web_app/defaults/main.yml)

```yaml
# Wipe Logic Control
web_app_wipe: false  # Default: do not wipe

# Usage examples:
#   Wipe only:     ansible-playbook deploy.yml -e "web_app_wipe=true" --tags web_app_wipe
#   Clean install: ansible-playbook deploy.yml -e "web_app_wipe=true"
#   Normal deploy: ansible-playbook deploy.yml (wipe tasks skipped)
```

### 3.3 Testing Results

**Scenario 1: Normal deployment (wipe should NOT run)**

See Task 2.6 above - wipe tasks show "skipping" because `web_app_wipe` is `false` by default

**Scenario 2: Wipe only**
```bash
$ ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true" --tags web_app_wipe --ask-vault-pass

PLAY [Deploy application] ********************************************************

TASK [Gathering Facts] ***********************************************************
ok: [devops-vm]

TASK [web_app : Include wipe tasks] **********************************************
included: /Users/tovarish-dru/Downloads/DevOps-Core-Course/ansible/roles/web_app/tasks/wipe.yml for devops-vm

TASK [web_app : Check if docker-compose file exists] *****************************
ok: [devops-vm]

TASK [web_app : Stop and remove containers with Docker Compose] ******************
changed: [devops-vm]

TASK [web_app : Remove docker-compose file] **************************************
changed: [devops-vm]

TASK [web_app : Remove application directory] ************************************
changed: [devops-vm]

TASK [web_app : Log wipe completion] *********************************************
ok: [devops-vm] => {
    "msg": "Application devops-python-app wiped successfully from /opt/devops-python-app"
}

PLAY RECAP ***********************************************************************
devops-vm                  : ok=7    changed=3    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

**Result:** Only wipe tasks ran, deployment tasks were skipped (because of `--tags web_app_wipe`).

**Scenario 3: Clean reinstallation (wipe → deploy)**
```bash
$ ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true" --ask-vault-pass

PLAY [Deploy application] ********************************************************

TASK [Gathering Facts] ***********************************************************
ok: [devops-vm]

TASK [docker : Create keyrings directory] ****************************************
ok: [devops-vm]

... (docker tasks) ...

TASK [docker : Log Docker configuration completion] ******************************
changed: [devops-vm]

TASK [web_app : Include wipe tasks] **********************************************
included: /Users/tovarish-dru/Downloads/DevOps-Core-Course/ansible/roles/web_app/tasks/wipe.yml for devops-vm

TASK [web_app : Check if docker-compose file exists] *****************************
ok: [devops-vm]

TASK [web_app : Stop and remove containers with Docker Compose] ******************
skipping: [devops-vm]

TASK [web_app : Remove docker-compose file] **************************************
ok: [devops-vm]

TASK [web_app : Remove application directory] ************************************
ok: [devops-vm]

TASK [web_app : Log wipe completion] *********************************************
ok: [devops-vm] => {
    "msg": "Application devops-python-app wiped successfully from /opt/devops-python-app"
}

TASK [web_app : Create application directory] ************************************
changed: [devops-vm]

TASK [web_app : Template docker-compose file] ************************************
changed: [devops-vm]

TASK [web_app : Log in to Docker Hub] ********************************************
ok: [devops-vm]

TASK [web_app : Deploy with docker compose] **************************************
changed: [devops-vm]

TASK [web_app : Display deployment result] ***************************************
ok: [devops-vm] => {
    "msg": "Application devops-python-app deployed successfully using Docker Compose"
}

TASK [web_app : Wait for application to be ready] ********************************
ok: [devops-vm]

TASK [web_app : Verify health endpoint] ******************************************
ok: [devops-vm]

TASK [web_app : Display health check result] *************************************
ok: [devops-vm] => {
    "msg": "Application health check passed! Status: 200"
}

PLAY RECAP ***********************************************************************
devops-vm                  : ok=25   changed=4    unreachable=0    failed=0    skipped=1    rescued=0    ignored=0
```

**Result:** Wipe ran first (removed old installation), then deployment ran (installed fresh)

**Scenario 4: Safety check (tag without variable)**
```bash
$ ansible-playbook playbooks/deploy.yml --tags web_app_wipe --ask-vault-pass

PLAY [Deploy application] ********************************************************

TASK [Gathering Facts] ***********************************************************
ok: [devops-vm]

TASK [web_app : Include wipe tasks] **********************************************
included: /Users/tovarish-dru/Downloads/DevOps-Core-Course/ansible/roles/web_app/tasks/wipe.yml for devops-vm

TASK [web_app : Check if docker-compose file exists] *****************************
skipping: [devops-vm]

TASK [web_app : Stop and remove containers with Docker Compose] ******************
skipping: [devops-vm]

TASK [web_app : Remove docker-compose file] **************************************
skipping: [devops-vm]

TASK [web_app : Remove application directory] ************************************
skipping: [devops-vm]

TASK [web_app : Log wipe completion] *********************************************
skipping: [devops-vm]

PLAY RECAP ***********************************************************************
devops-vm                  : ok=2    changed=0    unreachable=0    failed=0    skipped=5    rescued=0    ignored=0
```

**Result:** All wipe tasks show "skipping" because `web_app_wipe` is `false` by default. The `when: web_app_wipe | bool` condition blocked execution even though the tag was specified. This demonstrates the double-gating safety mechanism working correctly

### 3.4 Research Answers

**Q: Why use both variable AND tag?**
A: Double safety mechanism:
- **Variable** provides runtime control (can be set in inventory, group_vars, or command line)
- **Tag** provides selective execution (must be explicitly specified)
- Both must align for wipe to run, preventing accidental data loss
- Example: Running `--tags web_app_wipe` without `-e "web_app_wipe=true"` won't wipe

**Q: What's the difference between `never` tag and this approach?**
A: 
- `never` tag requires explicit `--tags never` to run (special Ansible tag)
- Our approach uses custom tag + variable, providing:
  - More flexibility (variable can be set in multiple places)
  - Clearer intent (tag name describes action)
  - Double safety (both conditions must be met)

**Q: Why must wipe logic come BEFORE deployment in main.yml?**
A: Enables clean reinstallation workflow:
1. Wipe old installation
2. Deploy new installation
If wipe came after deployment, you'd remove what you just deployed!

**Q: When would you want clean reinstallation vs. rolling update?**
A:
- **Clean reinstall:** Major version changes, corrupted state, testing from scratch, configuration changes that require fresh start
- **Rolling update:** Minor changes, zero-downtime requirements, production environments, incremental updates

**Q: How would you extend this to wipe Docker images and volumes too?**
A: Add additional tasks to wipe.yml:
```yaml
- name: Remove Docker images
  community.docker.docker_image:
    name: "{{ docker_image }}"
    state: absent
    force_absent: yes
  when: web_app_wipe_images | default(false) | bool

- name: Remove Docker volumes
  community.docker.docker_volume:
    name: "{{ app_name }}_data"
    state: absent
  when: web_app_wipe_volumes | default(false) | bool
```

---

## Task 4: CI/CD (3 pts)

### 4.1 Workflow Implementation

**File:** [`.github/workflows/ansible-deploy.yml`](../../.github/workflows/ansible-deploy.yml)

```yaml
name: Ansible Deployment

on:
  push:
    branches: [ main, master ]
    paths:
      - 'ansible/**'
      - '.github/workflows/ansible-deploy.yml'
  pull_request:
    branches: [ main, master ]
    paths:
      - 'ansible/**'
  workflow_dispatch:  # Allow manual trigger

jobs:
  lint:
    name: Ansible Lint
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
      - name: Set up Python
      - name: Install dependencies
      - name: Run ansible-lint

  deploy:
    name: Deploy Application
    needs: lint
    runs-on: ubuntu-latest
    if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'
    steps:
      - name: Checkout code
      - name: Set up Python
      - name: Install Ansible and dependencies
      - name: Setup SSH
      - name: Test SSH connection
      - name: Deploy with Ansible
      - name: Verify Deployment
```

**Workflow Features:**
- Triggers on push to ansible directory
- Path filters to avoid unnecessary runs
- Lint job runs ansible-lint
- Deploy job runs after lint passes
- SSH setup for remote deployment
- Vault password handling
- Deployment verification with curl

### 4.2 GitHub Secrets Configuration

**Required Secrets:** (Settings → Secrets and variables → Actions)

| Secret | Description |
|--------|-------------|
| `ANSIBLE_VAULT_PASSWORD` | Vault password for decryption |
| `SSH_PRIVATE_KEY` | SSH key for target VM |
| `VM_HOST` | Target VM IP (158.160.95.154) |
| `VM_USER` | SSH username (dryshatu) |

### 4.3 Status Badge

**Added to README.md:**
```markdown
[![Ansible Deployment](https://github.com/TovarishDru/DevOps-Core-Course/actions/workflows/ansible-deploy.yml/badge.svg)](https://github.com/TovarishDru/DevOps-Core-Course/actions/workflows/ansible-deploy.yml)
```

### 4.4 Testing Results

**Workflow run:**
[Screenshot of successful workflow execution]

**Lint job output:**
```
[Paste ansible-lint output]
```

**Deploy job output:**
```
[Paste deployment logs]
```

**Verification output:**
```
✅ Application is responding correctly
🚀 Deployment completed successfully!
📍 Application URL: http://158.160.95.154:8000
```

### 4.5 Research Answers

**Q: What are the security implications of storing SSH keys in GitHub Secrets?**
A: 
- **Pros:** GitHub Secrets are encrypted at rest and in transit, masked in logs, only exposed during workflow execution
- **Cons:** Compromised repo access could expose secrets, secrets are available to all workflows
- **Best practices:** Use dedicated deployment keys with minimal permissions, rotate keys regularly, use environment protection rules

**Q: How would you implement a staging → production deployment pipeline?**
A:
1. Create separate inventory files: `inventory/staging.ini`, `inventory/production.ini`
2. Use GitHub Environments with protection rules
3. Staging deploys automatically on push
4. Production requires manual approval
5. Use different secrets per environment

**Q: What would you add to make rollbacks possible?**
A:
1. Tag Docker images with commit SHA: `docker_tag: ${{ github.sha }}`
2. Store previous deployment state (image tag, compose file)
3. Add rollback workflow that redeploys previous image version
4. Implement blue-green or canary deployment patterns

**Q: How does self-hosted runner improve security compared to GitHub-hosted?**
A:
- **Self-hosted:** No SSH keys needed (already on network), direct access to infrastructure, no data sent to GitHub's infrastructure, faster execution
- **Trade-offs:** Requires maintenance, security hardening, and monitoring
- **Best for:** Production environments with strict security requirements

---

## Summary

### Challenges & Solutions

**Challenge 1:** Docker Compose module compatibility
**Solution:** Used `community.docker.docker_compose_v2` module which is compatible with Docker Compose v2 plugin

**Challenge 2:** Ensuring wipe logic safety
**Solution:** Implemented double-gating with both variable and tag requirements

**Challenge 3:** GitHub Actions SSH setup
**Solution:** Used ssh-keyscan to add host to known_hosts and proper key permissions

### Key Learnings

1. **Blocks** provide powerful error handling and task grouping capabilities
2. **Tags** enable flexible, selective execution of playbooks
3. **Docker Compose** is more maintainable than individual docker commands
4. **Role dependencies** ensure proper execution order automatically
5. **Double-gating** (variable + tag) provides safe destructive operations
6. **CI/CD automation** ensures consistent, auditable deployments

### Time Spent

- Task 1 (Blocks & Tags): ~1 hour
- Task 2 (Docker Compose): ~1 hours
- Task 3 (Wipe Logic): ~1 hour
- Task 4 (CI/CD): ~1 hours
- Task 5 (Documentation): ~0.5 hour
- **Total:** ~4.5 hours
---

## File Structure

```
ansible/
├── ansible.cfg
├── docs/
│   ├── LAB05.md
│   └── LAB06.md                    # This file
├── group_vars/
│   └── all.yml                     # Vault-encrypted variables
├── inventory/
│   └── hosts.ini
├── playbooks/
│   ├── deploy.yml                  # Updated: uses web_app role
│   ├── provision.yml
│   └── site.yml                    # Updated: uses web_app role
└── roles/
    ├── common/
    │   ├── defaults/main.yml
    │   └── tasks/main.yml          # Refactored with blocks & tags
    ├── docker/
    │   ├── defaults/main.yml
    │   ├── handlers/main.yml
    │   └── tasks/main.yml          # Refactored with blocks & tags
    └── web_app/                    # Renamed from app_deploy
        ├── defaults/main.yml       # Updated with new variables
        ├── handlers/main.yml
        ├── meta/main.yml           # NEW: Role dependencies
        ├── tasks/
        │   ├── main.yml            # Refactored for Docker Compose
        │   └── wipe.yml            # NEW: Wipe logic
        └── templates/
            └── docker-compose.yml.j2  # NEW: Compose template

.github/
└── workflows/
    ├── python-ci.yml               # Existing
    └── ansible-deploy.yml          # NEW: Ansible CI/CD