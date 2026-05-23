#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$ROOT_DIR/terraform"
ANSIBLE_DIR="$ROOT_DIR/ansible"

TF_VARS_FILE="terraform.tfvars"
INVENTORY_FILE="inventory/hosts.ini"
PLAN_ONLY=false
SKIP_TERRAFORM=false
SKIP_ANSIBLE=false

if [[ -t 1 && "${NO_COLOR:-0}" != "1" ]]; then
  C_RST="$(printf '\033[0m')"
  C_BOLD="$(printf '\033[1m')"
  C_BLUE="$(printf '\033[34m')"
  C_GREEN="$(printf '\033[32m')"
  C_YELLOW="$(printf '\033[33m')"
  C_RED="$(printf '\033[31m')"
else
  C_RST=""
  C_BOLD=""
  C_BLUE=""
  C_GREEN=""
  C_YELLOW=""
  C_RED=""
fi

STEP_NAMES=()
STEP_STATUS=()
STEP_SECONDS=()
STEP_LOGS=()
LOG_DIR=""
SUMMARY_PRINTED=false

usage() {
  cat <<'EOF'
Usage: scripts/bootstrap_infra.sh [options]

Options:
  --plan-only                 Run Terraform init+plan only (skip apply and Ansible)
  --skip-terraform            Skip Terraform stages
  --skip-ansible              Skip Ansible stages
  --tfvars <file>             Terraform vars file inside terraform/ (default: terraform.tfvars)
  --inventory <file>          Inventory file inside ansible/ (default: inventory/hosts.ini)
  -h, --help                  Show this help
EOF
}

line() {
  printf '%s\n' "--------------------------------------------------------------------------------"
}

section() {
  line
  printf "%b%s%b\n" "$C_BOLD$C_BLUE" "$1" "$C_RST"
  line
}

info() {
  printf "%b[info]%b %s\n" "$C_BLUE" "$C_RST" "$1"
}

ok() {
  printf "%b[ok]%b %s\n" "$C_GREEN" "$C_RST" "$1"
}

warn() {
  printf "%b[warn]%b %s\n" "$C_YELLOW" "$C_RST" "$1"
}

err() {
  printf "%b[error]%b %s\n" "$C_RED" "$C_RST" "$1"
}

record_step() {
  STEP_NAMES+=("$1")
  STEP_STATUS+=("$2")
  STEP_SECONDS+=("$3")
  STEP_LOGS+=("$4")
}

run_step() {
  local name="$1"
  local logfile="$2"
  shift 2

  local start_ts end_ts duration
  start_ts="$(date +%s)"

  section "$name"
  info "Log file: $logfile"
  if "$@" > >(tee "$logfile") 2> >(tee -a "$logfile" >&2); then
    end_ts="$(date +%s)"
    duration="$((end_ts - start_ts))"
    record_step "$name" "SUCCESS" "$duration" "$logfile"
    ok "$name finished in ${duration}s"
    return 0
  fi

  end_ts="$(date +%s)"
  duration="$((end_ts - start_ts))"
  record_step "$name" "FAILED" "$duration" "$logfile"
  err "$name failed after ${duration}s"
  return 1
}

print_summary() {
  SUMMARY_PRINTED=true
  section "Pipeline Summary"
  printf "%-28s | %-8s | %-7s | %s\n" "Step" "Status" "Time(s)" "Log"
  line
  local i
  for i in "${!STEP_NAMES[@]}"; do
    printf "%-28s | %-8s | %-7s | %s\n" \
      "${STEP_NAMES[$i]}" "${STEP_STATUS[$i]}" "${STEP_SECONDS[$i]}" "${STEP_LOGS[$i]}"
  done
  line
}

on_exit() {
  local exit_code=$?
  if [[ "$SUMMARY_PRINTED" == false && ${#STEP_NAMES[@]} -gt 0 ]]; then
    print_summary
  fi
  if [[ $exit_code -ne 0 ]]; then
    err "Pipeline exited with errors."
  fi
}

trap on_exit EXIT

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plan-only)
      PLAN_ONLY=true
      SKIP_ANSIBLE=true
      shift
      ;;
    --skip-terraform)
      SKIP_TERRAFORM=true
      shift
      ;;
    --skip-ansible)
      SKIP_ANSIBLE=true
      shift
      ;;
    --tfvars)
      TF_VARS_FILE="${2:-}"
      shift 2
      ;;
    --inventory)
      INVENTORY_FILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      err "Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$TF_VARS_FILE" || -z "$INVENTORY_FILE" ]]; then
  err "Invalid empty value for --tfvars or --inventory."
  usage
  exit 1
fi

RUN_ID="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="${TMPDIR:-/tmp}/leoai-deploy-${RUN_ID}"
mkdir -p "$LOG_DIR"

section "LeoAI Infra Pipeline"
info "Workspace: $ROOT_DIR"
info "Run ID: $RUN_ID"
info "Logs: $LOG_DIR"

if [[ "$SKIP_TERRAFORM" == false ]]; then
  cd "$TF_DIR"

  if [[ ! -f "$TF_VARS_FILE" ]]; then
    err "Terraform vars file not found: $TF_DIR/$TF_VARS_FILE"
    err "Copy terraform.tfvars.example and fill real values first."
    exit 1
  fi

  run_step "Terraform Init" "$LOG_DIR/terraform-init.log" \
    terraform init -no-color

  run_step "Terraform Plan" "$LOG_DIR/terraform-plan.log" \
    terraform plan -no-color -var-file="$TF_VARS_FILE"

  if [[ "$PLAN_ONLY" == false ]]; then
    run_step "Terraform Apply" "$LOG_DIR/terraform-apply.log" \
      terraform apply -auto-approve -no-color -var-file="$TF_VARS_FILE"
  else
    warn "Plan-only mode enabled. Skipping terraform apply and ansible stages."
  fi
fi

if [[ "$SKIP_ANSIBLE" == false ]]; then
  cd "$ANSIBLE_DIR"

  if [[ ! -f "$INVENTORY_FILE" ]]; then
    err "Inventory file not found: $ANSIBLE_DIR/$INVENTORY_FILE"
    err "Set generate_ansible_inventory=true in Terraform or create inventory manually."
    exit 1
  fi

  run_step "Ansible Bootstrap" "$LOG_DIR/ansible-bootstrap.log" \
    env ANSIBLE_HOST_KEY_CHECKING=False \
    ANSIBLE_LOCAL_TEMP=/private/tmp/ansible-local \
    TMPDIR=/private/tmp \
    ansible-playbook -i "$INVENTORY_FILE" playbooks/bootstrap.yml

  run_step "Ansible Deploy" "$LOG_DIR/ansible-deploy.log" \
    env ANSIBLE_HOST_KEY_CHECKING=False \
    ANSIBLE_LOCAL_TEMP=/private/tmp/ansible-local \
    TMPDIR=/private/tmp \
    ansible-playbook -i "$INVENTORY_FILE" playbooks/deploy.yml
fi

print_summary

ok "Infra + bootstrap + deploy completed."
