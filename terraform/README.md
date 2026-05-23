# Terraform (OCI)

Provisiona a infraestrutura base para executar o LeoAI em uma VM OCI.

## Pré-requisitos
- Terraform 1.6+
- OCI CLI autenticado (`oci setup config`)
- Chave SSH publica local

## Fluxo
1. Copie o arquivo de exemplo:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```
2. Preencha os OCIDs e parametros reais.
3. Execute:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

Se `generate_ansible_inventory=true`, o arquivo `../ansible/inventory/hosts.ini` sera gerado automaticamente.
