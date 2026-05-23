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
   - Defina `oci_config_profile` com o profile valido no seu `~/.oci/config` (ex.: `JNB`).
   - Defina `laptop_ingress_cidr` com seu IP publico em formato CIDR `/32`.
3. Execute:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

Se `generate_ansible_inventory=true`, o arquivo `../ansible/inventory/hosts.ini` sera gerado automaticamente.
