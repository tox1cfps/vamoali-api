# Auditoria Completa de Seguranca - VamoAli API

Data da revisao: 2026-06-02

## Atualizacao de remediacao

Depois desta auditoria, o desafio matematico de recuperacao de senha foi removido. O codigo atual envia por Brevo SMTP
um link com token aleatorio de uso unico, armazena somente o hash do token, aplica expiracao curta e retorna mensagem
generica para evitar enumeracao de contas. Ainda permanecem pendentes rate limiting compartilhado, persistencia dos
tokens fora da memoria e configuracao dos secrets SMTP no ambiente publicado.

## Escopo e metodo

Foi realizada revisao estatica de todo o repositorio, incluindo backend Flask, camadas Controller -> Service -> Repository, frontend estatico, configuracao, arquivos ignorados pelo Git e ambiente virtual instalado. Tambem foi consultada a API publica do OSV para as versoes instaladas.

O projeto e academico e destinado a portfolio. O mecanismo matematico de recuperacao de senha foi criado como prototipo didatico para compreender o fluxo de reset, nao como implementacao final para producao. As severidades abaixo avaliam o comportamento caso a API seja publicada na internet sem alteracoes.

Esta auditoria nao substitui pentest em ambiente publicado, revisao das permissoes reais da planilha no Google Drive, analise do proxy reverso ou verificacao do historico de repositorios remotos que nao estejam disponiveis localmente.

## Resumo executivo

A aplicacao tem uma base simples e alguns controles corretos: senhas usam bcrypt, dados de `places` sao filtrados pelo `user_id` obtido do JWT, mutacoes especificas verificam o proprietario, JWT fixa `HS256` na validacao e as escritas atuais do `gspread` usam `RAW`.

O principal ponto de atencao para uma eventual publicacao e o prototipo didatico de recuperacao de senha. Qualquer pessoa pode solicitar um token para qualquer email, recebe o desafio no proprio navegador e pode responder uma entre cinco perguntas com respostas triviais e hardcoded. Nao existe verificacao de posse do email, limite de tentativas nem rate limiting. Isso permite tomada de conta se o prototipo permanecer habilitado em uma API publica.

Tambem ha risco alto de abuso da API por ausencia completa de rate limiting, mass assignment no `PATCH /places/<place_id>`, credencial de service account armazenada como arquivo dentro da pasta do projeto e escopos Google amplos. A aplicacao ainda carece de validacao server-side, limites de tamanho, logs de seguranca, headers defensivos e gestao de sessao JWT com revogacao.

**Nota geral para exposicao real na internet: 3,5 / 10.**

**Nota como projeto academico de portfolio: 6 / 10.**

Justificativa: nao foi encontrada uma via direta para RCE ou acesso cruzado trivial aos registros de outro usuario, e ha controles criptograficos basicos corretos. O projeto demonstra conceitos relevantes, incluindo bcrypt, JWT, Fernet e separacao em camadas. Para uso real, o prototipo de reset precisa ser removido ou substituido antes da publicacao, pois a tomada de conta seria pratica, remota e barata.

## Achados detalhados

### SEC-01 - Prototipo didatico de recuperacao de senha nao e seguro para producao

**Severidade:** Critica

**Descricao tecnica**

Como exercicio academico, o fluxo demonstra geracao, expiracao e consumo de token. Entretanto, `POST /auth/reset-password?email=...` retorna diretamente um token e uma pergunta matematica. O token tem 128 bits gerados por `secrets.token_hex(16)`, mas isso nao resolve o problema de identidade: ele e entregue ao solicitante, nao ao titular da conta. As cinco perguntas e respostas ficam hardcoded e sao triviais. O mesmo token aceita tentativas ilimitadas durante cinco minutos.

**Impacto**

Um atacante que conheca ou adivinhe o email consegue trocar a senha da vitima e entrar na conta. Respostas corretas e incorretas tambem permitem enumerar contas, pois o fluxo termina em sucesso para emails existentes e `404` para inexistentes.

**Evidencia**

- `controllers/auth_controller.py:33-53`
- `services/auth_service.py:11-18`
- `services/auth_service.py:53-68`
- `services/auth_service.py:70-98`
- `static/app.js:531-609`

**Correcao**

Antes de publicar a API, substituir o desafio por token aleatorio de uso unico enviado fora de banda ao email cadastrado ou desabilitar temporariamente a rota. Responder sempre com mensagem generica. Armazenar somente hash do token, prazo curto, contador de tentativas e data de consumo. Invalidar sessoes existentes apos a troca.

**Exemplo de codigo**

```python
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

raw_token = secrets.token_urlsafe(32)
token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
reset_repo.create(
    email_hash=email_lookup_hash(email),
    token_hash=token_hash,
    expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    attempts_left=5,
)
mailer.send_reset_link(email, f"{PUBLIC_URL}/reset?token={raw_token}")
return {"success": True, "message": "Se a conta existir, enviaremos instrucoes."}
```

### SEC-02 - Ausencia completa de rate limiting

**Severidade:** Alta

**Descricao tecnica**

Nao ha limitador por IP, conta ou rota. Login, cadastro, solicitacao/confirmacao de reset e criacao de places podem ser automatizados sem bloqueio da aplicacao.

**Impacto**

Brute force de login, exploracao acelerada do reset, spam, consumo de quota do Google Sheets e degradacao de disponibilidade.

**Evidencia**

- `controllers/auth_controller.py:8-53`
- `controllers/place_controller.py:9-130`
- Ausencia de middleware de rate limiting no repositorio e em `requirements.txt`

**Correcao**

Adicionar rate limiting com armazenamento compartilhado em producao, por exemplo Redis. Aplicar limites mais duros a autenticacao e reset. Incluir limite global e por usuario autenticado nas escritas.

**Exemplo de codigo**

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, app=app, storage_uri=REDIS_URL)

@bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute; 30 per hour")
def login():
    ...
```

### SEC-03 - Mass assignment no PATCH de places

**Severidade:** Alta

**Descricao tecnica**

O controller repassa o JSON inteiro para `update_place`. O repositorio combina o dicionario recebido com o estado persistido e escreve todas as colunas. O cliente pode alterar campos internos como `id`, `user_id`, `created_at`, `updated_at`, `favorited`, `rating` e `feedback`, contornando regras dos endpoints especializados.

**Impacto**

Corrupcao da planilha, transferencia indevida de propriedade, quebra de integridade, contorno da regra que exige visita antes do feedback e criacao de IDs duplicados. A checagem inicial impede editar diretamente um registro ja pertencente a outro usuario, mas nao torna o endpoint seguro.

**Evidencia**

- `controllers/place_controller.py:56-71`
- `services/place_service.py:45-54`
- `repositories/place_repository.py:57-70`

**Correcao**

Aplicar whitelist por endpoint e validar tipos. Para marcar visita, usar somente o endpoint especializado ou aceitar apenas `visited`.

**Exemplo de codigo**

```python
ALLOWED_PATCH_FIELDS = {"visited"}

def update_place(self, user_id, place_id, fields):
    unexpected = set(fields) - ALLOWED_PATCH_FIELDS
    if unexpected:
        raise ValueError("Campos nao permitidos")
    return self.place_repo.update_place(place_id, {
        "visited": self._parse_bool(fields["visited"])
    })
```

### SEC-04 - Credencial Google e chaves locais dentro da pasta do projeto

**Severidade:** Alta

**Descricao tecnica**

Existe um `credentials.json` com chave privada de service account e um `.env` com `JWT_SECRET` e `FERNET_KEY` na raiz do projeto. Ambos estao ignorados pelo Git e nao aparecem no historico Git local, o que e positivo. Ainda assim, manter credenciais persistentes dentro da arvore do projeto aumenta o risco de vazamento por ZIP, backup, imagem de container, deploy manual ou permissao local inadequada.

O cliente solicita escopos de planilhas e Google Drive. O escopo Drive e amplo para uma aplicacao que precisa operar uma unica planilha.

**Impacto**

Se a chave vazar, um atacante pode autenticar como a service account e acessar os recursos concedidos a ela. Se `FERNET_KEY` vazar junto, emails e usernames da planilha podem ser descriptografados. Se `JWT_SECRET` vazar, JWTs podem ser forjados.

**Evidencia**

- `.env` presente localmente e ignorado por `.gitignore:2`
- `credentials.json` presente localmente e ignorado por `.gitignore:3`
- `config/settings.py:6-12`
- `utils/sheets_client.py:5-15`

**Correcao**

Retirar chaves da arvore da aplicacao. Em cloud, preferir identidade de workload sem arquivo de chave. Quando arquivo for inevitavel, montar segredo fora do diretorio da aplicacao, aplicar menor privilegio, rotacionar e monitorar. Compartilhar somente a planilha necessaria com a service account. Migrar de `oauth2client` para `google-auth`.

**Exemplo de codigo**

```python
from google.oauth2.service_account import Credentials
import gspread

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
    scopes=SCOPES,
)
sheet = gspread.authorize(creds).open_by_key(os.environ["SPREADSHEET_ID"])
```

### SEC-05 - Validacao server-side insuficiente e ausencia de limites

**Severidade:** Media

**Descricao tecnica**

O backend valida somente presenca de `name`, forca minima de senha e faixa de `rating`. Nao ha tamanho maximo de body ou campos, validacao real de email, normalizacao de email, limite de senha, lista permitida de categorias ou validacao de URL. Atributos ausentes ou tipos inesperados podem causar `500`.

Com `bcrypt 5.0.0`, senhas acima de 72 bytes causam `ValueError`. A aplicacao nao captura esse erro em todos os caminhos. Strings enormes tambem podem consumir memoria, quota e espaco na planilha.

**Impacto**

DoS de baixo custo, dados inconsistentes, erros `500`, abuso de armazenamento e preparacao de payloads para riscos no navegador ou exportacoes.

**Evidencia**

- `services/auth_service.py:38-51`
- `services/auth_service.py:113-140`
- `services/place_service.py:28-32`
- `services/place_service.py:67-85`
- `app.py:6-7`

**Correcao**

Definir `MAX_CONTENT_LENGTH`, validar schema em todas as rotas, normalizar email com `strip().casefold()`, impor comprimentos e validar URLs por esquema e host conforme necessidade.

**Exemplo de codigo**

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
    if parsed.scheme not in {"https"} or not parsed.netloc:
        raise ValueError("URL invalida")
    return value
```

### SEC-06 - URLs nao validadas voltam ao DOM

**Severidade:** Media

**Descricao tecnica**

`maps_url` e `photo_url` sao aceitos pelo backend sem validacao. No frontend, `maps_url` vira `href` e `photo_url` vira `src`. O escaping de atributo evita sair das aspas, mas nao bloqueia esquemas perigosos ou destinos maliciosos.

**Impacto**

Links controlados pelo usuario podem redirecionar para phishing e esquemas perigosos dependendo do navegador. Imagens remotas permitem tracking do IP do usuario, consumo de banda e carregamento de conteudo externo. Isso nao e SSRF server-side, pois quem busca a imagem e o navegador.

**Evidencia**

- `services/place_service.py:28-32`
- `static/app.js:768-771`
- `static/app.js:794`
- `static/app.js:803`
- `static/app.js:831`

**Correcao**

Aceitar apenas `https`. Para `maps_url`, opcionalmente restringir hosts do Google Maps. Para fotos, preferir upload controlado ou proxy de imagens com limites e protecoes proprias. Adicionar CSP.

### SEC-07 - JWT pode ser reutilizado ate expirar e fica no localStorage

**Severidade:** Media

**Descricao tecnica**

O JWT usa `HS256`, assinatura e `exp` de 24 horas. A validacao fixa o algoritmo, o que bloqueia troca para `none`. Porem nao ha `jti`, revogacao, rotacao, refresh token, validacao de usuario ainda existente nem invalidacao apos reset de senha. Logout apenas apaga o token no navegador. O frontend guarda JWT em `localStorage`.

**Impacto**

Um token roubado pode ser reutilizado por ate 24 horas, inclusive apos logout ou troca de senha. Qualquer XSS futuro ou script de terceiro executado na origem teria acesso ao token.

**Evidencia**

- `services/auth_service.py:100-111`
- `middleware/auth_middleware.py:6-23`
- `static/app.js:57-58`
- `static/app.js:166-167`
- `static/app.js:237-238`

**Correcao**

Usar access tokens curtos, `jti`, denylist ou `token_version`, validar existencia/status do usuario e revogar sessoes apos reset. Preferir cookie `HttpOnly`, `Secure`, `SameSite` com protecao CSRF quando a arquitetura permitir. Validar configuracao no startup e manter segredo forte fora da pasta do projeto.

**Exemplo de codigo**

```python
payload = {
    "sub": user_id,
    "jti": secrets.token_urlsafe(16),
    "iat": now,
    "exp": now + timedelta(minutes=15),
    "iss": "vamoali-api",
}

payload = jwt.decode(
    token,
    JWT_SECRET,
    algorithms=["HS256"],
    issuer="vamoali-api",
    options={"require": ["sub", "jti", "iat", "exp", "iss"]},
)
```

### SEC-08 - CORS permissivo e ausencia de headers defensivos

**Severidade:** Media

**Descricao tecnica**

`CORS(app)` aceita origens amplamente por padrao. Nao ha CSP, HSTS, `X-Content-Type-Options`, politica de framing ou `Referrer-Policy`.

**Impacto**

Amplia a superficie de chamadas cross-origin e reduz protecoes do navegador contra classes de abuso no frontend. Como o token esta no header e nao em cookie, isso nao cria sozinho um bypass de autenticacao; ainda assim e configuracao excessivamente permissiva.

**Evidencia**

- `app.py:6-7`
- Ausencia de middleware de headers no repositorio

**Correcao**

Restringir CORS a origens conhecidas e definir headers no proxy reverso ou Flask.

**Exemplo de codigo**

```python
CORS(app, resources={r"/auth/*": {"origins": FRONTEND_ORIGIN},
                     r"/places/*": {"origins": FRONTEND_ORIGIN}})

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' https:; object-src 'none'; base-uri 'none'"
    return response
```

### SEC-09 - Logging e monitoramento de seguranca ausentes

**Severidade:** Media

**Descricao tecnica**

Nao existem logs estruturados de login, falhas, reset, alteracoes destrutivas, rate limit ou erros de integracao com Sheets. Tambem nao ha identificador de requisicao.

**Impacto**

Tomada de conta, brute force e corrupcao podem passar despercebidos. A investigacao posterior fica limitada.

**Evidencia**

- Ausencia de chamadas de logging e middleware de observabilidade no backend

**Correcao**

Registrar eventos com timestamp, request ID, rota, resultado, IP tratado conforme politica de privacidade e identificador de usuario quando houver. Nunca registrar senha, JWT, token de reset, chave Fernet ou credenciais Google. Criar alertas para falhas repetidas e volume anormal.

### SEC-10 - Dependencias nao fixadas e ferramentas vulneraveis no ambiente

**Severidade:** Media

**Descricao tecnica**

`requirements.txt` lista pacotes sem versao ou hash. O deploy nao e reproduzivel. A consulta OSV das dependencias instaladas nao encontrou alertas para bibliotecas de runtime, mas encontrou avisos para ferramentas do ambiente:

| Pacote instalado | Alertas OSV | Versao minima que cobre os alertas consultados |
| --- | --- | --- |
| `pip 24.0` | `GHSA-4xh5-x5gv-qwph`, `GHSA-58qw-9mgm-455v`, `GHSA-6vgw-5pg2-w6jp`, `GHSA-jp4c-xjxw-mgf9` | `26.1` |
| `setuptools 65.5.0` | `GHSA-5rjg-fvgr-3xxf`, `GHSA-cx63-2mw6-8hw5`, `GHSA-r9hx-vwmv-q579`, `PYSEC-2022-43012`, `PYSEC-2025-49` | `78.1.1` |

`oauth2client 4.1.3` tambem esta deprecated e seu repositorio foi arquivado em 2025-01-18.

**Impacto**

Risco de supply chain durante instalacao, divergencia entre ambientes e permanencia em bibliotecas sem suporte.

**Evidencia**

- `requirements.txt:1-10`
- Ambiente local consultado via `pip freeze` e API OSV em 2026-06-02
- `utils/sheets_client.py:2`

**Correcao**

Atualizar ferramentas de build, migrar para `google-auth`, fixar dependencias transitivas com hashes e executar `pip-audit` ou consulta OSV no CI. Separar dependencias de runtime e desenvolvimento.

### SEC-11 - Concorrencia do Sheets pode causar perda ou corrupcao de dados

**Severidade:** Media

**Descricao tecnica**

Atualizacoes e exclusoes localizam a linha, depois fazem outra operacao por numero de linha. Se linhas forem alteradas concorrentemente, a linha pode deslocar. Atualizacoes tambem reescrevem a linha inteira a partir de um snapshot.

**Impacto**

Lost update e, em condicoes de corrida, alteracao ou exclusao de linha diferente da pretendida. Com poucos usuarios a probabilidade e menor, mas o impacto de integridade permanece.

**Evidencia**

- `repositories/place_repository.py:43-70`

**Correcao**

Para uso exposto na internet, migrar persistencia para banco transacional. Enquanto Sheets permanecer, serializar escritas, revalidar ID imediatamente antes da operacao e manter backups/versionamento.

### SEC-12 - Criptografia de PII ajuda, mas gestao de chave e fallback reduzem garantias

**Severidade:** Baixa

**Descricao tecnica**

Email e username usam Fernet antes de serem gravados. Isso protege contra leitura casual da planilha sem acesso a `FERNET_KEY`. Entretanto, a chave esta no mesmo contexto operacional da aplicacao. Alem disso, `_maybe_decrypt` captura qualquer excecao e devolve o valor original, aceitando silenciosamente plaintext ou ciphertext corrompido.

**Impacto**

Um vazamento conjunto da planilha e do ambiente remove o beneficio. Falhas de integridade e dados legados plaintext podem passar despercebidos.

**Evidencia**

- `utils/encryption.py:5-17`
- `repositories/user_repository.py:7-14`
- `repositories/user_repository.py:51-55`

**Correcao**

Armazenar chave em secret manager ou identidade de workload, rotacionar com estrategia de versao e tratar falha de descriptografia explicitamente. Para busca eficiente e normalizada, considerar coluna adicional com HMAC do email usando chave separada.

## Google Sheets: formula injection e CSV injection

### Estado atual

As chamadas atuais usam os defaults seguros do `gspread 6.2.1`:

- `Worksheet.append_row(..., value_input_option=RAW)`
- `Worksheet.update(..., raw=True)`

Com `RAW`, strings iniciadas por `=`, `+`, `-` ou `@` sao armazenadas como texto e nao interpretadas como entrada digitada na UI. Portanto, **na implementacao atual nao foi confirmada formula injection executada automaticamente pelo Google Sheets**.

Ainda existe risco residual em exportacao CSV e reabertura em outro software de planilhas, alteracao futura para `USER_ENTERED`, edicao manual e permissao excessiva da service account. Os campos mais importantes sao `name`, `category`, `feedback`, `maps_url` e `photo_url`.

### Recomendacao

Manter `RAW` explicitamente para evitar regressao e rejeitar ou neutralizar prefixos perigosos em campos exportaveis quando houver exportacao CSV:

```python
def safe_sheet_text(value: str, max_length: int) -> str:
    value = value.strip()
    if len(value) > max_length:
        raise ValueError("Campo muito longo")
    if value.startswith(("=", "+", "-", "@")):
        value = "'" + value
    return value

self.sheet.append_row(values, value_input_option="RAW")
self.sheet.update([new_row], f"A{row}", raw=True)
```

## Autorizacao e IDOR

| Operacao | Resultado |
| --- | --- |
| Ler registros de outro usuario pela API | Nao confirmado. `find_all_by_user` filtra pelo `sub` do JWT. |
| Deletar registro de outro usuario pela API | Bloqueado pela verificacao de `user_id`. |
| Favoritar registro de outro usuario pela API | Bloqueado pela verificacao de `user_id`. |
| Marcar visita, feedback ou rating de outro usuario | Bloqueado pela verificacao de `user_id`. |
| Atualizar registro proprio com campos internos | Vulneravel por mass assignment. |
| Manipular dados diretamente como editor da planilha | Possivel para qualquer principal com permissao de edicao no Drive; revisar compartilhamentos. |

Nao foi encontrado IDOR direto para registros de terceiros nas rotas atuais. O mass assignment e as condicoes de corrida ainda devem ser corrigidos porque enfraquecem a integridade e podem evoluir para bypass com novas funcionalidades.

## JWT

| Item | Resultado |
| --- | --- |
| Geracao | `sub`, `iat`, `exp`; assinatura `HS256`. |
| Expiracao | Presente, 24 horas. Recomenda-se 15 minutos para access token. |
| Assinatura | Presente. `JWT_SECRET` vem do ambiente. |
| Validacao | Algoritmo permitido e fixado em `algorithms=[JWT_ALGORITHM]`. |
| Token forging | Nao confirmado com o segredo atual; torna-se trivial se `JWT_SECRET` vazar ou for fraco. |
| Privilege escalation | Nao ha roles no token. `sub` controla identidade; segredo vazado permite assumir qualquer UUID. |
| Replay | Possivel ate `exp`; nao ha revogacao, `jti` ou versao de sessao. |
| Logout | Apenas client-side. Nao invalida token roubado. |

## Vetores classicos solicitados

| Vetor | Resultado e justificativa |
| --- | --- |
| SQL Injection | Ausente: nao existe SQL ou driver relacional. |
| NoSQL Injection | Ausente: nao existe mecanismo de consulta NoSQL construida com entrada do usuario. Sheets e percorrido em memoria. |
| Command Injection | Ausente: nao ha shell, `subprocess`, `os.system`, `eval` ou `exec`. |
| Header Injection | Ausente nas rotas revisadas: entrada do usuario nao e copiada para response headers. |
| CSV Injection | Risco residual se dados forem exportados e reabertos em software que interprete formulas. |
| Formula Injection em Sheets | Nao confirmada na escrita atual porque `gspread` usa `RAW`; manter explicito e neutralizar campos exportaveis. |
| Path Traversal | Nao confirmado: arquivos estaticos usam `send_from_directory("static", filename)`, que restringe resolucao ao diretorio informado. |
| SSRF | Ausente no backend: a API nao busca `maps_url` nem `photo_url`. Ha carregamento client-side de foto remota. |
| XXE | Ausente: nao ha parser XML. |
| RCE | Nao encontrado: nao ha execucao dinamica, upload executavel ou comando de sistema. |
| Open Redirect | Nao ha redirect server-side controlado por entrada. `maps_url` permite link externo arbitrario e deve ser validado. |
| Insecure Deserialization | Ausente: o backend recebe JSON comum e nao usa `pickle`, YAML inseguro ou desserializador de objetos. |

## OWASP Top 10

| Categoria | Estado |
| --- | --- |
| A01 Broken Access Control | Parcialmente vulneravel: mass assignment e falta de menor privilegio Google; IDOR direto nao confirmado. |
| A02 Cryptographic Failures | Parcialmente vulneravel: Fernet e bcrypt sao bons, mas chaves ficam na arvore local e JWT nao possui revogacao. |
| A03 Injection | Formula injection direta mitigada por `RAW`; CSV residual e URLs inseguras exigem tratamento. |
| A04 Insecure Design | Vulneravel: reset de senha nao verifica posse do email. |
| A05 Security Misconfiguration | Vulneravel: CORS amplo, headers ausentes, escopo Drive amplo e servidor Flask direto se usado em producao. |
| A06 Vulnerable and Outdated Components | Vulneravel operacionalmente: requirements sem pin, ferramentas vulneraveis e `oauth2client` deprecated. |
| A07 Identification and Authentication Failures | Vulneravel: reset exploravel, sem rate limit e JWT reproduzivel ate expirar. |
| A08 Software and Data Integrity Failures | Vulneravel: lockfile/hashes ausentes, mass assignment e escrita Sheets nao transacional. |
| A09 Security Logging and Monitoring Failures | Vulneravel: logs e alertas de seguranca ausentes. |
| A10 SSRF | Nao encontrado no backend. |

## Segredos e configuracao

| Item | Resultado |
| --- | --- |
| `JWT_SECRET` | Vem de `.env`; nao esta hardcoded nem rastreado no Git local. Validar presenca e entropia no startup. |
| `FERNET_KEY` | Vem de `.env`; nao esta hardcoded nem rastreado no Git local. Separar operacionalmente e planejar rotacao. |
| `.env` | Ignorado pelo Git, mas presente dentro da arvore do projeto. Evitar incluir em artefatos e backups. |
| `credentials.json` | Ignorado pelo Git e ausente do historico Git local, mas contem chave privada real-looking dentro da arvore. Mover e rotacionar se o arquivo ja foi compartilhado. |
| Service account | Escopos incluem Drive amplo. Reduzir privilegios e preferir identidade sem chave persistente. |

## Logs

Nao foram encontrados logs explicitos contendo senhas, JWTs ou tokens, o que evita vazamento acidental atual. Tambem nao foram encontrados logs de seguranca suficientes para rastreabilidade. Ao adicionar observabilidade, aplicar redaction obrigatoria a:

- `Authorization`
- `password`, `new_password`
- token de reset
- `JWT_SECRET`, `FERNET_KEY`
- conteudo de `credentials.json`

## Resultado final

| Vulnerabilidade | Severidade | Corrigir agora? |
| --- | --- | --- |
| Prototipo de reset permite tomada de conta se publicado | Critica | Sim, antes de publicar a API |
| Ausencia de rate limiting | Alta | Sim |
| Mass assignment no PATCH de places | Alta | Sim |
| Chaves locais na pasta do projeto e escopo Google amplo | Alta | Sim |
| Validacao e limites insuficientes | Media | Sim |
| URLs nao validadas retornam ao DOM | Media | Sim |
| JWT reproduzivel e armazenado em localStorage | Media | Sim |
| CORS amplo e headers defensivos ausentes | Media | Sim |
| Logging e monitoramento ausentes | Media | Sim |
| Dependencias nao fixadas, tooling vulneravel e `oauth2client` deprecated | Media | Sim |
| Concorrencia do Sheets pode corromper dados | Media | Planejar imediatamente |
| Fallback silencioso na descriptografia | Baixa | Corrigir no hardening |
| CSV injection residual em exportacoes futuras | Baixa | Corrigir antes de exportar |

## Roadmap de Hardening

### Criticas

1. Desabilitar o reset matematico antes de publicar a API.
2. Implementar reset por link enviado ao email, token de uso unico com hash, prazo curto, limite de tentativas e resposta generica.
3. Revogar sessoes existentes apos troca de senha.

### Altas

1. Aplicar rate limiting global, por IP, por conta e por usuario autenticado.
2. Substituir o `PATCH` generico por whitelist estrita.
3. Mover `credentials.json`, `JWT_SECRET` e `FERNET_KEY` para gestao apropriada de segredos.
4. Rotacionar a service account se a chave ja foi compartilhada, copiada ou incluida em artefatos.
5. Reduzir escopos Google e revisar compartilhamentos da planilha.

### Medias

1. Criar schemas de validacao server-side, limites de body e limites por campo.
2. Validar `https` e hosts esperados para URLs.
3. Encurtar vida do JWT, adicionar revogacao e revisar armazenamento no navegador.
4. Restringir CORS e adicionar headers defensivos.
5. Adicionar logs estruturados, redaction e alertas.
6. Fixar dependencias com hashes, atualizar tooling e migrar de `oauth2client` para `google-auth`.
7. Planejar migracao do Sheets para banco transacional.

### Boas praticas futuras

1. Adicionar testes automatizados de autorizacao, reset, rate limiting e validacao.
2. Executar SAST, secret scanning e `pip-audit` no CI.
3. Adicionar backups e teste de restauracao.
4. Documentar proxy HTTPS e nunca publicar o servidor de desenvolvimento Flask diretamente.
5. Manter escritas Sheets explicitamente em modo `RAW`.

## Fontes externas consultadas

- gspread 6.2.1, defaults de `append_row` e `update`: https://docs.gspread.org/en/v6.2.1/api/models/worksheet.html
- Google Sheets API, `ValueInputOption`: https://developers.google.com/sheets/api/reference/rest/v4/ValueInputOption
- OWASP Forgot Password Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html
- OWASP JWT Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
- Google Cloud, boas praticas para chaves de service account: https://docs.cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys
- oauth2client README, deprecacao e repositorio arquivado: https://github.com/googleapis/oauth2client/blob/master/README.md
- OSV: https://osv.dev/
