# Teste de performance

O cenário Locust simula o uso autenticado das rotas de leitura:

- `GET /places` com peso 60%.
- `GET /places/random` com peso 20%.
- `GET /sharing/group` com peso 20%.

Respostas `404` de sorteio e grupo são consideradas válidas, pois representam usuários sem lugares disponíveis ou
sem grupo. O cenário não cria, altera ou exclui dados.

Use somente um ambiente de staging ou uma planilha preparada para testes. Google Sheets possui limites de requisição e
não é indicado para testes agressivos em produção.

## Interface web

```powershell
$env:PERF_EMAIL="teste@example.com"
$env:PERF_PASSWORD="SenhaTeste1!"
.\.venv\Scripts\locust.exe -f performance\locustfile.py --host https://staging.example.com
```

Abra `http://localhost:8089` e comece com poucos usuários, aumentando gradualmente.

## Teste headless

```powershell
$env:PERF_TOKEN="jwt-de-um-usuario-de-teste"
$env:PERF_MAX_P95_MS="1500"
$env:PERF_MAX_FAILURE_RATIO="0.01"

.\.venv\Scripts\locust.exe -f performance\locustfile.py `
  --host https://staging.example.com `
  --headless `
  --users 10 `
  --spawn-rate 2 `
  --run-time 2m `
  --csv performance-results
```

O comando encerra com erro quando o p95 excede `PERF_MAX_P95_MS`, a proporção de falhas excede
`PERF_MAX_FAILURE_RATIO` ou nenhuma requisição é executada.

Usar `PERF_TOKEN` remove o custo de login e bcrypt da medição. Para medir também a autenticação, remova `PERF_TOKEN` e
configure `PERF_EMAIL` e `PERF_PASSWORD`.
