# Checklist de Deploy - VamoAli API

Este documento organiza o caminho para publicar o VamoAli como projeto academico de portfolio. O objetivo e fazer um deploy pequeno, demonstravel e responsavel, sem tratar o prototipo como uma aplicacao corporativa.

## Arquitetura recomendada

```text
GitHub
  -> plataforma de deploy
  -> pip install -r requirements.txt
  -> gunicorn app:app
  -> secrets configurados no painel
  -> HTTPS fornecido pela plataforma
  -> Flask serve API e frontend no mesmo dominio
  -> Google Sheets permanece como persistencia demonstrativa
```

Plataformas adequadas para este formato incluem Render, Railway e Fly.io.

## Bloqueadores antes do deploy

### 1. Substituir o reset matematico em producao

- [x] Remover o desafio matematico.
- [x] Criar a flag `ENABLE_PASSWORD_RESET=false`.
- [x] Bloquear a rota de reset quando a flag estiver desativada.
- [x] Ocultar o botao de reset quando a flag estiver desativada.
- [x] Implementar envio de link por Brevo SMTP.

Arquivos relacionados:

- `controllers/auth_controller.py`
- `services/auth_service.py`
- `static/auth.html`
- `static/app.js`

O mecanismo atual demonstra geracao, expiracao e consumo de token, mas nao comprova posse do email. Ele nao deve ficar acessivel em uma API publicada.

### 2. Corrigir mass assignment no PATCH de places

- [ ] Aplicar whitelist estrita no `PATCH /places/<place_id>`.
- [ ] Aceitar somente `visited` nesse endpoint ou remove-lo em favor do endpoint especializado.
- [ ] Rejeitar campos internos como `id`, `user_id`, `created_at`, `updated_at`, `feedback`, `rating` e `favorited`.
- [ ] Adicionar testes para tentativas de alteracao de `user_id` e `id`.

Arquivo principal:

- `services/place_service.py`

Exemplo:

```python
ALLOWED_PATCH_FIELDS = {"visited"}

def update_place(self, user_id, place_id, fields):
    unexpected = set(fields) - ALLOWED_PATCH_FIELDS
    if unexpected:
        raise ValueError("Campos nao permitidos")

    return self.place_repo.update_place(
        place_id,
        {"visited": self._parse_bool(fields["visited"])},
    )
```

### 3. Remover localhost fixo do frontend

- [ ] Trocar a URL absoluta da API por origem relativa.
- [ ] Testar login, cadastro e CRUD com frontend e API no mesmo dominio.

Arquivo:

- `static/app.js`

Alteracao:

```js
const API_URL = '';
```

### 4. Manter segredos fora do Git e do artefato

- [ ] Confirmar que `.env` e `credentials.json` continuam ignorados pelo Git.
- [ ] Nunca enviar `.env` ou `credentials.json` ao GitHub.
- [ ] Configurar `JWT_SECRET`, `FERNET_KEY` e `SHEET_NAME` como secrets no provedor.
- [ ] Armazenar a credencial Google como secret do provedor.
- [ ] Rotacionar a chave da service account caso ela ja tenha sido compartilhada.
- [ ] Revisar as permissoes da service account no Google Drive.
- [ ] Compartilhar somente a planilha necessaria.

Para um deploy simples de portfolio, uma opcao temporaria e usar uma variavel `GOOGLE_CREDENTIALS_JSON` contendo o JSON da service account. Em ambientes mais maduros, prefira identidade de workload ou secret manager.

### 5. Validar configuracao no startup

- [ ] Falhar imediatamente quando uma variavel obrigatoria estiver ausente.
- [ ] Validar entropia minima de `JWT_SECRET`.
- [ ] Validar formato da `FERNET_KEY`.
- [ ] Validar presenca da credencial Google.

Arquivo:

- `config/settings.py`

Exemplo:

```python
import os

REQUIRED_ENV_VARS = ["JWT_SECRET", "FERNET_KEY", "SHEET_NAME"]
missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]

if missing:
    raise RuntimeError(f"Variaveis ausentes: {', '.join(missing)}")
```

## Preparacao tecnica

### 6. Usar servidor WSGI de producao

- [ ] Adicionar `gunicorn` nas dependencias.
- [ ] Configurar o comando de inicializacao da plataforma.
- [ ] Nao usar `python app.py`, `flask run` ou o servidor de desenvolvimento publicamente.

Comando recomendado em Linux:

```bash
gunicorn --bind 0.0.0.0:$PORT --access-logfile=- app:app
```

### 7. Fixar dependencias

- [ ] Fixar versoes em `requirements.txt`.
- [ ] Migrar de `oauth2client` para `google-auth`.
- [ ] Remover `pytest` das dependencias de runtime.
- [ ] Criar um arquivo separado para desenvolvimento, como `requirements-dev.txt`.
- [ ] Atualizar `pip` e `setuptools` no ambiente de build.
- [ ] Executar `pip-audit` ou consulta OSV no CI.

Versoes instaladas durante a auditoria:

```txt
Flask==3.1.3
flask-cors==6.0.2
PyJWT==2.13.0
bcrypt==5.0.0
cryptography==48.0.0
python-dotenv==1.2.2
gspread==6.2.1
google-auth==2.53.0
requests==2.34.2
```

Adicionar tambem:

```txt
gunicorn
```

### 8. Restringir CORS

- [ ] Remover `CORS(app)` caso frontend e backend sejam servidos pelo mesmo dominio.
- [ ] Se houver frontend separado, aceitar somente a origem publicada.
- [ ] Nao usar wildcard de origem em producao.

Arquivo:

- `app.py`

Exemplo para frontend separado:

```python
CORS(
    app,
    resources={
        r"/auth/*": {"origins": FRONTEND_ORIGIN},
        r"/places/*": {"origins": FRONTEND_ORIGIN},
    },
)
```

### 9. Adicionar validacao server-side

- [ ] Limitar o tamanho total do JSON recebido.
- [ ] Limitar tamanho de username, nome do lugar, categoria e feedback.
- [ ] Normalizar email com `strip().casefold()`.
- [ ] Validar formato de email.
- [ ] Aceitar somente URLs `https`.
- [ ] Opcionalmente restringir `maps_url` a hosts esperados do Google Maps.
- [ ] Aplicar whitelist de categorias.
- [ ] Validar senhas entre 8 caracteres e 72 bytes para compatibilidade com bcrypt.
- [ ] Tratar tipos inesperados sem retornar erro `500`.

Exemplo:

```python
from urllib.parse import urlparse

app.config["MAX_CONTENT_LENGTH"] = 32 * 1024

def validate_http_url(value, *, required=False):
    if not value:
        if required:
            raise ValueError("URL obrigatoria")
        return ""

    if len(value) > 2048:
        raise ValueError("URL muito longa")

    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("URL invalida")

    return value
```

### 10. Adicionar endpoint de saude

- [ ] Criar uma rota simples para a plataforma verificar se o processo iniciou.
- [ ] Nao expor segredos nem detalhes da integracao com Google Sheets.

Arquivo:

- `app.py`

Exemplo:

```python
@app.get("/health")
def health():
    return {"status": "ok"}, 200
```

### 11. Adicionar headers defensivos

- [ ] Definir `X-Content-Type-Options`.
- [ ] Definir `Referrer-Policy`.
- [ ] Definir Content Security Policy.
- [ ] Habilitar HSTS no proxy ou plataforma quando HTTPS estiver confirmado.

Exemplo:

```python
@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' https:; "
        "object-src 'none'; "
        "base-uri 'none'"
    )
    return response
```

## Recomendado logo depois do primeiro deploy

### 12. Adicionar rate limiting

- [ ] Limitar tentativas de login por IP.
- [ ] Limitar cadastro por IP.
- [ ] Limitar escritas por usuario autenticado.
- [ ] Limitar rotas de reset se um reset real for implementado.
- [ ] Usar armazenamento compartilhado, como Redis, quando houver mais de uma instancia.

Exemplo:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri=REDIS_URL,
)
```

### 13. Adicionar logs basicos

- [ ] Registrar startup e erros de integracao.
- [ ] Registrar sucesso e falha de login sem armazenar senha.
- [ ] Registrar exclusao e alteracao de registros.
- [ ] Registrar bloqueios de rate limit.
- [ ] Criar identificador por requisicao.
- [ ] Configurar redaction de dados sensiveis.

Nunca registrar:

- `Authorization`
- JWT
- senha ou nova senha
- token de reset
- `JWT_SECRET`
- `FERNET_KEY`
- conteudo de `credentials.json`

### 14. Melhorar sessoes JWT

- [ ] Reduzir expiracao do access token.
- [ ] Adicionar `jti`.
- [ ] Adicionar revogacao ou `token_version`.
- [ ] Invalidar sessoes depois de troca de senha.
- [ ] Planejar migracao de `localStorage` para cookie `HttpOnly`, `Secure` e `SameSite` quando houver protecao CSRF adequada.

### 15. Implementar reset real por email com Brevo

O fluxo seguro foi implementado no codigo. Para ativa-lo no ambiente publicado, ainda e necessario verificar o remetente
na Brevo, cadastrar os secrets SMTP e definir `ENABLE_PASSWORD_RESET=true`.

- [ ] Criar uma conta na Brevo.
- [ ] Cadastrar um email pessoal como remetente individual.
- [ ] Confirmar o link enviado pela Brevo para verificar o remetente.
- [ ] Gerar uma SMTP key na Brevo.
- [ ] Configurar as variaveis SMTP como secrets no Render.
- [x] Usar `smtp-relay.brevo.com`.
- [x] Usar a porta `2525` no plano gratuito do Render.
- [x] Ativar TLS.
- [x] Enviar link com token aleatorio de uso unico e expiracao curta.
- [x] Armazenar somente o hash do token.
- [ ] Limitar tentativas e solicitacoes de reset.
- [x] Responder sempre com mensagem generica para nao revelar se o email existe.
- [ ] Invalidar sessoes antigas depois da troca de senha.

Configuracao recomendada:

```dotenv
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=2525
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_FROM_NAME=VamoAli
SMTP_USE_TLS=true
ENABLE_PASSWORD_RESET=true
PASSWORD_RESET_URL=https://seu-site.example/auth.html
```

No Render gratuito, as portas SMTP `25`, `465` e `587` sao bloqueadas para trafego de saida. A Brevo oferece a porta `2525` como alternativa. Para um projeto academico, um remetente individual verificado e suficiente; dominio proprio com SPF e DKIM pode ficar como evolucao futura.

### 16. Proteger integridade dos dados

- [ ] Manter escritas no Sheets explicitamente em modo `RAW`.
- [ ] Adicionar backups periodicos da planilha.
- [ ] Testar restauracao de backup.
- [ ] Revisar compartilhamentos no Google Drive.
- [ ] Planejar migracao futura para PostgreSQL se o projeto ganhar usuarios reais.

Exemplo:

```python
self.sheet.append_row(values, value_input_option="RAW")
self.sheet.update([new_row], f"A{row}", raw=True)
```

## Arquivos auxiliares recomendados

### `.env.example`

- [ ] Criar `.env.example` sem valores reais.

Exemplo:

```dotenv
SHEET_NAME=
JWT_SECRET=
FERNET_KEY=
GOOGLE_CREDENTIALS_JSON=
ENABLE_PASSWORD_RESET=false
PASSWORD_RESET_URL=http://localhost:5000/auth.html
PASSWORD_RESET_EXPIRATION_MINUTES=15
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=2525
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_FROM_NAME=VamoAli
SMTP_USE_TLS=true
```

### `README.md`

- [ ] Explicar arquitetura Controller -> Service -> Repository.
- [ ] Explicar que Google Sheets foi usado como persistencia demonstrativa.
- [x] Declarar que o reset matematico foi substituido por link enviado via Brevo SMTP.
- [ ] Documentar configuracao local sem incluir segredos.
- [ ] Adicionar link da aplicacao publicada.
- [ ] Listar limitacoes conhecidas e proximos passos.

### Testes

- [ ] Criar testes de autenticacao.
- [ ] Criar testes de autorizacao e IDOR.
- [ ] Criar teste contra mass assignment.
- [ ] Criar testes de validacao de URL.
- [ ] Criar testes de limites de tamanho.
- [ ] Criar testes de rate limiting quando implementado.

### CI

- [ ] Executar testes automaticamente.
- [ ] Executar `pip-audit`.
- [ ] Executar secret scanning.
- [ ] Bloquear merge quando os checks falharem.

## Configuracao da plataforma

- [ ] Conectar o repositorio GitHub.
- [ ] Definir versao suportada do Python.
- [ ] Configurar comando de build:

```bash
pip install -r requirements.txt
```

- [ ] Configurar comando de start:

```bash
gunicorn --bind 0.0.0.0:$PORT --access-logfile=- app:app
```

- [ ] Cadastrar secrets no painel.
- [ ] Confirmar HTTPS.
- [ ] Configurar health check em `/health`.
- [ ] Verificar logs do primeiro startup.

## Teste manual depois da publicacao

- [ ] Abrir a pagina inicial por HTTPS.
- [ ] Confirmar que o frontend nao tenta acessar `localhost`.
- [ ] Criar usuario de teste.
- [ ] Fazer login e logout.
- [ ] Confirmar que a solicitacao de reset envia email e nao revela se a conta existe.
- [ ] Criar, listar, favoritar, visitar, avaliar e excluir um lugar.
- [ ] Testar nome e feedback longos.
- [ ] Testar URL sem HTTPS.
- [ ] Confirmar que um usuario nao acessa registros de outro.
- [ ] Confirmar que o `PATCH` rejeita `user_id` e `id`.
- [ ] Abrir `/health`.
- [ ] Revisar logs para garantir que tokens e senhas nao aparecem.

## Criterio minimo para publicar

O deploy de portfolio pode ser liberado quando:

- [x] O reset matematico foi removido.
- [ ] O reset real por email foi configurado e testado no ambiente publicado.
- [x] O mass assignment estiver corrigido.
- [x] O frontend usar URL relativa.
- [x] Os segredos locais estiverem ignorados pelo Git.
- [x] O processo usar servidor WSGI de producao.
- [x] CORS estiver removido ou restrito.
- [x] Validacao server-side basica estiver ativa.
- [x] O endpoint `/health` responder corretamente.
- [ ] O fluxo principal tiver sido testado manualmente por HTTPS.

## Decisoes academicas documentadas

Estas escolhas sao aceitaveis para o portfolio quando estiverem documentadas:

- Google Sheets como persistencia demonstrativa para poucos usuarios.
- Frontend estatico servido pelo Flask.
- JWT simples para demonstrar autenticacao.
- Reset real de senha listado como evolucao futura.
- PostgreSQL, Redis e secret manager listados como evolucoes para uso real.
- Brevo com remetente individual verificado como opcao futura de reset real sem dominio proprio.

## Referencias

- Flask, deploy em producao: https://flask.palletsprojects.com/en/stable/deploying/
- Flask, Gunicorn: https://flask.palletsprojects.com/en/2.2.x/deploying/gunicorn/
- Google, service accounts: https://developers.google.com/identity/protocols/oauth2/service-account
- Google Cloud, boas praticas para chaves: https://docs.cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys
- OWASP, forgot password: https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html
- Render, bloqueio SMTP no plano gratuito: https://render-web.app.render.com/changelog/free-web-services-will-no-longer-allow-outbound-traffic-to-smtp-ports
- Brevo, envio transacional por SMTP: https://help.brevo.com/hc/en-us/articles/7924908994450-Send-transactional-emails-using-Brevo-SMTP
- Brevo, portas SMTP: https://help.brevo.com/hc/pt/articles/10905415650322-Qual-porta-SMTP-devo-usar-Porta-587-465-ou-2525
- Relatorio detalhado do projeto: `SECURITY_AUDIT.md`

## Status da implementacao no repositorio

Revisao atualizada em 2026-06-02. Itens marcados abaixo foram verificados no codigo. Pendencias externas permanecem
abertas ate serem executadas no provedor ou no ambiente publicado.

### Concluido no codigo

- [x] Reset matematico removido e substituido por link enviado via Brevo SMTP.
- [x] Token de reset aleatorio, de uso unico, expiravel e armazenado somente como hash.
- [x] Resposta de solicitacao de reset generica para evitar enumeracao de contas.
- [x] `PATCH /places/<place_id>` aceita somente `visited` booleano; testes rejeitam `id` e `user_id`.
- [x] Frontend usa origem relativa para API.
- [x] `.env` e `credentials.json` permanecem ignorados; `.env.example` nao contem segredos.
- [x] Startup valida variaveis obrigatorias, tamanho minimo de `JWT_SECRET`, formato Fernet e credencial Google.
- [x] Runtime usa dependencias fixadas, `gunicorn`, `Procfile`, `google-auth` e arquivo separado de desenvolvimento.
- [x] Cliente Sheets usa escrita no Sheets e leitura do Drive para localizar a planilha por `SHEET_NAME`.
- [x] CORS permissivo foi removido porque frontend e API compartilham origem.
- [x] JSON limitado a 32 KiB; email, senha, campos, categorias e URLs recebem validacao server-side.
- [x] `/health` retorna somente `{"status": "ok"}`.
- [x] Headers `X-Content-Type-Options`, `Referrer-Policy` e Content Security Policy adicionados.
- [x] JWT expira em duas horas por padrao e inclui `jti`.
- [x] Escritas no Sheets usam explicitamente modo `RAW`.
- [x] Testes automatizados cobrem autenticacao, autorizacao/IDOR, mass assignment, URLs e limites.
- [x] CI executa lint, testes com cobertura minima de 80%, `pip-audit` e Gitleaks.
- [x] CD aguarda CI bem-sucedido em `main` e usa secret para o deploy hook.
- [x] README documenta arquitetura, ambiente local, testes, CI/CD, deploy e limitacoes.

### Pendente antes ou depois da publicacao

- [ ] Cadastrar secrets no provedor e GitHub, incluindo `RENDER_DEPLOY_HOOK_URL`.
- [ ] Rotacionar a service account caso tenha sido compartilhada e revisar acesso da planilha no Google Drive.
- [ ] Conectar o repositorio ao provedor, confirmar Python 3.11, HTTPS, `/health` e logs de startup.
- [ ] Configurar branch protection em `main` exigindo os checks do CI.
- [ ] Executar integralmente a secao "Teste manual depois da publicacao" por HTTPS.
- [ ] Adicionar HSTS no proxy quando HTTPS estiver confirmado.
- [ ] Adicionar rate limiting com armazenamento compartilhado, preferencialmente Redis.
- [ ] Adicionar logs estruturados com request id e redaction de dados sensiveis.
- [ ] Implementar revogacao ou `token_version` para JWT e invalidacao depois de troca de senha.
- [ ] Finalizar configuracao externa da Brevo: verificar remetente e cadastrar secrets SMTP no provedor.
- [ ] Autorizar no Brevo as faixas de IP de saida do servico Render exibidas em `Connect > Outbound`.
- [ ] Criar rotina de backup da planilha e testar restauracao.
- [ ] Adicionar o link publicado ao README.
