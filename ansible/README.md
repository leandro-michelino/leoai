# Ansible

Automatiza bootstrap e deploy da aplicacao na VM criada pelo Terraform.

## Playbooks
- `playbooks/bootstrap.yml`
  - instala dependencias base do sistema
  - cria diretorio da aplicacao
- `playbooks/deploy.yml`
  - clona/atualiza repo
  - cria venv e instala projeto
  - escreve `.env` da app
  - configura e reinicia servico systemd

## Fluxo recomendado
1. Provisione VM com Terraform.
2. Confirme/gerar inventario em `inventory/hosts.ini`.
3. Edite `group_vars/all.yml` com valores reais:
- `leoai_oci_region`
- `leoai_oci_compartment_id`
- `leoai_api_auth_key`
4. Rode bootstrap:
```bash
ansible-playbook -i inventory/hosts.ini playbooks/bootstrap.yml
```
5. Rode deploy:
```bash
ansible-playbook -i inventory/hosts.ini playbooks/deploy.yml
```

## Seguranca
- `leoai_api_auth_key` default e placeholder e falha por design no deploy.
- Defina uma chave forte (>=12 chars) antes de executar.
- Nao commitar inventario real nem credenciais.

## Pre-requisitos OCI
Para `instance_principal` funcionar:
- instancia no Dynamic Group correto
- policy permitindo uso do Generative AI Inference no compartment alvo
