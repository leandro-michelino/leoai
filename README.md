# leoai

Starter para executar um assistente de IA na OCI com:
- CLI local
- API FastAPI com auth
- RAG v2 (embeddings + reranking híbrido)
- Ingestao de Object Storage e Web
- Upload multi-arquivo (ate 10) com extracao por tipo e indexacao async
- Chat com streaming SSE
- Reverse proxy Nginx com TLS
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

LEOAI_API_AUTH_ENABLED=false
LEOAI_API_AUTH_KEY=troque_por_uma_chave_forte

WEB_SEARCH_ENABLED=true
WEB_SEARCH_MAX_RESULTS=5

RAG_ENABLED=true
RAG_STORE_PATH=/opt/leoai/data/knowledge_base.json
RAG_EMBEDDINGS_ENABLED=true
RAG_EMBEDDING_MODEL_ID=cohere.embed-multilingual-v3.0
RAG_RERANK_ALPHA=0.65
RAG_CHUNK_SIZE=1200
RAG_CHUNK_OVERLAP=180
RAG_DEFAULT_TOP_K=5

FILES_STORE_DIR=/opt/leoai/data/files/uploads
GENERATED_STORE_DIR=/opt/leoai/data/files/generated
FILES_INDEX_PATH=/opt/leoai/data/files/index.json
MAX_UPLOAD_SIZE_MB=100

OCI_TEMPERATURE=0.2
OCI_TOP_P=0.75
OCI_MAX_TOKENS=600
```

Validacoes importantes em runtime:
- `OCI_AUTH_MODE`: `instance_principal` ou `api_key`
- `OCI_API_FORMAT`: `GENERIC` ou `COHERE`
- `OCI_COHERE_SAFETY_MODE`: fixo `OFF` (politica do projeto)
- `LEOAI_API_AUTH_ENABLED=false`: modo automático da dashboard (sem key manual)
- `WEB_SEARCH_MAX_RESULTS`: 1..10
- `RAG_RERANK_ALPHA`: 0..1
- `RAG_CHUNK_SIZE`: 200..4000
- `RAG_CHUNK_OVERLAP`: >=0 e menor que `RAG_CHUNK_SIZE`
- `RAG_DEFAULT_TOP_K`: 1..20
- `MAX_UPLOAD_SIZE_MB`: 1..1024
- `OCI_TEMPERATURE`: 0..2
- `OCI_TOP_P`: >0 e <=1
- `OCI_MAX_TOKENS`: 1..4096

## Endpoints
- `GET /health`
- `GET /auth/verify` (exige `X-API-Key` quando auth habilitada)
- `POST /chat`
- `POST /chat/stream` (SSE)
- `POST /chat/export`
- `POST /rag/ingest/object-storage`
- `POST /rag/ingest/web`
- `GET /rag/sources`
- `POST /rag/search`
- `POST /files/upload` (ate 10 arquivos por request)
- `GET /files`
- `GET /files/{file_id}/download`
- `POST /files/generate`
- `POST /jobs/rag-index-files`
- `GET /jobs`
- `GET /jobs/{job_id}`

## Infra e deploy
- Terraform: [`terraform/README.md`](./terraform/README.md)
- Ansible: [`ansible/README.md`](./ansible/README.md)
- Pipeline local: [`scripts/bootstrap_infra.sh`](./scripts/bootstrap_infra.sh)
  - inclui resumo bonito por etapa + highlights finais (IP, URLs e comandos úteis)
  - no fim do Ansible, a saida inclui Dashboard/Health/Auth verify prontas para handover

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

Se `leoai_tls_mode=letsencrypt`:
- configure DNS do dominio apontando para o IP publico da VM antes do deploy;
- informe `leoai_tls_domain` e `leoai_tls_email`;
- o playbook cria renovacao automatica (`certbot renew`) com reload do Nginx.

## Higiene e seguranca
- Nao commitar arquivos locais de credenciais/estado:
  - `terraform/terraform.tfvars`
  - `terraform/.oci-config-temp`
  - `ansible/inventory/hosts.ini`
  - `*.tfstate`
- O repositorio contem apenas templates/samples, sem secrets reais.

## Testes
```bash
.venv/bin/pytest -q
```

## CI
Pipeline GitHub Actions roda testes Python em `push` e `pull_request`.
