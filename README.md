# order-service

Microsserviço de **registro de transações de ordens de serviço**, em Python 3.12 + FastAPI. Cria ordens de forma idempotente, valida o solicitante no `requester-service` e publica o evento `OrderCreated` de forma confiável via outbox pattern.