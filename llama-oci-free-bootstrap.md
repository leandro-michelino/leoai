# Llama on OCI Always Free - End-to-End Bootstrap Runbook (v2)

> **Audience:** AI coding agent (Codex) executing this runbook autonomously.
> **Goal:** Provision an OCI Always Free environment serving a quantized Llama with a web UI, an authenticated OpenAI-compatible API, and an optional RAG endpoint - all for $0.
> **Estimated time:** 45-120 minutes (A1 capacity is the main variable).

---

## 0. Mission and final state

Stand up the following on OCI Always Free:

- 1x `VM.Standard.A1.Flex` (4 OCPU / 24 GB RAM, ARM Ampere Altra)
- Oracle Linux 9 Aarch64
- Llama 3.2 3B Instruct in GGUF Q4_K_M, served by Ampere-optimized `llama.cpp`
- Open WebUI as the chat frontend (built-in auth)
- API key-protected OpenAI-compatible API
- RAG service (ChromaDB + sentence-transformers + FastAPI)
- Model file stored in OCI Object Storage (so VM rebuilds don't re-download from HF)
- NGINX as single ingress on port 80
- Everything wrapped behind a Makefile

End state - publicly reachable on `http://<public-ip>`:

| Path | Purpose | Auth |
|------|---------|------|
| `/` | Open WebUI chat UI | Built-in (signup/login) |
| `/v1/*` | OpenAI-compatible API (chat, completions, embeddings) | Header `X-API-Key` |
| `/rag/query` | RAG query endpoint | Header `X-API-Key` |
| `/rag/index` | Ingest documents into the vector store | Header `X-API-Key` |
| `/health` | Liveness probe | Public |

---

## 1. Prerequisites the user must supply

If any of the following is missing, STOP and ask the user.

| # | Item | How to get it |
|---|------|---------------|
| 1 | OCI tenancy with Always Free | https://www.oracle.com/cloud/free/ |
| 2 | Region with A1 capacity | `eu-frankfurt-1` (best for EU) or `ap-singapore-1` |
| 3 | OCI CLI installed and configured (`~/.oci/config`) | https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm |
| 4 | Terraform >= 1.5 | https://developer.hashicorp.com/terraform/install |
| 5 | Ansible >= 2.14 | `pipx install ansible` or distro package |
| 6 | Hugging Face account + read token | https://huggingface.co/settings/tokens |
| 7 | Meta Llama 3.2 license accepted on HF (or use community mirror in section 2) | https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct |
| 8 | SSH keypair | `ssh-keygen -t ed25519 -f ~/.ssh/oci_llama` |
| 9 | `jq`, `curl`, `make`, `python3` on the operator machine | distro package manager |

Required environment variables (put in `.env` at repo root, do NOT commit):

```bash
# OCI auth
export TF_VAR_tenancy_ocid="ocid1.tenancy.oc1..xxxxx"
export TF_VAR_user_ocid="ocid1.user.oc1..xxxxx"
export TF_VAR_fingerprint="aa:bb:cc:..."
export TF_VAR_private_key_path="$HOME/.oci/oci_api_key.pem"
export TF_VAR_region="eu-frankfurt-1"
export TF_VAR_compartment_ocid="ocid1.compartment.oc1..xxxxx"  # use tenancy OCID if no compartment
export TF_VAR_ssh_public_key_path="$HOME/.ssh/oci_llama.pub"
export TF_VAR_ssh_private_key_path="$HOME/.ssh/oci_llama"

# App secrets (Ansible reads these)
export HF_TOKEN="hf_xxxxxxxxxxxxxxxx"
export API_KEY="$(openssl rand -hex 32)"        # generated once, reused
export WEBUI_SECRET_KEY="$(openssl rand -hex 32)"
```

---

## 2. Architecture

```
                            Internet
                                |
                  HTTP 80 (NGINX ingress)
                                |
        +-----------------------v-----------------------+
        | VM.Standard.A1.Flex  (4 OCPU / 24 GB)         |
        | Oracle Linux 9 ARM                            |
        |                                               |
        |  +----------+    +----------+   +---------+   |
        |  | NGINX 80 |--->|Open WebUI|   |llama.cpp|   |
        |  |          |    |  :3000   |-->|  :8081  |   |
        |  |          |    +----------+   | (OpenAI |   |
        |  |          |--->| RAG API  |-->|  /v1)   |   |
        |  |          |    |  :8082   |   +---------+   |
        |  +----------+    +----+-----+        ^        |
        |                       |              |        |
        |                  +----v-----+        |        |
        |                  |ChromaDB  |        |        |
        |                  |(embedded)|        |        |
        |                  +----------+        |        |
        |                                      |        |
        |   /opt/llama/models/*.gguf  ---------+        |
        +-----------------------------------------------+
                                |
                                v
                  +----------------------------+
                  | OCI Object Storage         |
                  | bucket: llama-models       |
                  | (model staged here once,   |
                  |  VM pulls via PAR URL)     |
                  +----------------------------+
```

---

## 3. Repository layout to create

```
oci-llama/
├── .env.example                 # template for user to fill
├── .gitignore
├── Makefile                     # operator entry point
├── README.md                    # this file
├── terraform/
│   ├── versions.tf
│   ├── providers.tf
│   ├── variables.tf
│   ├── network.tf
│   ├── compute.tf
│   ├── storage.tf
│   ├── outputs.tf
│   ├── cloud-init.yaml          # minimal - just enough for Ansible to take over
│   └── templates/
│       └── inventory.tpl        # rendered to ansible/inventory.yml
└── ansible/
    ├── ansible.cfg
    ├── site.yml
    ├── group_vars/
    │   └── all.yml
    └── roles/
        ├── base/tasks/main.yml
        ├── model/tasks/main.yml
        ├── llama/
        │   ├── tasks/main.yml
        │   └── templates/llama.service.j2
        ├── webui/
        │   ├── tasks/main.yml
        │   └── templates/webui.service.j2
        ├── rag/
        │   ├── tasks/main.yml
        │   ├── templates/rag.service.j2
        │   └── files/
        │       ├── rag_api.py
        │       ├── requirements.txt
        │       └── seed.txt
        └── nginx/
            ├── tasks/main.yml
            └── templates/llama.conf.j2
```

---

## 4. Root files

### 4.1 `.env.example`

```bash
# Copy to .env and fill in. NEVER commit .env.

# OCI
export TF_VAR_tenancy_ocid=""
export TF_VAR_user_ocid=""
export TF_VAR_fingerprint=""
export TF_VAR_private_key_path="$HOME/.oci/oci_api_key.pem"
export TF_VAR_region="eu-frankfurt-1"
export TF_VAR_compartment_ocid=""
export TF_VAR_ssh_public_key_path="$HOME/.ssh/oci_llama.pub"
export TF_VAR_ssh_private_key_path="$HOME/.ssh/oci_llama"

# Secrets
export HF_TOKEN=""
export API_KEY=""
export WEBUI_SECRET_KEY=""
```

### 4.2 `.gitignore`

```
.env
*.tfstate
*.tfstate.backup
.terraform/
.terraform.lock.hcl
ansible/inventory.yml
ansible/.vault-pass
__pycache__/
*.pyc
```

### 4.3 `Makefile`

```makefile
SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c

# Source .env if present
ifneq (,$(wildcard .env))
include .env
export
endif

TF_DIR      := terraform
ANSIBLE_DIR := ansible

.PHONY: help check up down tf-init tf-plan tf-apply tf-destroy \
        inventory ansible-ping ansible-deploy ansible-check \
        logs status test ssh seed-rag

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS=":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

check: ## Verify required env vars and tools
	@for v in TF_VAR_tenancy_ocid TF_VAR_compartment_ocid TF_VAR_region HF_TOKEN API_KEY WEBUI_SECRET_KEY; do \
	  if [ -z "$${!v:-}" ]; then echo "ERROR: $$v is not set"; exit 1; fi; \
	done
	@command -v terraform >/dev/null || { echo "terraform not installed"; exit 1; }
	@command -v ansible-playbook >/dev/null || { echo "ansible not installed"; exit 1; }
	@command -v jq >/dev/null || { echo "jq not installed"; exit 1; }
	@echo "All required env vars and tools present."

up: check tf-apply inventory ansible-deploy test ## Full bootstrap end to end
	@echo ""
	@echo "============================================"
	@echo "  Bootstrap complete. Endpoints:"
	@echo "============================================"
	@cd $(TF_DIR) && PUBLIC_IP=$$(terraform output -raw public_ip) && \
	  echo "  Web UI:  http://$$PUBLIC_IP/" && \
	  echo "  API:     http://$$PUBLIC_IP/v1/chat/completions" && \
	  echo "  RAG:     http://$$PUBLIC_IP/rag/query" && \
	  echo "  API key: $$API_KEY"

down: tf-destroy ## Tear down everything

tf-init: ## terraform init
	cd $(TF_DIR) && terraform init -upgrade

tf-plan: ## terraform plan
	cd $(TF_DIR) && terraform plan -out tfplan

tf-apply: tf-init ## terraform apply with capacity retry
	@cd $(TF_DIR) && \
	ATTEMPTS=0; MAX=30; SLEEP=180; \
	terraform plan -out tfplan; \
	until terraform apply -auto-approve tfplan; do \
	  ATTEMPTS=$$((ATTEMPTS+1)); \
	  if [ $$ATTEMPTS -ge $$MAX ]; then echo "Out of attempts"; exit 1; fi; \
	  echo "Attempt $$ATTEMPTS/$$MAX failed. Retry in $$SLEEP s..."; \
	  sleep $$SLEEP; \
	  terraform plan -out tfplan; \
	done

tf-destroy: ## terraform destroy
	cd $(TF_DIR) && terraform destroy -auto-approve

inventory: ## Wait for SSH, write Ansible inventory
	@cd $(TF_DIR) && IP=$$(terraform output -raw public_ip) && \
	  echo "Waiting for SSH on $$IP..." && \
	  until ssh -i $$TF_VAR_ssh_private_key_path -o StrictHostKeyChecking=no \
	    -o ConnectTimeout=10 opc@$$IP "echo ready" 2>/dev/null; do sleep 10; done && \
	  ssh -i $$TF_VAR_ssh_private_key_path -o StrictHostKeyChecking=no opc@$$IP \
	    "sudo cloud-init status --wait" && \
	  echo "Host ready."

ansible-ping: ## Verify Ansible connectivity
	cd $(ANSIBLE_DIR) && ansible -i inventory.yml all -m ping

ansible-check: ## Ansible dry run
	cd $(ANSIBLE_DIR) && ansible-playbook -i inventory.yml site.yml --check --diff

ansible-deploy: ## Apply Ansible playbook
	cd $(ANSIBLE_DIR) && ansible-playbook -i inventory.yml site.yml

logs: ## Tail service logs
	@cd $(TF_DIR) && IP=$$(terraform output -raw public_ip) && \
	  ssh -i $$TF_VAR_ssh_private_key_path opc@$$IP "sudo journalctl -u llama -u webui -u rag -f"

status: ## Service status on the VM
	@cd $(TF_DIR) && IP=$$(terraform output -raw public_ip) && \
	  ssh -i $$TF_VAR_ssh_private_key_path opc@$$IP \
	    "systemctl status llama webui rag nginx --no-pager -l"

ssh: ## SSH into the VM
	@cd $(TF_DIR) && IP=$$(terraform output -raw public_ip) && \
	  ssh -i $$TF_VAR_ssh_private_key_path opc@$$IP

test: ## Smoke-test all endpoints
	@cd $(TF_DIR) && IP=$$(terraform output -raw public_ip); \
	  echo "--- Health ---"; \
	  curl -fsS http://$$IP/health; echo ""; \
	  echo "--- Chat completion (X-API-Key) ---"; \
	  curl -fsS http://$$IP/v1/chat/completions \
	    -H "X-API-Key: $$API_KEY" -H "Content-Type: application/json" \
	    -d '{"messages":[{"role":"user","content":"Say hi in Portuguese."}],"max_tokens":40}' | jq .choices[0].message.content; \
	  echo "--- RAG query ---"; \
	  curl -fsS http://$$IP/rag/query \
	    -H "X-API-Key: $$API_KEY" -H "Content-Type: application/json" \
	    -d '{"query":"What is OCI Always Free?","top_k":3}' | jq .answer

seed-rag: ## Re-index the seed documents
	@cd $(TF_DIR) && IP=$$(terraform output -raw public_ip) && \
	  ssh -i $$TF_VAR_ssh_private_key_path opc@$$IP \
	    "sudo systemctl restart rag && sleep 5 && curl -fsS -X POST http://127.0.0.1:8082/reindex"
```

---

## 5. Terraform layer

All Terraform files live in `terraform/`.

### 5.1 `terraform/versions.tf`

```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 5.0.0"
    }
    local = {
      source  = "hashicorp/local"
      version = ">= 2.4.0"
    }
  }
}
```

### 5.2 `terraform/providers.tf`

```hcl
provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}
```

### 5.3 `terraform/variables.tf`

```hcl
variable "tenancy_ocid" { type = string }
variable "user_ocid" { type = string }
variable "fingerprint" { type = string }
variable "private_key_path" { type = string }
variable "region" { type = string }
variable "compartment_ocid" { type = string }
variable "ssh_public_key_path" { type = string }
variable "ssh_private_key_path" { type = string }

variable "instance_name" {
  type    = string
  default = "llama-free"
}

variable "vcn_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "subnet_cidr" {
  type    = string
  default = "10.0.1.0/24"
}

variable "ocpus" {
  type    = number
  default = 4
}

variable "memory_gb" {
  type    = number
  default = 24
}

variable "boot_volume_gb" {
  type    = number
  default = 50
}

variable "model_bucket_name" {
  type    = string
  default = "llama-models"
}

variable "model_file" {
  type    = string
  default = "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
}

# Community GGUF mirror (ungated). Switch to meta-llama/* if the license was accepted.
variable "model_source_url" {
  type    = string
  default = "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
}
```

### 5.4 `terraform/network.tf`

```hcl
resource "oci_core_vcn" "this" {
  compartment_id = var.compartment_ocid
  cidr_blocks    = [var.vcn_cidr]
  display_name   = "${var.instance_name}-vcn"
  dns_label      = "llamavcn"
}

resource "oci_core_internet_gateway" "this" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.instance_name}-igw"
  enabled        = true
}

resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.instance_name}-rt"
  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.this.id
  }
}

resource "oci_core_security_list" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.instance_name}-sl"

  egress_security_rules {
    destination      = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
    protocol         = "all"
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 22
      max = 22
    }
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 80
      max = 80
    }
  }
}

resource "oci_core_subnet" "public" {
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.this.id
  cidr_block                 = var.subnet_cidr
  display_name               = "${var.instance_name}-subnet"
  dns_label                  = "llamasubnet"
  route_table_id             = oci_core_route_table.public.id
  security_list_ids          = [oci_core_security_list.public.id]
  prohibit_public_ip_on_vnic = false
}
```

### 5.5 `terraform/storage.tf`

Creates an Object Storage bucket and a Pre-Authenticated Request (PAR) for the model file, so the VM can pull the model without OCI credentials. The model file itself is staged into the bucket once by the operator (see notes below).

```hcl
data "oci_objectstorage_namespace" "ns" {
  compartment_id = var.tenancy_ocid
}

resource "oci_objectstorage_bucket" "models" {
  compartment_id = var.compartment_ocid
  namespace      = data.oci_objectstorage_namespace.ns.namespace
  name           = var.model_bucket_name
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
}

# PAR to read the model object. Works even before the object exists - Ansible
# tries it first, and falls back to Hugging Face if 404.
resource "oci_objectstorage_preauthrequest" "model_read" {
  namespace    = data.oci_objectstorage_namespace.ns.namespace
  bucket       = oci_objectstorage_bucket.models.name
  name         = "read-${var.model_file}"
  access_type  = "ObjectRead"
  object_name  = var.model_file
  time_expires = timeadd(timestamp(), "8760h") # 1 year

  lifecycle {
    ignore_changes = [time_expires]
  }
}

locals {
  par_url = "https://objectstorage.${var.region}.oraclecloud.com${oci_objectstorage_preauthrequest.model_read.access_uri}"
}
```

### 5.6 `terraform/compute.tf`

```hcl
data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

data "oci_core_images" "ol9_arm" {
  compartment_id           = var.tenancy_ocid
  operating_system         = "Oracle Linux"
  operating_system_version = "9"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

resource "oci_core_instance" "llama" {
  compartment_id      = var.compartment_ocid
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  shape               = "VM.Standard.A1.Flex"
  display_name        = var.instance_name

  shape_config {
    ocpus         = var.ocpus
    memory_in_gbs = var.memory_gb
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ol9_arm.images[0].id
    boot_volume_size_in_gbs = var.boot_volume_gb
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public.id
    assign_public_ip = true
    hostname_label   = "llama"
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_public_key_path)
    user_data           = base64encode(file("${path.module}/cloud-init.yaml"))
  }
}
```

### 5.7 `terraform/cloud-init.yaml`

Now minimal - just enough to make the VM Ansible-ready.

```yaml
#cloud-config
package_update: true
packages:
  - python3
  - python3-pip
  - python3-libdnf5
  - firewalld
runcmd:
  - systemctl disable --now firewalld || true
  - iptables -I INPUT -p tcp --dport 80 -j ACCEPT
  - iptables -I INPUT -p tcp --dport 22 -j ACCEPT
  - /sbin/iptables-save > /etc/sysconfig/iptables || true
  - mkdir -p /opt/llama/models /opt/llama/chroma /opt/llama/rag
  - chown -R opc:opc /opt/llama
final_message: "cloud-init done. Hand off to Ansible."
```

### 5.8 `terraform/outputs.tf`

```hcl
output "public_ip" {
  value = oci_core_instance.llama.public_ip
}

output "ssh_command" {
  value = "ssh -i ${var.ssh_private_key_path} opc@${oci_core_instance.llama.public_ip}"
}

output "bucket_namespace" {
  value = data.oci_objectstorage_namespace.ns.namespace
}

output "bucket_name" {
  value = oci_objectstorage_bucket.models.name
}

output "model_par_url" {
  value     = local.par_url
  sensitive = true
}

# Render Ansible inventory next to the playbook
resource "local_file" "ansible_inventory" {
  filename        = "${path.module}/../ansible/inventory.yml"
  file_permission = "0600"
  content = templatefile("${path.module}/templates/inventory.tpl", {
    public_ip         = oci_core_instance.llama.public_ip
    ssh_key_path      = var.ssh_private_key_path
    model_file        = var.model_file
    model_source_url  = var.model_source_url
    par_url           = local.par_url
    bucket_namespace  = data.oci_objectstorage_namespace.ns.namespace
    bucket_name       = oci_objectstorage_bucket.models.name
    region            = var.region
  })
}
```

### 5.9 `terraform/templates/inventory.tpl`

```yaml
all:
  hosts:
    llama:
      ansible_host: ${public_ip}
      ansible_user: opc
      ansible_ssh_private_key_file: ${ssh_key_path}
      ansible_ssh_common_args: '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
  vars:
    model_file: ${model_file}
    model_source_url: ${model_source_url}
    par_url: "${par_url}"
    bucket_namespace: ${bucket_namespace}
    bucket_name: ${bucket_name}
    oci_region: ${region}
```

---

## 6. Ansible layer

### 6.1 `ansible/ansible.cfg`

```ini
[defaults]
host_key_checking = False
retry_files_enabled = False
stdout_callback = yaml
inventory = inventory.yml
forks = 5
gathering = smart
roles_path = roles
timeout = 60

[ssh_connection]
pipelining = True
ssh_args = -o ControlMaster=auto -o ControlPersist=60s
```

### 6.2 `ansible/group_vars/all.yml`

```yaml
hf_token: "{{ lookup('env', 'HF_TOKEN') }}"
api_key: "{{ lookup('env', 'API_KEY') }}"
webui_secret_key: "{{ lookup('env', 'WEBUI_SECRET_KEY') }}"

llama_port: 8081
webui_port: 3000
rag_port: 8082

llama_image: "docker.io/amperecomputingai/llama.cpp:latest"
webui_image: "ghcr.io/open-webui/open-webui:main"

ctx_size: 4096
threads: 4
```

### 6.3 `ansible/site.yml`

```yaml
---
- name: Bootstrap Llama stack on OCI Always Free
  hosts: all
  become: true
  gather_facts: true

  pre_tasks:
    - name: Wait for cloud-init to finish
      ansible.builtin.command: cloud-init status --wait
      changed_when: false

    - name: Fail fast if secrets missing
      ansible.builtin.assert:
        that:
          - hf_token | length > 0
          - api_key | length > 0
          - webui_secret_key | length > 0
        fail_msg: "HF_TOKEN, API_KEY and WEBUI_SECRET_KEY must be set in the environment."

  roles:
    - base
    - model
    - llama
    - webui
    - rag
    - nginx

  post_tasks:
    - name: Final summary
      ansible.builtin.debug:
        msg: |
          Stack deployed. Public IP: {{ ansible_host }}
          Web UI:  http://{{ ansible_host }}/
          API:     http://{{ ansible_host }}/v1/chat/completions
          RAG:     http://{{ ansible_host }}/rag/query
```

### 6.4 Role: `base`

`ansible/roles/base/tasks/main.yml`

```yaml
---
- name: Install base packages
  ansible.builtin.dnf:
    name:
      - podman
      - nginx
      - jq
      - wget
      - python3-pip
      - python3-virtualenv
      - gcc
      - python3-devel
    state: present

- name: Ensure base directories
  ansible.builtin.file:
    path: "{{ item }}"
    state: directory
    owner: opc
    group: opc
    mode: "0755"
  loop:
    - /opt/llama
    - /opt/llama/models
    - /opt/llama/chroma
    - /opt/llama/rag
    - /opt/llama/rag/seed
    - /var/log/llama

- name: Create env file for secrets (root-only)
  ansible.builtin.copy:
    dest: /etc/llama.env
    owner: root
    group: root
    mode: "0600"
    content: |
      API_KEY={{ api_key }}
      WEBUI_SECRET_KEY={{ webui_secret_key }}
      HF_TOKEN={{ hf_token }}
```

### 6.5 Role: `model`

Strategy: try the Object Storage PAR first. If the object isn't there yet (first run), fall back to Hugging Face. After the first successful download, the operator uploads the file to the bucket once - subsequent VM rebuilds pull from OCI in seconds.

`ansible/roles/model/tasks/main.yml`

```yaml
---
- name: Check if model already on VM
  ansible.builtin.stat:
    path: "/opt/llama/models/{{ model_file }}"
  register: model_local

- name: Try Object Storage PAR download
  ansible.builtin.get_url:
    url: "{{ par_url }}"
    dest: "/opt/llama/models/{{ model_file }}"
    mode: "0644"
    owner: opc
    group: opc
    timeout: 120
  register: par_download
  failed_when: false
  when: not model_local.stat.exists

- name: Fallback to Hugging Face download
  ansible.builtin.get_url:
    url: "{{ model_source_url }}"
    dest: "/opt/llama/models/{{ model_file }}"
    mode: "0644"
    owner: opc
    group: opc
    headers:
      Authorization: "Bearer {{ hf_token }}"
    timeout: 600
  when:
    - not model_local.stat.exists
    - par_download.failed | default(false) or (par_download.status_code | default(0)) != 200

- name: Verify model size is sane (>1 GB)
  ansible.builtin.stat:
    path: "/opt/llama/models/{{ model_file }}"
  register: model_check
  failed_when: model_check.stat.size < 1073741824
```

> **Operator step (one time, after first successful run):** Upload the downloaded model to Object Storage so future rebuilds skip HF:
> ```bash
> make ssh -- "sudo cp /opt/llama/models/$MODEL_FILE /tmp/" 
> # then from your laptop:
> oci os object put --bucket-name llama-models --file ./model.gguf --name $MODEL_FILE
> ```

### 6.6 Role: `llama`

`ansible/roles/llama/templates/llama.service.j2`

```ini
[Unit]
Description=llama.cpp Ampere-optimized server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Restart=on-failure
RestartSec=10
ExecStartPre=-/usr/bin/podman rm -f llama
ExecStartPre=/usr/bin/podman pull {{ llama_image }}
ExecStart=/usr/bin/podman run --rm --name llama \
  -p 127.0.0.1:{{ llama_port }}:{{ llama_port }} \
  -v /opt/llama/models:/models:Z \
  {{ llama_image }} \
  -m /models/{{ model_file }} \
  --host 0.0.0.0 --port {{ llama_port }} \
  --ctx-size {{ ctx_size }} \
  --threads {{ threads }} \
  --api-key dummy-internal-key
ExecStop=/usr/bin/podman stop -t 10 llama

[Install]
WantedBy=multi-user.target
```

`ansible/roles/llama/tasks/main.yml`

```yaml
---
- name: Deploy llama systemd unit
  ansible.builtin.template:
    src: llama.service.j2
    dest: /etc/systemd/system/llama.service
    mode: "0644"

- name: Enable and start llama
  ansible.builtin.systemd:
    name: llama
    enabled: true
    state: started
    daemon_reload: true

- name: Wait for llama HTTP
  ansible.builtin.uri:
    url: "http://127.0.0.1:{{ llama_port }}/health"
    status_code: 200
  register: llama_health
  retries: 30
  delay: 10
  until: llama_health.status == 200
```

### 6.7 Role: `webui` (Open WebUI)

`ansible/roles/webui/templates/webui.service.j2`

```ini
[Unit]
Description=Open WebUI
After=network-online.target llama.service
Wants=network-online.target

[Service]
Type=simple
Restart=on-failure
RestartSec=10
EnvironmentFile=/etc/llama.env
ExecStartPre=-/usr/bin/podman rm -f webui
ExecStartPre=/usr/bin/podman pull {{ webui_image }}
ExecStart=/usr/bin/podman run --rm --name webui \
  -p 127.0.0.1:{{ webui_port }}:8080 \
  -v /opt/llama/webui-data:/app/backend/data:Z \
  -e OPENAI_API_BASE_URLS=http://host.containers.internal:{{ llama_port }}/v1 \
  -e OPENAI_API_KEYS=dummy-internal-key \
  -e WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY} \
  -e WEBUI_AUTH=true \
  -e ENABLE_SIGNUP=true \
  --add-host=host.containers.internal:host-gateway \
  {{ webui_image }}
ExecStop=/usr/bin/podman stop -t 10 webui

[Install]
WantedBy=multi-user.target
```

`ansible/roles/webui/tasks/main.yml`

```yaml
---
- name: Ensure webui data dir
  ansible.builtin.file:
    path: /opt/llama/webui-data
    state: directory
    owner: opc
    group: opc
    mode: "0755"

- name: Deploy webui systemd unit
  ansible.builtin.template:
    src: webui.service.j2
    dest: /etc/systemd/system/webui.service
    mode: "0644"

- name: Enable and start webui
  ansible.builtin.systemd:
    name: webui
    enabled: true
    state: started
    daemon_reload: true

- name: Wait for Open WebUI
  ansible.builtin.uri:
    url: "http://127.0.0.1:{{ webui_port }}/"
    status_code: 200
  register: webui_health
  retries: 60
  delay: 5
  until: webui_health.status == 200
```

### 6.8 Role: `rag` (FastAPI + ChromaDB + sentence-transformers)

`ansible/roles/rag/files/requirements.txt`

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
chromadb==0.5.5
sentence-transformers==3.0.1
httpx==0.27.2
pydantic==2.8.2
```

`ansible/roles/rag/files/rag_api.py`

```python
"""Minimal RAG service: embed + retrieve from Chroma + call llama.cpp /v1/chat/completions."""
import os
from pathlib import Path
from typing import List, Optional

import chromadb
import httpx
from chromadb.utils import embedding_functions
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

API_KEY = os.environ["API_KEY"]
LLAMA_URL = os.environ.get("LLAMA_URL", "http://127.0.0.1:8081/v1/chat/completions")
LLAMA_KEY = os.environ.get("LLAMA_INTERNAL_KEY", "dummy-internal-key")
CHROMA_DIR = os.environ.get("CHROMA_DIR", "/opt/llama/chroma")
SEED_DIR = os.environ.get("SEED_DIR", "/opt/llama/rag/seed")
COLLECTION = "docs"
EMBED_MODEL = "all-MiniLM-L6-v2"

app = FastAPI(title="llama-rag")

embedder = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = client.get_or_create_collection(name=COLLECTION, embedding_function=embedder)


def _check_key(x_api_key: Optional[str]) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


class IndexBody(BaseModel):
    documents: List[str]
    ids: Optional[List[str]] = None
    metadatas: Optional[List[dict]] = None


class QueryBody(BaseModel):
    query: str
    top_k: int = 3
    temperature: float = 0.2
    max_tokens: int = 400


@app.get("/health")
def health():
    return {"status": "ok", "count": collection.count()}


@app.post("/index")
def index(body: IndexBody, x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    ids = body.ids or [f"doc-{collection.count() + i}" for i in range(len(body.documents))]
    metadatas = body.metadatas or [{} for _ in body.documents]
    collection.add(documents=body.documents, ids=ids, metadatas=metadatas)
    return {"added": len(body.documents), "total": collection.count()}


@app.post("/reindex")
def reindex(x_api_key: Optional[str] = Header(None)):
    """Wipe collection and re-load seed docs from disk (no auth needed when called locally)."""
    client.delete_collection(name=COLLECTION)
    new_collection = client.get_or_create_collection(name=COLLECTION, embedding_function=embedder)
    seed_files = list(Path(SEED_DIR).glob("*.txt"))
    docs, ids = [], []
    for f in seed_files:
        text = f.read_text(encoding="utf-8")
        for i, chunk in enumerate([p.strip() for p in text.split("\n\n") if p.strip()]):
            docs.append(chunk)
            ids.append(f"{f.stem}-{i}")
    if docs:
        new_collection.add(documents=docs, ids=ids)
    return {"reindexed": len(docs), "files": [str(f.name) for f in seed_files]}


@app.post("/query")
def query(body: QueryBody, x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    if collection.count() == 0:
        raise HTTPException(status_code=409, detail="collection is empty - POST /index or /reindex first")

    result = collection.query(query_texts=[body.query], n_results=body.top_k)
    contexts = result["documents"][0]
    context_block = "\n\n".join(f"[{i+1}] {c}" for i, c in enumerate(contexts))

    system = (
        "You answer strictly from the provided context. "
        "If the answer is not in the context, say you don't know."
    )
    user = f"Context:\n{context_block}\n\nQuestion: {body.query}"

    payload = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": body.temperature,
        "max_tokens": body.max_tokens,
    }
    headers = {"Authorization": f"Bearer {LLAMA_KEY}", "Content-Type": "application/json"}

    with httpx.Client(timeout=300) as h:
        r = h.post(LLAMA_URL, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()

    return {
        "answer": data["choices"][0]["message"]["content"],
        "contexts": contexts,
        "usage": data.get("usage"),
    }
```

`ansible/roles/rag/files/seed.txt`

```
Oracle Cloud Infrastructure (OCI) Always Free tier includes 4 OCPUs and 24 GB of RAM on Arm-based Ampere A1 Flex instances that never expire.

The Ampere-optimized llama.cpp container provides Q4_K_4 and Q8R16 quantizations tuned for the ARM SVE/NEON instruction set, delivering 1.5-2x speedup over standard Q4_K_M.

OCI Object Storage offers 20 GB of free standard tier storage and supports Pre-Authenticated Requests (PARs), which allow time-limited URL-based access to objects without credentials.

NGINX is the reverse proxy in front of all services on this VM. It exposes port 80, routing / to Open WebUI, /v1 to llama.cpp, and /rag to the RAG API, gated by an X-API-Key header.

The RAG service uses ChromaDB as the vector store and sentence-transformers/all-MiniLM-L6-v2 for embeddings - both run locally with no external API calls.
```

`ansible/roles/rag/templates/rag.service.j2`

```ini
[Unit]
Description=RAG API (FastAPI + ChromaDB + sentence-transformers)
After=network-online.target llama.service
Wants=network-online.target

[Service]
Type=simple
User=opc
Group=opc
WorkingDirectory=/opt/llama/rag
EnvironmentFile=/etc/llama.env
Environment=CHROMA_DIR=/opt/llama/chroma
Environment=SEED_DIR=/opt/llama/rag/seed
Environment=LLAMA_URL=http://127.0.0.1:{{ llama_port }}/v1/chat/completions
Environment=LLAMA_INTERNAL_KEY=dummy-internal-key
ExecStart=/opt/llama/rag/venv/bin/uvicorn rag_api:app --host 127.0.0.1 --port {{ rag_port }}
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

`ansible/roles/rag/tasks/main.yml`

```yaml
---
- name: Copy RAG files
  ansible.builtin.copy:
    src: "{{ item.src }}"
    dest: "{{ item.dest }}"
    owner: opc
    group: opc
    mode: "0644"
  loop:
    - { src: "rag_api.py", dest: "/opt/llama/rag/rag_api.py" }
    - { src: "requirements.txt", dest: "/opt/llama/rag/requirements.txt" }
    - { src: "seed.txt", dest: "/opt/llama/rag/seed/seed.txt" }

- name: Create Python venv
  ansible.builtin.command: python3 -m venv /opt/llama/rag/venv
  args:
    creates: /opt/llama/rag/venv/bin/python

- name: Install RAG dependencies
  ansible.builtin.pip:
    requirements: /opt/llama/rag/requirements.txt
    virtualenv: /opt/llama/rag/venv

- name: Fix venv ownership
  ansible.builtin.file:
    path: /opt/llama/rag
    state: directory
    recurse: true
    owner: opc
    group: opc

- name: Deploy RAG systemd unit
  ansible.builtin.template:
    src: rag.service.j2
    dest: /etc/systemd/system/rag.service
    mode: "0644"

- name: Enable and start RAG
  ansible.builtin.systemd:
    name: rag
    enabled: true
    state: started
    daemon_reload: true

- name: Wait for RAG health
  ansible.builtin.uri:
    url: "http://127.0.0.1:{{ rag_port }}/health"
    status_code: 200
  register: rag_health
  retries: 30
  delay: 5
  until: rag_health.status == 200

- name: Seed the vector store
  ansible.builtin.uri:
    url: "http://127.0.0.1:{{ rag_port }}/reindex"
    method: POST
    status_code: 200
  failed_when: false
```

### 6.9 Role: `nginx` (single ingress with API-key auth)

`ansible/roles/nginx/templates/llama.conf.j2`

```nginx
map $http_x_api_key $api_key_valid {
    default 0;
    "{{ api_key }}" 1;
}

server {
    listen 80 default_server;
    server_name _;
    client_max_body_size 16m;

    location = /health {
        access_log off;
        default_type text/plain;
        return 200 "ok\n";
    }

    # OpenAI-compatible API - requires X-API-Key
    location /v1/ {
        if ($api_key_valid = 0) { return 401 "missing or invalid X-API-Key\n"; }

        proxy_pass http://127.0.0.1:{{ llama_port }}/v1/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 600s;
        proxy_buffering off;
    }

    # RAG API - requires X-API-Key
    location /rag/ {
        if ($api_key_valid = 0) { return 401 "missing or invalid X-API-Key\n"; }

        proxy_pass http://127.0.0.1:{{ rag_port }}/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 600s;
        proxy_buffering off;
    }

    # Open WebUI (handles its own auth)
    location / {
        proxy_pass http://127.0.0.1:{{ webui_port }}/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 600s;
        proxy_buffering off;
    }
}
```

`ansible/roles/nginx/tasks/main.yml`

```yaml
---
- name: Remove default NGINX server
  ansible.builtin.file:
    path: /etc/nginx/conf.d/default.conf
    state: absent
  notify: reload nginx

- name: Deploy llama.conf
  ansible.builtin.template:
    src: llama.conf.j2
    dest: /etc/nginx/conf.d/llama.conf
    mode: "0644"
  notify: reload nginx

- name: Allow nginx to proxy upstream (SELinux)
  ansible.posix.seboolean:
    name: httpd_can_network_connect
    state: true
    persistent: true
  failed_when: false

- name: Enable and start NGINX
  ansible.builtin.systemd:
    name: nginx
    enabled: true
    state: started

handlers:
  - name: reload nginx
    ansible.builtin.systemd:
      name: nginx
      state: reloaded
```

---

## 7. Execution sequence

From the repo root:

```bash
cp .env.example .env
# fill in .env, then:
source .env
make check       # validates env + tools
make up          # tf-apply (with retry) -> inventory -> ansible-deploy -> test
```

`make up` runs end-to-end. The terminal prints the final endpoints + API key. First run takes ~30 min after capacity is available (downloads model + container images). Subsequent rebuilds take ~10 min if the model is in Object Storage.

If something fails partway through, just re-run `make up` - Ansible is idempotent and skips completed steps.

---

## 8. Post-bootstrap operations

| Action | Command |
|--------|---------|
| Open chat UI | Browser to `http://$PUBLIC_IP/` and sign up (first user becomes admin) |
| Call API | `curl http://$IP/v1/chat/completions -H "X-API-Key: $API_KEY" ...` |
| Index docs into RAG | `curl -X POST http://$IP/rag/index -H "X-API-Key: $API_KEY" -d '{"documents":["..."]}'` |
| Query RAG | `curl -X POST http://$IP/rag/query -H "X-API-Key: $API_KEY" -d '{"query":"..."}'` |
| Re-index seeds | `make seed-rag` |
| Tail logs | `make logs` |
| Check status | `make status` |
| SSH | `make ssh` |
| Update config | edit Ansible roles, then `make ansible-deploy` |
| Destroy | `make down` |

---

## 9. Troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| `terraform apply` errors `Out of host capacity` repeatedly | A1 capacity exhausted in chosen region | Change `TF_VAR_region` to `ap-singapore-1` and re-run |
| `cloud-init status --wait` returns error | dnf failure on first boot | `make ssh`, inspect `/var/log/cloud-init-output.log` |
| Ansible `model` role: HF returns 403 | License not accepted or wrong repo | Use community mirror (default in `variables.tf`) |
| `llama` service won't start | Model not at expected path | `make ssh` and check `/opt/llama/models/` |
| Open WebUI loads but says "no models" | `OPENAI_API_BASE_URLS` wrong, or llama.cpp not exposing `/v1` | `make ssh -- "curl -s http://127.0.0.1:8081/v1/models \| jq ."` |
| `/v1/...` returns 401 with right key | Header name typo | Use exact `X-API-Key` |
| `/rag/query` returns 409 "collection is empty" | Seeding failed | `make seed-rag` |
| RAG `sentence-transformers` first-run download fails | Network blip | `make ssh`, then `sudo systemctl restart rag` (model cached after first success) |
| Inference very slow (<2 tokens/s) | Wrong shape config | OCI console: VM must show 4 OCPU / 24 GB |

Useful one-liners:

```bash
make ssh -- sudo journalctl -u llama -n 100 --no-pager
make ssh -- sudo podman ps -a
make ssh -- free -h
make ssh -- "curl -s http://127.0.0.1:8081/v1/models | jq ."
```

---

## 10. Cost guardrails

All resources used are within Always Free limits:

- 1x VM.Standard.A1.Flex with 4 OCPU / 24 GB - free (tenancy limit: 4 OCPU + 24 GB total across A1)
- 50 GB boot volume - free (limit: 200 GB total)
- 1x Object Storage bucket with one ~2 GB object - free (limit: 20 GB)
- 1x VCN + IGW + 1 PAR - free
- Outbound network - free up to 10 TB/month

If a second A1 instance is added, the 4 OCPU / 24 GB pool is shared - don't exceed it.

---

## 11. Success criteria checklist

The runbook is complete when ALL are true:

- [ ] `make check` passes
- [ ] `terraform apply` succeeded; `public_ip` output present
- [ ] `ansible/inventory.yml` was generated
- [ ] `ansible-playbook site.yml` completed with no failed tasks
- [ ] `curl http://$PUBLIC_IP/health` returns `ok`
- [ ] `curl http://$PUBLIC_IP/v1/chat/completions ...` returns valid JSON with content
- [ ] Without `X-API-Key`, `/v1/*` returns 401
- [ ] `curl http://$PUBLIC_IP/rag/query ...` returns an `answer` field
- [ ] `http://$PUBLIC_IP/` loads the Open WebUI sign-up screen
- [ ] `make logs` shows all three units (llama, webui, rag) running cleanly
- [ ] `make down` cleanly destroys everything

---

## 12. References

- OCI Terraform provider: https://registry.terraform.io/providers/oracle/oci/latest/docs
- OCI Object Storage PAR: https://docs.oracle.com/en-us/iaas/Content/Object/Tasks/usingpreauthenticatedrequests.htm
- OCI quantized GGUF reference architecture: https://docs.oracle.com/en/solutions/run-quantized-gguf-llm-ampere-cluster/index.html
- Ampere-optimized llama.cpp: https://github.com/AmpereComputingAI/llama.cpp
- llama.cpp server API: https://github.com/ggerganov/llama.cpp/tree/master/examples/server
- Open WebUI docs: https://docs.openwebui.com/
- Open WebUI image: https://github.com/open-webui/open-webui/pkgs/container/open-webui
- ChromaDB: https://docs.trychroma.com/
- sentence-transformers: https://www.sbert.net/
- OCI Always Free: https://www.oracle.com/cloud/free/

---

**End of runbook.** Codex should: create files in section 3 layout, populate per sections 4-6, then execute section 7. Report section 11 checklist when finished.
