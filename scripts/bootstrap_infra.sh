#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR/terraform"

if [[ ! -f terraform.tfvars ]]; then
  echo "[erro] terraform.tfvars nao encontrado. Copie terraform.tfvars.example e preencha os valores."
  exit 1
fi

terraform init
terraform apply -auto-approve

cd "$ROOT_DIR/ansible"

if [[ ! -f inventory/hosts.ini ]]; then
  echo "[erro] inventory/hosts.ini nao encontrado."
  echo "Use generate_ansible_inventory=true no Terraform ou preencha manualmente inventory/hosts.ini."
  exit 1
fi

ansible-playbook playbooks/bootstrap.yml
ansible-playbook playbooks/deploy.yml

echo "[ok] Infra + bootstrap + deploy executados."
