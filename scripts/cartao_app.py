"""
cartao_app.py - Slide de propaganda do app (desde 15/10/2026).

Entra entre os slides de piscina (vermelho) e os de águas abertas: quem acabou
de ver os três treinos do dia descobre que pode levá-los no celular. A chamada é
"comente EU QUERO", que pede os links no direct -- link na legenda não é
clicável no Instagram.

As lojas vêm de lojas.json e são conferidas na hora: a que ainda não abriu (a App
Store responde 404 até a Apple liberar) não aparece no slide nem na legenda.
Quando ela abrir, entra sozinha no post seguinte.
"""
import base64
import json
from datetime import date
from functools import lru_cache

import requests

import gerar_card as base

esc = base.esc
AZUL, ROSA, AMARELO, VERDE = base.AZUL, base.ROSA, base.AMARELO, base.VERDE

LOJAS = base.RAIZ / "lojas.json"
NOME_DA_LOJA = {"play": "Google Play", "apple": "App Store"}
SISTEMA = {"play": "Android", "apple": "iPhone"}


@lru_cache(maxsize=1)
def lojas_no_ar() -> tuple[str, ...]:
    """Chaves das lojas cujo link abre agora ("play", "apple"), na ordem do arquivo.

    Falha de rede conta como fora do ar: na dúvida o slide promete menos, nunca
    um link que não abre."""
    if not LOJAS.exists():
        return ()
    links = json.loads(LOJAS.read_text(encoding="utf-8"))
    no_ar = []
    for chave in ("play", "apple"):
        url = links.get(chave)
        if not url:
            continue
        try:
            r = requests.get(url, timeout=15, allow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0"})
            ok = r.status_code == 200
        except requests.RequestException:
            ok = False
        print(f"  loja {NOME_DA_LOJA[chave]}: {'no ar' if ok else 'fora do ar'}")
        if ok:
            no_ar.append(chave)
    return tuple(no_ar)


def sistemas(lojas: tuple[str, ...]) -> str:
    """"Android e iPhone", "Android" ou ""."""
    return " e ".join(SISTEMA[c] for c in lojas)


def _tela(nome: str) -> str:
    return "data:image/jpeg;base64," + base64.b64encode((base.MARCA / nome).read_bytes()).decode()


def slide(dados: dict, quando: date, logo, lojas: tuple[str, ...], compacto: bool = False) -> str:
    selos = "".join(
        f'<div class="selo-loja"><span class="sl-pq">Disponível no</span>'
        f'<span class="sl-nome">{NOME_DA_LOJA[c]}</span></div>'
        for c in lojas)
    recursos = [
        ("calendario", AZUL, "Treino do dia pronto, no seu nível"),
        ("nadador", ROSA, "Cronômetro série por série na piscina"),
        ("alvo", AMARELO, "Plano de semanas que cabe na sua rotina"),
        ("trofeu", VERDE, "Progresso, pontos e conquistas"),
    ]
    itens = "".join(
        f'<div class="recurso"><div class="selo" style="--cor:{cor}">{base.icone(ic, 40)}</div>'
        f'<div>{esc(txt)}</div></div>'
        for ic, cor, txt in recursos)
    miolo = (
        base.cabecalho_html(logo)
        + '<div class="regua">Treine com o app</div>'
        + '<div class="painel"><div class="conteudo app" id="conteudo" style="--fs:30px">'
          '<div class="pergunta">Leve o treino do dia no celular</div>'
          '<div class="vitrine">'
          f'  <div class="telas"><img class="tela t1" src="{_tela("app_inicio.jpg")}" alt="">'
          f'  <img class="tela t2" src="{_tela("app_treino.jpg")}" alt=""></div>'
          f'  <div class="recursos">{itens}</div>'
          '</div>'
        + (f'<div class="lojas">{selos}</div>' if selos else "")
        + '<div class="eu-quero">Comente <b>EU QUERO</b><br>'
          '<span>que a gente te manda o link no direct</span></div>'
          '</div></div>'
        + base.rodape_html(logo, dados["handle"])
    )
    return base.pagina(miolo, quando.toordinal() % 997).replace("</style>", CSS + "</style>", 1)


CSS = f"""
  .app .pergunta {{
    font-family:"Titulo","Arial Narrow",sans-serif;
    font-size:calc(var(--fs) * 1.7); text-align:center; color:#dce9fb;
    margin-bottom:calc(var(--fs) * .6);
  }}
  .vitrine {{ display:flex; align-items:center; gap:calc(var(--fs) * .9); }}
  .telas {{ position:relative; width:440px; height:560px; flex:none; }}
  .tela {{
    position:absolute; width:250px; border-radius:30px;
    border:7px solid #0b1b38; box-shadow:0 18px 40px rgba(0,0,0,.6);
  }}
  .tela.t1 {{ left:0; top:30px; transform:rotate(-5deg); }}
  .tela.t2 {{ left:180px; top:0; transform:rotate(4deg); }}
  .recursos {{ flex:1; }}
  .recurso {{
    display:flex; align-items:center; gap:18px;
    font-size:calc(var(--fs) * .95); font-weight:700; line-height:1.25;
    margin-bottom:calc(var(--fs) * .75);
  }}
  .recurso .selo {{ width:calc(var(--fs) * 2.1); height:calc(var(--fs) * 2.1); }}
  .lojas {{ display:flex; gap:18px; justify-content:center; margin-top:calc(var(--fs) * .5); }}
  .selo-loja {{
    display:flex; flex-direction:column; align-items:flex-start;
    background:#000; border:2px solid rgba(255,255,255,.55); border-radius:16px;
    padding:8px 26px 10px; min-width:260px;
  }}
  .sl-pq {{ font-size:18px; color:#dce9fb; letter-spacing:.3px; }}
  .sl-nome {{ font-size:34px; font-weight:800; line-height:1.05; }}
  .eu-quero {{
    margin-top:calc(var(--fs) * .8); text-align:center;
    border:3px solid {AMARELO}; border-radius:22px;
    background:linear-gradient(90deg, color-mix(in srgb, {ROSA} 35%, #061630),
                               color-mix(in srgb, {AZUL} 35%, #061630));
    padding:calc(var(--fs) * .5) calc(var(--fs) * .8);
    font-family:"Titulo","Arial Narrow",sans-serif;
    font-size:calc(var(--fs) * 1.5); line-height:1.1; letter-spacing:.5px;
  }}
  .eu-quero b {{ color:{AMARELO}; font-weight:400; }}
  .eu-quero span {{
    font-family:"Corpo","Segoe UI",sans-serif; font-size:calc(var(--fs) * .8);
    font-weight:600; color:#dce9fb; letter-spacing:0;
  }}
"""
