# leoai

Starter para executar um assistente de IA na OCI com:
- CLI local
- API FastAPI com auth
- RAG simples em JSON
- Ingestao de Object Storage e Web
- Provisionamento com Terraform + Ansible

## Arquitetura
- Documento completo em ASCII: [`ARCHITECTURE.md`](./ARCHITECTURE.md)

## Requisitos
- Python 3.9+
- Terraform 1.6+
- Ansible (para deploy remoto)
- Acesso OCI com permissoes para:
  - Compute
  - Networking
  - Generative AI Inference
  - Object Storage (se usar ingestao)

## Setup local rapido
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

Edite `.env` com pelo menos:
- `OCI_REGION`
- `OCI_COMPARTMENT_ID`
- `OCI_GENAI_MODEL_ID`
- `LEOAI_API_AUTH_KEY` (minimo 12 chars quando auth habilitada)

## Executar
CLI:
```bash
leoai
```

API:
```bash
uvicorn leoai.api:app --host 0.0.0.0 --port 8000
```

GUI local:
- `http://localhost:8000`
- Health: `http://localhost:8000/health`

## Variaveis principais (.env)
```dotenv
OCI_AUTH_MODE=instance_principal
OCI_REGION=eu-madrid-1
OCI_COMPARTMENT_ID=ocid1.compartment.oc1..xxxx
OCI_GENAI_MODEL_ID=cohere.command-a
OCI_API_FORMAT=COHERE
OCI_COHERE_SAFETY_MODE=OFF

LEOAI_API_AUTH_ENABLED=true
LEOAI_API_AUTH_KEY=troque_por_uma_chave_forte

WEB_SEARCH_ENABLED=true
WEB_SEARCH_MAX_RESULTS=5

RAG_ENABLED=true
RAG_STORE_PATH=/opt/leoai/data/knowledge_base.json

OCI_TEMPERATURE=0.2
OCI_TOP_P=0.75
OCI_MAX_TOKENS=600
```

Validacoes importantes em runtime:
- `OCI_AUTH_MODE`: `instance_principal` ou `api_key`
- `OCI_API_FORMAT`: `GENERIC` ou `COHERE`
- `OCI_COHERE_SAFETY_MODE`: fixo `OFF` (politica do projeto)
- `WEB_SEARCH_MAX_RESULTS`: 1..10
- `OCI_TEMPERATURE`: 0..2
- `OCI_TOP_P`: >0 e <=1
- `OCI_MAX_TOKENS`: 1..4096

## Endpoints
- `GET /health`
- `GET /auth/verify` (exige `X-API-Key` quando auth habilitada)
- `POST /chat`
- `POST /rag/ingest/object-storage`
- `POST /rag/ingest/web`
- `GET /rag/sources`

## Infra e deploy
- Terraform: [`terraform/README.md`](./terraform/README.md)
- Ansible: [`ansible/README.md`](./ansible/README.md)
- Pipeline local: [`scripts/bootstrap_infra.sh`](./scripts/bootstrap_infra.sh)

Fluxo curto:
```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# editar valores reais

cd terraform
terraform init
terraform apply

cd ../ansible
# editar group_vars/all.yml com valores reais e chave forte
ansible-playbook -i inventory/hosts.ini playbooks/bootstrap.yml
ansible-playbook -i inventory/hosts.ini playbooks/deploy.yml
```

## Higiene e seguranca
- Nao commitar arquivos locais de credenciais/estado:
  - `terraform/terraform.tfvars`
  - `terraform/.oci-config-temp`
  - `ansible/inventory/hosts.ini`
  - `*.tfstate`
- O repositório contem apenas templates/samples, sem secrets reais.

## Testes
```bash
.venv/bin/pytest -q
```

## CI
Pipeline GitHub Actions roda testes Python em `push` e `pull_request`.
