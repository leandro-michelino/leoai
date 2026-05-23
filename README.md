# leoai

Projeto inicial do seu AI rodando 100% na OCI (OCI Generative AI).

## O que já vem pronto
- CLI interativa em `src/leoai`
- API FastAPI (`/health` e `/chat`)
- Configuração OCI via `.env`
- Infra com Terraform + Ansible
- Remote Git apontando para `leandro-michelino/leoai`

## Requisitos
- Python 3.10+
- Acesso OCI com permissão para OCI Generative AI

## Setup rápido local
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Edite `.env` com `OCI_REGION`, `OCI_COMPARTMENT_ID` e `OCI_GENAI_MODEL_ID`.

## Rodar CLI
```bash
leoai
```

## Rodar API
```bash
uvicorn leoai.api:app --host 0.0.0.0 --port 8000
```

## .env para 100% OCI (Instance Principal)
```dotenv
OCI_AUTH_MODE=instance_principal
OCI_REGION=eu-madrid-1
OCI_COMPARTMENT_ID=ocid1.compartment.oc1..xxxx
OCI_GENAI_MODEL_ID=cohere.command-a
OCI_API_FORMAT=COHERE
OCI_COHERE_SAFETY_MODE=OFF
```

Observacao: confirme no console da OCI se `cohere.command-a` esta disponivel na sua regiao.

## Payload exato (Cohere com menos guardrails)
Use este formato quando quiser Cohere com `safety_mode=OFF`:
```python
chat_details = oci.generative_ai_inference.models.ChatDetails(
    compartment_id=OCI_COMPARTMENT_ID,
    serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(
        model_id="cohere.command-a"
    ),
    chat_request=oci.generative_ai_inference.models.CohereChatRequest(
        message="Seu prompt aqui",
        safety_mode="OFF",
        temperature=0.2,
        top_p=0.75,
        max_tokens=600,
        is_stream=False,
    ),
)
```

## IAM mínimo (OCI)
- Coloque a VM em um Dynamic Group.
- Crie policy permitindo esse Dynamic Group usar o serviço Generative AI Inference no compartment alvo.

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

## Boas práticas de Git remoto aplicadas
- CI no GitHub Actions para testes em `push` e `pull_request`
- Template de Pull Request em `.github/pull_request_template.md`
- `CODEOWNERS` para ownership e revisão
