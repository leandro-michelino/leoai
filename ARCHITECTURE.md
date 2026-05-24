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
              |                       | - /rag/sources                       |
              v                       +-------------------+------------------+
      +-------+-------------------+                       |
      | LeoAIAssistant            |<----------------------+
      | - monta prompt/contexto   |
      | - formato COHERE/GENERIC  |
      +-------+-------------------+
              |
              v
      +-------+-----------------------------------------------+
      | OCI Generative AI Inference                           |
      | - chat model                                          |
      | - embed model (RAG v2)                                |
      +-------------------------------------------------------+
```

## 2) Exposicao publica (Nginx + TLS)

```text
Internet
   |
   +--> 80  (redirect)
   +--> 443 (TLS)
           |
           v
      +----+------------------+
      | Nginx reverse proxy   |
      | - rate limit /chat    |
      | - security headers    |
      +----+------------------+
           |
           v
      127.0.0.1:8000
      (uvicorn / FastAPI)
```

## 3) Pipeline de contexto (RAG v2 + Web)

```text
User prompt
   |
   v
/chat
   |
   +--> with_web=true  --> DuckDuckGo API (web_search.py)
   |
   +--> with_rag=true
           |
           v
     KnowledgeBase JSON
           |
           +--> lexical score (tokens)
           +--> semantic score (cosine embedding)
           +--> reranking hibrido (alpha)
           |
           v
     Contexto final para o modelo
```

## 4) Ingestao de fontes

```text
/rag/ingest/object-storage --> OCI Object Storage --> texto --> embedding --> KnowledgeBase JSON
/rag/ingest/web            --> URL http/https      --> texto --> embedding --> KnowledgeBase JSON
```

## 5) Infraestrutura OCI (Terraform)

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
                      | NSG (22/80/443)      |            | Route Table privada   |
                      +--+-------------------+            | 0.0.0.0/0 -> NAT GW   |
                         |                                | OCI Services -> SGW    |
                         |                                +-----------+------------+
                 +-------v--------+                                   |
                 | OCI Instance   |                            +------v------+
                 | LeoAI + Nginx  |                            | NAT + SGW    |
                 +----------------+                            +-------------+
```

## 6) Deploy (Ansible)

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
   - instala/configura nginx
   - configura TLS (self_signed ou letsencrypt)
   - restart dos servicos
```
