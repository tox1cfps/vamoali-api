# VamoAli API

API Flask para organizar lugares que um casal deseja conhecer. O frontend estatico e servido pelo proprio Flask e usa
a mesma origem da API. A persistencia em Google Sheets e uma escolha demonstrativa adequada ao portfolio, nao a uma
aplicacao com volume ou concorrencia elevados.

## Arquitetura

O backend segue o fluxo `Controller -> Service -> Repository`:

- `controllers/`: rotas HTTP e conversao de erros em respostas da API.
- `services/`: autenticacao, autorizacao por proprietario e regras de lugares.
- `repositories/`: leitura e escrita das abas `users` e `places` no Google Sheets.
- `middleware/`: validacao do JWT.
- `utils/`: cliente Sheets, criptografia Fernet e validacao de entrada.

Nome de usuario e email sao criptografados com Fernet antes de serem persistidos. Senhas usam bcrypt. A recuperacao de
senha envia por Brevo SMTP um link com token aleatorio de uso unico; somente o hash do token fica armazenado.

## Executando localmente

Requer Python 3.11.

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip setuptools
pip install -r requirements-dev.txt
```

Crie um `.env` local a partir de `.env.example`. Nunca versione `.env` ou `credentials.json`. Para desenvolvimento,
use `GOOGLE_APPLICATION_CREDENTIALS` apontando para um arquivo local fora do repositorio ou defina
`GOOGLE_CREDENTIALS_JSON`. Gere `FERNET_KEY` com `Fernet.generate_key()` e use um `JWT_SECRET` aleatorio com pelo menos
32 caracteres. Como a planilha e aberta pelo nome configurado em `SHEET_NAME`, a integracao solicita acesso de escrita
ao Sheets e leitura do Drive para localizar esse arquivo.

```bash
flask --app app run
```

Abra `http://localhost:5000`. Para ativar recuperacao de senha, configure as variaveis SMTP da Brevo e defina
`ENABLE_PASSWORD_RESET=true`. Em desenvolvimento local use `SMTP_PORT=587`; no Render gratuito use `SMTP_PORT=2525`.

O cache de login usa Redis quando `REDIS_URL` esta configurada. Sem essa variavel, a aplicacao usa um cache local em
memoria apenas para desenvolvimento/testes. Para producao, cadastre no provedor:

```bash
REDIS_URL=rediss://default:SENHA@HOST:PORT
LOGIN_CACHE_TTL_SECONDS=900
```

O cache acelera a busca do usuario no login, mas a senha continua sendo validada com bcrypt a cada tentativa.

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

- Google Sheets nao oferece transacoes adequadas para alta concorrencia; PostgreSQL e a evolucao natural.
- Rate limiting com Redis, logs estruturados e revogacao de JWT estao planejados para uso alem do portfolio.
- Tokens de reset ficam em memoria; use Redis ou banco antes de executar mais de uma instancia da API.
- O frontend ainda armazena o JWT em `localStorage`; cookies seguros com protecao CSRF sao uma evolucao futura.
