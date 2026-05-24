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
  - configura `systemd` do backend (`uvicorn` em loopback)
  - configura `nginx` como reverse proxy publico
  - configura TLS (`self_signed` ou `letsencrypt`)
  - ajusta `firewalld` para 22/80/443

## Fluxo recomendado
1. Provisione VM com Terraform.
2. Confirme/gerar inventario em `inventory/hosts.ini`.
3. Edite `group_vars/all.yml` com valores reais:
- `leoai_oci_region`
- `leoai_oci_compartment_id`
- `leoai_api_auth_key`
- `leoai_tls_mode`
- `leoai_tls_domain` e `leoai_tls_email` (se `letsencrypt`)
4. Rode bootstrap:
```bash
ansible-playbook -i inventory/hosts.ini playbooks/bootstrap.yml
```
5. Rode deploy:
```bash
ansible-playbook -i inventory/hosts.ini playbooks/deploy.yml
```

## TLS modes
- `self_signed`: gera certificado local para subir HTTPS imediatamente.
- `letsencrypt`: emite certificado valido (exige dominio apontando para a VM).
- `disabled`: somente HTTP no reverse proxy.

## Seguranca
- `leoai_api_auth_key` default e placeholder e falha por design no deploy.
- Defina uma chave forte (>=12 chars) antes de executar.
- Nao commitar inventario real nem credenciais.

## Pre-requisitos OCI
Para `instance_principal` funcionar:
- instancia no Dynamic Group correto
- policy permitindo uso do Generative AI Inference no compartment alvo
