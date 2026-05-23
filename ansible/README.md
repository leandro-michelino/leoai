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

## Observacoes
- O playbook cria `.env` com variaveis OCI (`OCI_AUTH_MODE`, `OCI_REGION`, `OCI_COMPARTMENT_ID`, `OCI_GENAI_MODEL_ID`).
- O deploy tambem escreve auth e RAG: `LEOAI_API_AUTH_*`, `RAG_*`, `WEB_SEARCH_*`.
- A variavel `leoai_api_auth_key` precisa estar definida com chave forte antes do deploy.
- Para `instance_principal`, garanta Dynamic Group + Policy do OCI Generative AI para a instancia.
