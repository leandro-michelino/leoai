# Terraform (OCI)

Provisiona infraestrutura para rodar o LeoAI em VM OCI.

## O que este modulo cria
- 1 NSG com regras:
  - SSH (22) a partir de `laptop_ingress_cidr`
  - API (`leoai_api_port`) a partir de `laptop_ingress_cidr`
  - Egress liberado
- 1 instancia OCI com chave SSH local
- (Opcional) inventario Ansible em `../ansible/inventory/hosts.ini`
- (Opcional) topologia privada com NAT Gateway + Service Gateway + subnet privada

## Modos de rede
1. Publico
- `use_private_subnet_with_nat_sgw=false`
- VM usa `subnet_id` informado
- Pode receber IP publico (`assign_public_ip=true`)
- `create_service_gateway` pode ser `true` ou `false`

2. Privado recomendado
- `use_private_subnet_with_nat_sgw=true`
- Cria subnet privada no VCN alvo
- VM sem IP publico
- Cria NAT Gateway e Service Gateway
- `create_service_gateway` deve ser `true`

## Uso
1. Copie o exemplo:
```bash
cp terraform.tfvars.example terraform.tfvars
```
2. Preencha OCIDs e parametros.
3. Execute:
```bash
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

## Campos essenciais em terraform.tfvars
- `oci_region`
- `oci_config_profile`
- `compartment_id`
- `availability_domain`
- `subnet_id`
- `image_id`
- `ssh_public_key_path`
- `laptop_ingress_cidr`

## Outputs principais
- `instance_id`
- `instance_public_ip`
- `instance_private_ip`
- `effective_subnet_id`
- `ansible_inventory_file` (quando habilitado)
- `nat_gateway_id` (quando habilitado)
- `service_gateway_id` (quando habilitado)

## Observacoes
- `terraform.tfvars` e arquivos de estado nao devem ir para git.
- Para deploy com Ansible, valide o inventario gerado em `ansible/inventory/hosts.ini`.
