# Lab 5 - Ansible Fundamentals Documentation

## 1. Architecture Overview

### Ansible Version
- Ansible 2.20.2

### Target VM
- **OS:** Ubuntu 22.04 LTS

### Role Structure

```
ansible/
├── inventory/
│   └── hosts.ini              # Static inventory with VM details
├── roles/
│   ├── common/                # Common system tasks
│   │   ├── tasks/
│   │   │   └── main.yml       # Package installation, timezone
│   │   └── defaults/
│   │       └── main.yml       # Default packages list
│   ├── docker/                # Docker installation
│   │   ├── tasks/
│   │   │   └── main.yml       # Docker setup tasks
│   │   ├── handlers/
│   │   │   └── main.yml       # Docker service handler
│   │   └── defaults/
│   │       └── main.yml       # Docker configuration
│   └── app_deploy/            # Application deployment
│       ├── tasks/
│       │   └── main.yml       # Container deployment
│       ├── handlers/
│       │   └── main.yml       # Container restart handler
│       └── defaults/
│           └── main.yml       # App configuration
├── playbooks/
│   ├── site.yml               # Full deployment
│   ├── provision.yml          # System provisioning only
│   └── deploy.yml             # App deployment only
├── group_vars/
│   └── all.yml                # Encrypted variables (Vault)
├── ansible.cfg                # Ansible configuration
└── docs/
    └── LAB05.md               # This documentation
```

### Why Roles Instead of Monolithic Playbooks?

1. **Reusability**: Roles can be reused across multiple projects and playbooks
2. **Organization**: Clear separation of concerns - each role handles one responsibility
3. **Maintainability**: Changes are isolated to specific roles
4. **Testing**: Roles can be tested independently
5. **Sharing**: Roles can be shared via Ansible Galaxy
6. **Modularity**: Mix and match roles for different deployment scenarios

---

## 2. Roles Documentation

### Common Role

**Purpose:** Basic system setup that every server needs - updates packages and installs essential tools.

**Variables (defaults/main.yml):**
| Variable | Default | Description |
|----------|---------|-------------|
| `common_packages` | List of packages | Essential packages to install |
| `timezone` | `UTC` | System timezone |
| `apt_cache_valid_time` | `3600` | APT cache validity in seconds |

**Tasks:**
1. Update apt cache
2. Install common packages (python3-pip, curl, git, vim, htop, etc.)
3. Set system timezone

**Handlers:** None

**Dependencies:** None

---

### Docker Role

**Purpose:** Install and configure Docker CE on Ubuntu systems.

**Variables (defaults/main.yml):**
| Variable | Default | Description |
|----------|---------|-------------|
| `docker_packages` | List | Docker packages to install |
| `docker_user` | `{{ ansible_user }}` | User to add to docker group |
| `docker_gpg_url` | Docker GPG URL | GPG key for Docker repo |
| `docker_repo` | Docker repo URL | APT repository for Docker |
| `python_docker_package` | `python3-docker` | Python Docker package |

**Tasks:**
1. Create keyrings directory
2. Add Docker GPG key
3. Convert GPG key to binary format
4. Add Docker repository
5. Update apt cache
6. Install Docker packages
7. Ensure Docker service is running and enabled
8. Add user to docker group
9. Install Python Docker package for Ansible modules

**Handlers:**
- `restart docker`: Restarts Docker service when notified

**Dependencies:** Requires `common` role to be run first (for prerequisites)

---

### App Deploy Role

**Purpose:** Deploy containerized application using Docker, with secure credential management.

**Variables (defaults/main.yml):**
| Variable | Default | Description |
|----------|---------|-------------|
| `app_name` | `devops-python-app` | Application name |
| `app_host_port` | `5000` | Host port for the application |
| `app_container_port` | `8000` | Container internal port |
| `docker_image` | `{{ dockerhub_username }}/{{ app_name }}` | Docker image |
| `docker_image_tag` | `latest` | Image tag |
| `container_restart_policy` | `unless-stopped` | Container restart policy |
| `health_check_path` | `/health` | Health check endpoint |
| `health_check_timeout` | `60` | Health check timeout |

**Tasks:**
1. Log in to Docker Hub (using vaulted credentials)
2. Pull Docker image
3. Stop existing container (if running)
4. Remove old container (if exists)
5. Run new container with proper configuration
6. Wait for application to be ready
7. Verify health endpoint

**Handlers:**
- `restart app container`: Restarts application container when notified

**Dependencies:** Requires `docker` role to be run first

---

## 3. Idempotency Demonstration

### First Run Output

```bash
tovarish-dru@172 DevOps-Core-Course % cd ansible && ansible-playbook playbooks/provision.yml

PLAY [Provision web servers] *************************************************************************************************************************

TASK [Gathering Facts] *******************************************************************************************************************************
ok: [devops-vm]

TASK [common : Update apt cache] *********************************************************************************************************************
changed: [devops-vm]

TASK [common : Install common packages] **************************************************************************************************************
changed: [devops-vm]

TASK [common : Set timezone] *************************************************************************************************************************
changed: [devops-vm]

TASK [docker : Create keyrings directory] ************************************************************************************************************
ok: [devops-vm]

TASK [docker : Add Docker GPG key] *******************************************************************************************************************
changed: [devops-vm]

TASK [docker : Convert GPG key to binary format] *****************************************************************************************************
changed: [devops-vm]

TASK [docker : Set permissions on GPG key] ***********************************************************************************************************
ok: [devops-vm]

TASK [docker : Add Docker repository] ****************************************************************************************************************
[WARNING]: Deprecation warnings can be disabled by setting `deprecation_warnings=False` in ansible.cfg.
[DEPRECATION WARNING]: INJECT_FACTS_AS_VARS default to `True` is deprecated, top-level facts will not be auto injected after the change. This feature will be removed from ansible-core version 2.24.
Origin: /Users/tovarish-dru/Downloads/DevOps-Core-Course/ansible/roles/docker/defaults/main.yml:22:14

20
21 # Architecture mapping
22 docker_arch: "{{ 'amd64' if ansible_architecture == 'x86_64' else ansible_architecture }}"
                ^ column 14

Use `ansible_facts["fact_name"]` (no `ansible_` prefix) instead.

changed: [devops-vm]

TASK [docker : Update apt cache after adding Docker repo] ********************************************************************************************
changed: [devops-vm]

TASK [docker : Install Docker packages] **************************************************************************************************************
changed: [devops-vm]

TASK [docker : Ensure Docker service is running and enabled] *****************************************************************************************
ok: [devops-vm]

TASK [docker : Add user to docker group] *************************************************************************************************************
changed: [devops-vm]

TASK [docker : Install Python Docker package for Ansible modules] ************************************************************************************
changed: [devops-vm]

RUNNING HANDLER [docker : restart docker] ************************************************************************************************************
changed: [devops-vm]

PLAY RECAP *******************************************************************************************************************************************
devops-vm                  : ok=15   changed=11   unreachable=0    failed=0    skipped=0    rescued=0    ignored=0   
```

### Second Run Output

```bash
tovarish-dru@172 DevOps-Core-Course % cd ansible && ansible-playbook playbooks/provision.yml

PLAY [Provision web servers] *************************************************************************************************************************

TASK [Gathering Facts] *******************************************************************************************************************************
ok: [devops-vm]

TASK [common : Update apt cache] *********************************************************************************************************************
ok: [devops-vm]

TASK [common : Install common packages] **************************************************************************************************************
ok: [devops-vm]

TASK [common : Set timezone] *************************************************************************************************************************
ok: [devops-vm]

TASK [docker : Create keyrings directory] ************************************************************************************************************
ok: [devops-vm]

TASK [docker : Add Docker GPG key] *******************************************************************************************************************
ok: [devops-vm]

TASK [docker : Convert GPG key to binary format] *****************************************************************************************************
ok: [devops-vm]

TASK [docker : Set permissions on GPG key] ***********************************************************************************************************
ok: [devops-vm]

TASK [docker : Add Docker repository] ****************************************************************************************************************
ok: [devops-vm]

TASK [docker : Update apt cache after adding Docker repo] ********************************************************************************************
ok: [devops-vm]

TASK [docker : Install Docker packages] **************************************************************************************************************
ok: [devops-vm]

TASK [docker : Ensure Docker service is running and enabled] *****************************************************************************************
ok: [devops-vm]

TASK [docker : Add user to docker group] *************************************************************************************************************
ok: [devops-vm]

TASK [docker : Install Python Docker package for Ansible modules] ************************************************************************************
ok: [devops-vm]

PLAY RECAP *******************************************************************************************************************************************
devops-vm                  : ok=14   changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0   
```

### Analysis

**First Run:**
- 11 tasks showed "changed" status (yellow)
- These tasks made actual changes to the system
- Handler was triggered because Docker packages were installed

**Second Run:**
- 0 tasks showed "changed" status
- All tasks showed "ok" status (green)
- No handler was triggered because nothing changed

### What Makes These Roles Idempotent?

1. **Stateful Modules:** Using `state: present` instead of imperative commands
2. **Cache Valid Time:** APT cache only updates if older than specified time
3. **Creates Parameter:** Shell commands use `creates` to skip if file exists
4. **Service State:** `state: started` only starts if not already running
5. **User Module:** Only adds to group if not already a member

---

## 4. Ansible Vault Usage

### How Credentials Are Stored

Sensitive data is stored in `group_vars/all.yml` encrypted with Ansible Vault.

### Creating Encrypted File

```bash
# Create new encrypted file
ansible-vault create group_vars/all.yml

# Or encrypt existing file
ansible-vault encrypt group_vars/all.yml
```

### Vault Password Management

**Option 1: Interactive prompt**
```bash
ansible-playbook playbooks/deploy.yml --ask-vault-pass
```

**Option 2: Password file (recommended for automation)**
```bash
# Create password file
echo "your-vault-password" > .vault_pass
chmod 600 .vault_pass

# Add to .gitignore
echo ".vault_pass" >> .gitignore

# Use in playbook
ansible-playbook playbooks/deploy.yml --vault-password-file .vault_pass
```

**Option 3: Configure in ansible.cfg**
```ini
[defaults]
vault_password_file = .vault_pass
```

### Example of Encrypted File

```bash
tovarish-dru@172 ansible % cat ./group_vars/all.yml
$ANSIBLE_VAULT;1.1;AES256
38356132656466376662316463666435333730333763356334346333393631323733363131323862
3338356332626665366433396637343263613133323633640a373635373930383964656163386463
38613630643533613838376561363664633535326666623639386534373964313132626435323138
6162326639633636330a323764616466633962643162376566636237333265613662356331663837
34663566393166643030636439343165303030613638376664666165313034306464313332373965
31346465333136663836316639333739363030376162643931366261353264666462393439373339
37383638396435333938636430626265343238663838643439373661643533366430356462626539
62393832353236623633366663646261353263656262363564326663666165316466363466353466
34343466653465313239353266333533633933386636663934303661363465663130653063636565
64623931393866623534316666346562636232663262386261626264303766356661626339326134
61363939386661323235653837626136616261643561316239306663363835383230326531633265
30363438336636623431633866363034346161636438613932613133313566343537653638373834
32326361633461626138393566336638643739323364626432386230396566366237323066626531
61373733333833653130383032626661633466313964616333343439646364623334623032383331
36346465653863326464616565663731366534323033623036333761346535346332313737653638
65323366346433363630393039336237333139363239326133643931383434633931613364306135
3964
```

### Why Ansible Vault Is Important

1. **Security:** Credentials never stored in plain text
2. **Version Control:** Encrypted files can be safely committed to Git
3. **Compliance:** Meets security requirements for credential management
4. **Audit Trail:** Changes to encrypted files are tracked in Git
5. **Team Collaboration:** Share encrypted files, share password separately

---

## 5. Deployment Verification

### Deploy Playbook Output

```bash
tovarish-dru@172 ansible % ansible-playbook playbooks/deploy.yml --ask-vault-pass
Vault password: 

PLAY [Deploy application] ****************************************************************************************************************************

TASK [Gathering Facts] *******************************************************************************************************************************
ok: [devops-vm]

TASK [app_deploy : Log in to Docker Hub] *************************************************************************************************************
ok: [devops-vm]

TASK [app_deploy : Pull Docker image] ****************************************************************************************************************
ok: [devops-vm]

TASK [app_deploy : Remove old container if exists] ***************************************************************************************************
changed: [devops-vm]

TASK [app_deploy : Run application container] ********************************************************************************************************
changed: [devops-vm]

TASK [app_deploy : Display container info] ***********************************************************************************************************
ok: [devops-vm] => {
    "msg": "Container devops-python-app started with ID: 43a02c7fad51"
}

TASK [app_deploy : Wait for application to be ready] *************************************************************************************************
ok: [devops-vm]

TASK [app_deploy : Verify health endpoint] ***********************************************************************************************************
ok: [devops-vm]

TASK [app_deploy : Display health check result] ******************************************************************************************************
ok: [devops-vm] => {
    "msg": "Application health check passed! Status: 200"
}

PLAY RECAP *******************************************************************************************************************************************
devops-vm                  : ok=9    changed=2    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0   
```

### Health Check Verification

```bash
tovarish-dru@172 ansible % curl http://158.160.95.154:5000/health
{"status":"healthy","timestamp":"2026-02-22T17:35:12.456673+00:00","uptime_seconds":695}

tovarish-dru@172 ansible % curl http://158.160.95.154:5000/      
{"endpoints":[{"description":"Service information","method":"GET","path":"/"},{"description":"Health check","method":"GET","path":"/health"}],"request":{"client_ip":"93.158.188.126","method":"GET","path":"/","user_agent":"curl/8.7.1"},"runtime":{"current_time":"2026-02-22T17:35:24.139748+00:00","timezone":"UTC","uptime_human":"0 hours, 11 minutes","uptime_seconds":707},"service":{"description":"DevOps course info service","framework":"Flask","name":"devops-info-service","version":"1.0.0"},"system":{"architecture":"x86_64","cpu_count":2,"hostname":"43a02c7fad51","platform":"Linux","platform_version":"#100-Ubuntu SMP PREEMPT_DYNAMIC Tue Jan 13 16:40:06 UTC 2026","python_version":"3.13.11"}}
```

### Handler Execution

The `restart app container` handler is triggered when:
- Docker image is pulled (new version available)
- Container configuration changes

---

## 6. Key Decisions

### Why use roles instead of plain playbooks?

Roles provide a standardized way to organize Ansible code. They enable code reuse across projects, make testing easier, and follow the single responsibility principle. Each role handles one specific concern (common setup, Docker, app deployment), making the codebase maintainable and understandable.

### How do roles improve reusability?

Roles can be shared via Ansible Galaxy, used across multiple playbooks, and parameterized with variables. The same Docker role can be used in development, staging, and production environments with different configurations. Roles also enable composition - combining multiple roles to create complex deployments.

### What makes a task idempotent?

A task is idempotent when it produces the same result regardless of how many times it runs. This is achieved by using stateful modules (apt with state: present), checking current state before making changes, and using parameters like `creates` for shell commands. Idempotent tasks only make changes when the current state differs from the desired state.

### How do handlers improve efficiency?

Handlers only run when notified by a task that made a change. This prevents unnecessary service restarts. For example, Docker service only restarts when packages are actually installed, not on every playbook run. Handlers also run once at the end, even if notified multiple times.

### Why is Ansible Vault necessary?

Ansible Vault encrypts sensitive data (passwords, API keys, tokens) so they can be safely stored in version control. Without Vault, credentials would be in plain text, creating security risks. Vault enables secure collaboration - team members can share encrypted files and manage the password separately through secure channels.
