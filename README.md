# order-service

Microsserviço de **registro de transações de ordens de serviço**, escrito em **Python 3.12 + FastAPI**. Cria ordens de forma idempotente, valida o solicitante ("requester") junto ao [`requester-service`](https://github.com/itau-desafio-tecnico/requester-service/blob/main/README.md) e publica o evento `OrderCreated` de forma confiável através de um **outbox pattern** com envio para o Amazon SNS.

## Sumário

- [Escopo](#escopo)
- [Stack de tecnologia](#stack-de-tecnologia)
- [Arquitetura](#arquitetura)
- [Fluxos](#fluxos)
- [Endpoints](#endpoints)
- [Configuração](#configuração)
- [Como executar](#como-executar)
- [Testes](#testes)
- [CI/CD](#cicd)

## Escopo

O `order-service` é responsável por registrar **ordens de serviço**. Cada ordem referencia um `requester_id` (a entidade que solicita a ordem), que é validada em tempo real contra o serviço `requester-service`. Após a criação, o serviço publica de forma assíncrona e confiável um evento `OrderCreated` para um tópico SNS, permitindo que outros serviços reajam à criação da ordem sem acoplamento direto.

Principais garantias de negócio:

- **Idempotência**: requisições de criação repetidas com o mesmo par `Idempotency-Key` + `requester_id` retornam a ordem já existente, sem revalidar o solicitante nem publicar um novo evento. A mesma chave usada por solicitantes diferentes gera ordens distintas — a chave de idempotência é escopada por solicitante, nunca global.
- **Consistência**: a ordem e o evento de outbox são persistidos na mesma transação de banco de dados — o evento nunca é perdido mesmo que a publicação no SNS falhe.
- **Entrega confiável**: um dispatcher em background publica os eventos pendentes no SNS com retry e contagem de tentativas, marcando o evento como `FAILED` após esgotar as tentativas.
- **Seguro para múltiplas réplicas**: o dispatcher reivindica eventos via `SELECT ... FOR UPDATE SKIP LOCKED`, então rodar mais de uma instância do serviço (escalabilidade horizontal) não duplica publicações no SNS — cada evento é processado por uma única instância por vez.

## Stack de tecnologia

| Categoria | Tecnologia |
|---|---|
| Linguagem/runtime | Python 3.12 |
| Framework web | FastAPI 0.115, servido por Uvicorn |
| Validação/config | Pydantic 2.9 + pydantic-settings |
| ORM / driver DB | SQLAlchemy 2.0 + psycopg3 |
| Banco de dados | PostgreSQL 16 |
| Migrações | Liquibase 4.29 (changelogs YAML em `db/changelog`) |
| Cliente HTTP | httpx + tenacity (retry com backoff exponencial) |
| Mensageria | AWS SNS (boto3) — publisher via outbox pattern |
| Observabilidade | OpenTelemetry (traces e métricas via OTLP/HTTP) |
| Testes | pytest, pytest-asyncio, pytest-cov, respx |
| Empacotamento | Docker (multi-stage não aplicável — imagem única `python:3.12-slim`) |
| Licença | Apache License 2.0 |

## Arquitetura

O projeto segue **arquitetura hexagonal (ports & adapters) / clean architecture**, com o domínio isolado de frameworks:

```
src/
├── domain/              # Regras de negócio puras, sem dependências de framework
│   ├── entities.py         # Order, OrderStatus, OutboxEvent, OutboxStatus
│   ├── exceptions.py       # DomainError, RequesterNotFoundError, RequesterServiceError
│   └── ports.py            # Interfaces abstratas: OrderRepository, OutboxRepository,
│                            #   RequesterClient, EventPublisher
├── app/                 # Camada de aplicação (casos de uso)
│   └── create_order_use_case.py   # CreateOrderUseCase — orquestra domínio + ports
├── infra/               # Adapters que implementam os ports do domínio
│   ├── config.py               # Settings (pydantic-settings)
│   ├── telemetry.py             # Setup do OpenTelemetry
│   ├── db/                      # SQLAlchemy: modelos, repositórios, sessão
│   ├── http/                    # HttpRequesterClient (chama o requester-service)
│   └── message/                  # OutboxDispatcher + SnsEventPublisher
├── interfaces/          # Adapters de entrada (inbound)
│   └── api/
│       ├── routers/orders.py     # Rotas FastAPI
│       ├── schemas.py             # DTOs Pydantic
│       ├── dependencies.py        # Injeção de dependências (Depends)
│       └── error_handlers.py      # Handlers globais de exceção → respostas HTTP
└── main.py              # Composition root: app FastAPI, lifespan, telemetria, outbox dispatcher
```

A direção de dependência aponta sempre para dentro (`infra`/`interfaces` → `domain`). O domínio define os *ports* (classes abstratas) que os adapters de infraestrutura implementam; a camada `app` contém o único caso de uso do serviço e depende apenas dos ports do domínio.

## Fluxos

### Criação de ordem (síncrono, via HTTP)

1. Cliente chama `POST /py-order-service/orders` com header `Idempotency-Key` e corpo `{requester_id, description}`.
2. `CreateOrderUseCase` verifica se já existe uma ordem para o par `(idempotency_key, requester_id)` — se existir, retorna a ordem existente imediatamente (sem revalidar o solicitante nem gerar novo evento). A mesma `Idempotency-Key` usada por um `requester_id` diferente **não** é tratada como repetição — gera uma nova ordem normalmente.
3. Caso contrário, valida o solicitante chamando `GET {REQUESTER_SERVICE_URL}/requesters/{id}/validation` no `requester-service`, com até 3 tentativas e backoff exponencial em caso de erro de transporte.
   - Solicitante inexistente/inativo → `422 Unprocessable Entity`.
   - `requester-service` indisponível (5xx) → `503 Service Unavailable`.
4. Se válido, cria a `Order` (gera UUID e `order_number` no formato `OS-YYYYMMDD--XXXXXX`) e o `OutboxEvent` correspondente (`OrderCreated`).
5. Persiste **ordem e evento de outbox na mesma transação** de banco (transactional outbox pattern). Em caso de corrida (mesmo par `idempotency_key` + `requester_id` duplicado concorrentemente), faz rollback e retorna a ordem já existente. A unicidade é garantida no banco por uma constraint composta em `(idempotency_key, requester_id)`, não pela chave isolada.
6. Responde `201 Created` com os dados da ordem criada.

### Despacho assíncrono do outbox (background task)

- Ao subir, a aplicação inicia uma task assíncrona (`OutboxDispatcher`) que faz polling da tabela `outbox_events` a cada `outbox_poll_interval_seconds` (padrão 2s), reivindicando até 20 eventos por ciclo via `claim_pending`.
- O claim é atômico: numa única transação curta, seleciona eventos `PENDING` (ou `PROCESSING` presos além de `outbox_processing_timeout_seconds`, padrão 60s) com `SELECT ... FOR UPDATE SKIP LOCKED`, e já marca essas linhas como `PROCESSING` com `claimed_at = now()` antes de liberar o lock. Isso é o que permite rodar múltiplas instâncias do `order-service` (autoscaling) sem que duas instâncias publiquem o mesmo evento: cada uma só enxerga os eventos que a outra ainda não reivindicou, e o lock não fica preso durante a chamada de rede ao SNS.
- Se uma instância morrer no meio do processamento (ex.: task do ECS substituída em um deploy), o evento fica `PROCESSING` até `outbox_processing_timeout_seconds` expirar — depois disso, qualquer instância (a mesma ou outra) volta a reivindicá-lo no próximo ciclo, evitando perda silenciosa de evento.
- Para cada evento reivindicado, publica no tópico SNS configurado (`sns_topic_arn`) com atributos de mensagem `event_type`/`event_id`.
- Em caso de sucesso, marca o evento como `PUBLISHED`. Em caso de falha, incrementa `attempts` e volta o status para `PENDING`; ao atingir `outbox_max_attempts` (padrão 5), marca como `FAILED`.
- Este serviço **não consome mensagens** — atua apenas como produtor SNS. Não há Kafka/RabbitMQ/SQS neste projeto.

## Endpoints

Prefixo de contexto: **`/py-order-service`**.

| Método | Path | Descrição | Request | Respostas |
|---|---|---|---|---|
| `POST` | `/py-order-service/orders` | Cria uma ordem de serviço (idempotente) | Header `Idempotency-Key` (obrigatório); Body `{requester_id: UUID, description: string}` | `201` → `{order_number, requester_id, description, status, created_at}`; `422` solicitante inválido/inexistente ou body inválido; `503` `requester-service` indisponível |
| `GET` | `/py-order-service/health` | Health check (usado por ALB/ECS; excluído de logs de acesso e de traces/métricas) | — | `200` `{"status": "ok"}` |
| `GET` | `/py-order-service/apidocs` | Swagger UI | — | HTML |
| `GET` | `/py-order-service/openapi.json` | Especificação OpenAPI | — | JSON |

### Mensageria

- **Produtor**: publica o evento **`OrderCreated`** no tópico SNS configurado em `sns_topic_arn`, com o payload `{order_id, order_number, requester_id, description, status, created_at}`.
- Não há consumidores de fila neste serviço.

### Dependência externa

- Chama `GET {REQUESTER_SERVICE_URL}/requesters/{requester_id}/validation` no [`requester-service`](https://github.com/itau-desafio-tecnico/requester-service/blob/main/README.md) para validar o solicitante antes de criar a ordem.

## Configuração

Variáveis de ambiente (ver `src/infra/config.py`):

| Variável | Padrão | Descrição |
|---|---|---|
| `APP_NAME` | `py-order-service` | Prefixo das rotas HTTP |
| `DB_HOST` | `localhost` | Host do PostgreSQL |
| `DB_PORT` | `5432` | Porta do PostgreSQL |
| `DB_NAME` | `order_service` | Nome do banco |
| `DB_USER` | `postgres` | Usuário do banco |
| `DB_PASSWORD` | `postgres` | Senha do banco |
| `REQUESTER_SERVICE_URL` | `http://localhost:8001/jv-requester-service` | URL base do `requester-service` |
| `SNS_TOPIC_ARN` | `arn:aws:sns:sa-east-1:000000000000:order-created` | Tópico SNS para o evento `OrderCreated` |
| `AWS_REGION` | `sa-east-1` | Região AWS usada pelo cliente SNS |
| `OUTBOX_POLL_INTERVAL_SECONDS` | `2.0` | Frequência de polling do outbox dispatcher |
| `OUTBOX_MAX_ATTEMPTS` | `5` | Tentativas máximas de publicação antes de marcar `FAILED` |
| `OUTBOX_PROCESSING_TIMEOUT_SECONDS` | `60.0` | Tempo até um evento `PROCESSING` "preso" (instância morta no meio do processamento) voltar a ser reivindicável |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | `http://localhost:4318/v1/traces` | Endpoint OTLP para traces |
| `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` | `http://localhost:4318/v1/metrics` | Endpoint OTLP para métricas |

## Como executar

### Via Docker Compose (recomendado)

```bash
docker compose up
```

Sobe Postgres (porta host `5433`), roda as migrações do Liquibase automaticamente e inicia o `order-service` em `http://localhost:8000`. Pressupõe que `requester-service` e um `otel-collector` estejam acessíveis pelos hostnames configurados (ex.: em uma rede Docker compartilhada com o [`requester-service`](https://github.com/itau-desafio-tecnico/requester-service/blob/main/README.md)).

### Local (sem Docker)

```bash
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

Aponte as variáveis `DB_*` para uma instância PostgreSQL acessível e rode as migrações do Liquibase separadamente (changelogs em `db/changelog`).

## Testes

```bash
pytest --cov=src --cov-report=term-missing --cov-fail-under=80
```

- Framework: `pytest` + `pytest-asyncio` + `pytest-cov`.
- Gate de cobertura: 80% de linhas (exclui `src/interfaces/api/schemas.py` e `src/main.py`).
- Estrutura em `tests/unit/`, espelhando `src/` (`domain`, `app`, `infra`, `interfaces`), com mocks/fakes para os ports (repositórios, cliente HTTP, publisher SNS) — sem Testcontainers.

## CI/CD

Workflow `.github/workflows/ci.yml`: roda testes com gate de cobertura em push/PR para `main`; em push para `main`, constrói e publica as imagens Docker (`order-service` e a imagem de migração Liquibase) no Amazon ECR, executa a migração como task Fargate no ECS e força um novo deployment do serviço no cluster `desafio-dev-cluster`.
