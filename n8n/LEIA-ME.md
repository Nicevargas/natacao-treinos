# Disparo diário pelo n8n

## Por que existe

O `schedule` do GitHub Actions não cumpre horário. Em repositório público no
plano gratuito ele é a fila de menor prioridade da plataforma:

| Dia | Programado | O que aconteceu |
|---|---|---|
| 29/08 | 06:00 | não rodou — pulado |
| 30/08 | 06:13 | rodou 11:24, cinco horas depois |

Com o limite de publicar **até as 8h**, isso está fora. Mas o problema é só o
gatilho: a parte pesada (gerar os 5 slides no Linux, com as fontes certas, e
publicar) já funciona no Actions.

Então o n8n entra só como relógio. Ele chama a API de `repository_dispatch` do
GitHub, que roda o workflow **na hora** — disparo por API não passa pela fila do
cron. Somando a subida do runner e a execução, o post sai por volta das 06:03.

O `schedule` continua no workflow como rede de segurança, caso o n8n esteja
fora do ar. Se o n8n já publicou, essas execuções tardias veem o carrossel do
dia na conta e saem sem fazer nada.

## Configurar (uma vez)

### 1. Criar o PAT no GitHub

Settings → Developer settings → Personal access tokens → **Fine-grained**.

- Repositório: só `natacao-treinos`
- Permissão: **Contents → Read and write** (é o que a API de dispatches exige)
- Validade: sem expiração

Se você já criou o `PAT_SEGREDOS` para a renovação do token, pode usar o mesmo,
desde que ele tenha a permissão de Contents além da de Secrets.

### 2. Criar a credencial no n8n

Credentials → New → **Header Auth**:

- **Name:** `Authorization`
- **Value:** `Bearer SEU_PAT_AQUI`

O `Bearer ` na frente faz parte do valor. Guardar assim mantém o token fora do
JSON do fluxo, então o arquivo pode ser versionado sem risco.

### 3. Importar o fluxo

n8n → Import from File → `disparo-diario.json`.

Abra o nó **Disparar o GitHub Actions** e selecione a credencial criada acima.
Depois ative o fluxo.

### 3b. Conferir o fuso — o n8n ignora o do arquivo

O JSON traz `settings.timezone: America/Sao_Paulo`, **mas o n8n descarta isso na
importação** e aplica o fuso padrão da instância. Nesta instância o padrão é
`America/New_York`, então o gatilho de 06:00 dispara às 07:00 de Brasília.

Isso ainda cabe na janela até as 8h, mas quebra em novembro: quando os EUA
saem do horário de verão, `America/New_York` vira UTC-5 e as 06:00 de lá
passam a ser **08:00 aqui** — em cima do limite.

Corrigir em: menu `...` do fluxo → **Settings** → **Timezone** →
`America/Sao_Paulo` → Save.

Para conferir depois: abra o nó do gatilho, execute, e olhe o campo `Timezone`
na saída. Tem que dizer `America/Sao_Paulo (UTC-03:00)`.

### 4. Testar

Clique em **Execute Workflow**. O esperado é o nó verde e a mensagem
"Disparo aceito" — a API do GitHub responde **204 No Content** quando aceita,
que é sucesso, não erro.

Confira em github.com/Nicevargas/natacao-treinos/actions: deve aparecer uma
execução nova com o evento `repository_dispatch`.

## Se falhar

- **404** — quase sempre o PAT não tem permissão de Contents neste repositório,
  ou está apontando para o repositório errado. A API devolve 404 em vez de 403
  para não revelar se o repositório existe.
- **401** — o valor da credencial está sem o prefixo `Bearer `, ou o PAT expirou.
- **Disparou, mas não publicou** — não é problema do n8n. Veja o log da
  execução no Actions; o mais provável é o programa de treinos ter sido
  reprovado pelo `scripts/treino.py`, que roda antes de gerar qualquer imagem.
