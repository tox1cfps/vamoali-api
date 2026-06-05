# VamoAli API

API Flask para organizar lugares que um casal deseja conhecer. O frontend estatico e servido pelo proprio Flask e usa
a mesma origem da API. PostgreSQL e a fonte principal de dados; Google Sheets recebe somente um relatorio diario
sanitizado para visualizacao e exportacao.

## Arquitetura

O backend segue o fluxo `Controller -> Service -> Repository`:

- `controllers/`: rotas HTTP e conversao de erros em respostas da API.
- `services/`: autenticacao, autorizacao por proprietario e regras de lugares.
- `repositories/`: persistencia PostgreSQL via SQLAlchemy.
- `workers/`: fila de emails, lembretes, relatorio Sheets e backup CSV.
- `middleware/`: validacao do JWT.
- `utils/`: cliente Sheets, criptografia Fernet e validacao de entrada.

Senhas usam bcrypt. A recuperacao de senha envia por Brevo SMTP um link com token aleatorio de uso unico. O hash fica
na tabela de tokens; o token bruto existe somente no payload criptografado da fila ate a entrega.

## Executando localmente

Requer Python 3.11.

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip setuptools
pip install -r requirements-dev.txt
```

Crie um `.env` local a partir de `.env.example`. Nunca versione `.env` ou `credentials.json`. Configure `DATABASE_URL`
e use um `JWT_SECRET` aleatorio com pelo menos 32 caracteres. As credenciais Google e `SHEET_NAME` sao necessarias
somente para importar os dados antigos; `REPORT_SHEET_NAME` habilita o relatorio diario sanitizado.

```bash
flask --app app run
```

Antes de iniciar, aplique o schema:

```bash
alembic upgrade head
```

Abra `http://localhost:5000`. Para ativar recuperacao de senha, configure as variaveis SMTP da Brevo e defina
`ENABLE_PASSWORD_RESET=true`. Em desenvolvimento local use `SMTP_PORT=587`; no Render gratuito use `SMTP_PORT=2525`.

### Executando com Docker

Com Docker e Docker Compose instalados, copie `.env.example` para `.env` e preencha os secrets reais quando necessario.
O Compose cria PostgreSQL, Redis, aplica as migrations e sobe a API em `http://localhost:5000`.

```bash
docker compose up --build
```

Para executar comandos dentro do container:

```bash
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m workers.email_worker
```

## Documentacao da API

A documentacao interativa Swagger fica disponivel em `http://localhost:5000/docs/`. O contrato OpenAPI 3 usado pela
interface pode ser consultado diretamente em `http://localhost:5000/openapi.json`.

Para testar rotas protegidas pela interface, autentique-se em `/auth/login`, copie o token retornado e use o botao
**Authorize** informando somente o token JWT. Os contratos de endpoints, corpos, respostas e schemas compartilhados
ficam centralizados em `docs/openapi.json`.

O cache de login usa Redis quando `REDIS_URL` esta configurada. Sem essa variavel, a aplicacao usa um cache local em
memoria apenas para desenvolvimento/testes. Para producao, cadastre no provedor:

```bash
REDIS_URL=rediss://default:SENHA@HOST:PORT
LOGIN_CACHE_TTL_SECONDS=900
```

O Redis acelera a busca do usuario no login. A senha continua sendo validada com bcrypt a cada tentativa.

## Workers e migracao

```bash
python -m workers.email_worker
python -m workers.schedule_unvisited_reminders
python -m workers.sync_sheets_report
python -m workers.backup_database
python -m scripts.import_sheets_to_postgres
```

O importador e idempotente e preserva IDs, hashes de senha, lugares, grupos e convites existentes. Execute primeiro em
um banco de homologacao e valide as contagens antes da troca final. O backup completo gera CSVs compactados, criptografa
com `BACKUP_ENCRYPTION_KEY` e os envia para `BACKUP_EMAIL`; o relatorio Sheets nao inclui emails, hashes, tokens ou IDs
de usuarios.

No plano gratuito do Render, somente o Web Service e o PostgreSQL sao provisionados. Boas-vindas e reset sao enviados
imediatamente pelo Web Service. O workflow `.github/workflows/scheduled-jobs.yml` chama um endpoint administrativo
protegido diariamente para enviar lembretes, reprocessar emails pendentes, atualizar o relatorio e gerar o backup.
Configure no GitHub Actions:

```text
VAMOALI_APP_URL=https://vamoali-app.onrender.com
ADMIN_JOB_SECRET=<mesmo valor configurado no Render>
```

A migracao real pode ser executada uma unica vez pelo endpoint protegido `POST /internal/jobs/migrate-sheets`.
Antes disso, configure no Web Service `SHEET_NAME`, `FERNET_KEY` e `GOOGLE_CREDENTIALS_JSON`. Consulte
`GET /internal/jobs/migration-status` para comparar automaticamente as contagens. O workflow manual
`.github/workflows/migrate-sheets.yml` executa ambos ao receber a confirmacao `MIGRATE`.

## Testes

Os testes usam mocks para Google Sheets e nao dependem da planilha real.

```bash
pytest
pytest --cov=. --cov-report=term-missing
black --check .
isort --check-only .
ruff check .
pip-audit -r requirements.txt
```

A configuracao em `pyproject.toml` exige cobertura global minima de 80%.

## Teste de performance

O cenário Locust em `performance/locustfile.py` mede os principais fluxos autenticados de leitura sem modificar dados.
As instrucoes para executar pela interface web ou em modo headless, incluindo limites automaticos de p95 e erros,
estao em `performance/README.md`.

## CI/CD

`.github/workflows/ci.yml` executa Black, Isort, Ruff, pytest com cobertura, `pip-audit` e secret scanning com Gitleaks.
Configure branch protection em `main` para exigir os checks do workflow.

`.github/workflows/deploy.yml` roda somente depois de um CI bem-sucedido em `main` e chama o deploy hook armazenado no
secret `RENDER_DEPLOY_HOOK_URL`. Credenciais da aplicacao devem ser cadastradas diretamente no provedor.

## Deploy

Para deploy manual em Render, Railway ou Fly.io:

1. Configure Python 3.11 e o build command `pip install -r requirements.txt`.
2. Configure o start command `gunicorn --bind 0.0.0.0:$PORT --access-logfile=- app:app`.
3. Cadastre os secrets descritos em `.env.example`, incluindo Brevo SMTP e `PASSWORD_RESET_URL`.
4. Configure o health check em `/health`.
5. Confirme HTTPS e execute os testes manuais de `DEPLOY_CHECKLIST.md`.

O arquivo `Procfile` registra o mesmo comando WSGI. O link da aplicacao publicada deve ser adicionado aqui depois da
criacao do ambiente.

## Limitacoes Conhecidas

- Rate limiting com Redis, logs estruturados e revogacao de JWT estao planejados para uso alem do portfolio.
- O frontend ainda armazena o JWT em `localStorage`; cookies seguros com protecao CSRF sao uma evolucao futura.
