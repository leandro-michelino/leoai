# LeoAI Architecture (ASCII)

Este documento descreve a arquitetura atual do projeto de forma operacional.

## 1) Aplicacao (runtime)

```text
+---------------------------+         +--------------------------------------+
| CLI (leoai.cli)           |         | FastAPI (leoai.api)                  |
| - prompt interativo       |         | - /chat                              |
| - chama LeoAIAssistant    |         | - /auth/verify                       |
+-------------+-------------+         | - /rag/ingest/object-storage         |
              |                       | - /rag/ingest/web                    |
              |                       | - /rag/sources                        |
              v                       +-------------------+------------------+
      +-------+-------------------+                       |
      | LeoAIAssistant            |<----------------------+
      | - monta prompt/contexto   |
      | - escolhe formato COHERE  |
      |   ou GENERIC              |
      +-------+-------------------+
              |
              v
      +-------+-----------------------------------------------+
      | OCI Generative AI Inference                           |
      | endpoint: https://inference.generativeai.<region>... |
      +-------------------------------------------------------+
```

## 2) Pipeline de contexto (RAG + Web)

```text
                     +---------------------------------------+
User prompt -------->| /chat                                |
                     +-------------------+-------------------+
                                         |
                 with_rag=true           | with_web=true
                                         |
               +------------------+      v
               | KnowledgeBase    |  +----------------------+
               | JSON local       |  | DuckDuckGo API       |
               | retrieve_context |  | (web_search.py)      |
               +---------+--------+  +----------+-----------+
                         |                      |
                         +----------+-----------+
                                    v
                           Prompt enriquecido
                                    |
                                    v
                             LeoAIAssistant
```

## 3) Ingestao de fontes

```text
/rag/ingest/object-storage --> OCI Object Storage --> texto --> KnowledgeBase JSON
/rag/ingest/web            --> URL http/https      --> texto --> KnowledgeBase JSON
```

## 4) Infraestrutura OCI (Terraform)

```text
                         +------------------------------+
                         | VCN (existente via subnet_id)|
                         +---------------+--------------+
                                         |
                         +---------------+-----------------------------+
                         |                                             |
             use_private_subnet_with_nat_sgw=false         use_private_subnet_with_nat_sgw=true
                         |                                             |
             +-----------v----------+                      +-----------v----------+
             | Subnet alvo (exist.) |                      | Subnet privada nova  |
             | VM pode ter IP pub   |                      | VM sem IP publico    |
             +-----------+----------+                      +-----------+----------+
                         |                                             |
                      +--v-------------------+            +-----------v-----------+
                      | NSG (SSH + API CIDR) |            | Route Table privada   |
                      +--+-------------------+            | 0.0.0.0/0 -> NAT GW   |
                         |                                | OCI Services -> SGW    |
                         |                                +-----------+------------+
                 +-------v--------+                                   |
                 | OCI Instance   |                            +------v------+
                 | (LeoAI API)    |                            | NAT + SGW    |
                 +----------------+                            +-------------+
```

## 5) Deploy (Ansible)

```text
Terraform apply
   |
   +--> gera ansible/inventory/hosts.ini (opcional)
           |
           v
ansible bootstrap.yml
   - instala python/git/venv
           |
           v
ansible deploy.yml
   - git checkout repo
   - pip install (venv)
   - gera /opt/leoai/.env
   - instala systemd leoai-api.service
   - restart do servico
```
