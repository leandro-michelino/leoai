# Ansible

Automatiza bootstrap e deploy da aplicacao na VM provisionada pelo Terraform.

## Fluxo recomendado
1. Gere/provisione a VM com Terraform.
2. Confirme o inventario em `inventory/hosts.ini`.
3. Rode bootstrap:
   ```bash
   ansible-playbook playbooks/bootstrap.yml
   ```
4. Rode deploy:
   ```bash
   ansible-playbook playbooks/deploy.yml
   ```

## Observacao
- O playbook cria `.env` com placeholder de chave OpenAI. Atualize no servidor apos o deploy.
