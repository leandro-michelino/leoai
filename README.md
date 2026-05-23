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
