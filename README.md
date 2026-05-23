# leoai

Projeto inicial do seu novo AI com interface via terminal usando OpenAI.

## O que já vem pronto
- Estrutura Python organizada em `src/leoai`
- Configuração via `.env`
- CLI interativa para conversar com o modelo
- Remote Git apontando para `leandro-michelino/leoai`

## Requisitos
- Python 3.10+

## Setup rápido
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Depois, edite o `.env` e adicione sua chave da OpenAI.

## Rodar
```bash
leoai
```

Digite mensagens normalmente.
- `sair` ou `exit` para encerrar.

## Próximos passos sugeridos
- Adicionar memória de conversas
- Expor API com FastAPI
- Adicionar testes de integração

## Boas práticas de Git remoto aplicadas
- CI no GitHub Actions para rodar testes em `push` e `pull_request`
- Template de Pull Request em `.github/pull_request_template.md`
- `CODEOWNERS` para ownership e revisão

## Preparativos de infraestrutura (Terraform + Ansible)
- Terraform em [`terraform/`](./terraform)
- Ansible em [`ansible/`](./ansible)
- Script de orquestração em [`scripts/bootstrap_infra.sh`](./scripts/bootstrap_infra.sh)

### Fluxo rápido
```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# editar terraform/terraform.tfvars com seus OCIDs e parametros

cd terraform
terraform init
terraform apply

cd ../ansible
cp inventory/hosts.ini.example inventory/hosts.ini  # se Terraform nao gerar automaticamente
ansible-playbook playbooks/bootstrap.yml
ansible-playbook playbooks/deploy.yml
```
