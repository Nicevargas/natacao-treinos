# "EU QUERO" — links do app no direct da @natacaocriativa

Desde 15/10/2026 o carrossel tem o slide 5 (propaganda do app) e a legenda pede
"Comente EU QUERO que a gente te manda o link do app no direct".

## Hoje

**A resposta é manual.** Quem cuida da @natacaocriativa responde no direct de
quem comentou, com a mensagem abaixo. A Meta permite **uma** resposta privada
até 7 dias depois do comentário.

## Mensagem para copiar

> Oi! Que bom que você quer treinar com a gente 💙
>
> 📱 Android (Google Play):
> https://play.google.com/store/apps/details?id=com.natacaocriativa.treinos
>
> 🍎 iPhone (App Store):
> https://apps.apple.com/br/app/id6820528444
>
> Todo dia tem um treino novo pronto no seu nível, com cronômetro série por
> série. Qualquer dúvida, responde aqui.

Resposta pública no comentário: `Te chamei no direct! 👀 Se não achar, olha em Solicitações de mensagem 💙`

## Para automatizar depois

Já existe o robô que faz isso para a @nicevargas.mkt:
`C:\Users\eunic\instagram-autoresposta` (webhook na Vercel). Ele atende **uma
conta por instalação**, porque a conta vem do token. Para a @natacaocriativa:

1. Outra instalação do mesmo código na Vercel, com o token da @natacaocriativa
   (o mesmo segredo `INSTAGRAM_ACCESS_TOKEN` do carrossel).
2. Webhook do campo `comments` no app da Meta `1584024343082090`
   (`natacaocriativa`, portfólio do Renato), com a chave secreta do **app do
   Instagram**, não a do Facebook.
3. Uma regra em `regras.json` com as palavras `eu quero`, `quero`, `app`,
   `link` e a mensagem acima nos dois campos (`mensagem_segue` e
   `mensagem_nao_segue`): o link do app vai para todo mundo, siga ou não.

O passo 2 depende de acesso de administrador ao app da Meta do portfólio do Renato.
