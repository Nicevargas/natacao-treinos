"""
gerar_card.py - Carrossel diário "Cada Dia 1 Treino" da @natacaocriativa

Cinco slides JPEG 1080x1350 (4:5, o retrato máximo que a API da Meta aceita):

    0  capa         "Escolha seu desafio" com as três metragens do dia
    1  verde        menor volume
    2  amarelo      intermediário
    3  vermelho     maior volume + técnica (o único com EDUCATIVOS)
    4  glossário    o que são EDUCATIVOS e SCULLING

O texto vem de treinos.json. O ciclo tem 28 dias e gira sozinho: o índice sai
de (data - âncora) mod 28, então qualquer data futura já tem treino.

Uso:
    python scripts/gerar_card.py                    # carrossel de hoje
    python scripts/gerar_card.py --data 2026-09-05
    python scripts/gerar_card.py --so-slide 3       # só um slide, para iterar
"""
import argparse
import base64
import json
import sys
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import treino  # noqa: E402  -- leitura e metragem do programa

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

RAIZ = Path(__file__).resolve().parent.parent
TREINOS = RAIZ / "treinos.json"
MARCA = RAIZ / "marca"
SAIDA = RAIZ / "cards"

LARGURA, ALTURA = 1080, 1350

DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

# Paleta tirada da arte de referência da marca.
AZUL = "#1E8BE0"
ROSA = "#E01B62"
AMARELO = "#F7B90B"
VERDE = "#8DC63F"

ORDEM_NIVEIS = ["verde", "amarelo", "vermelho"]


# ------------------------------------------------------------------- dados

carregar = treino.carregar
treino_de = treino.treino_de


def _uri(nome: str) -> str | None:
    arq = MARCA / nome
    if not arq.exists():
        return None
    return "data:image/png;base64," + base64.b64encode(arq.read_bytes()).decode()


def logo_uri() -> str | None:
    """O logo é arte da marca, não algo que dê para reproduzir em código.
    Sem o PNG em marca/, o cabeçalho cai num fallback de texto para não travar
    o resto do layout."""
    return _uri("logo.png")


def splat_uri() -> str | None:
    """O rodapé usa só o splat, sem o letreiro -- igual à arte de referência."""
    return _uri("splat.png")


def fontes_css() -> str:
    """As fontes vão embutidas no HTML.

    O runner do GitHub Actions é Linux e não tem Franklin Gothic nem Segoe UI:
    o card sairia com outra fonte, outras quebras de linha e outro título. Com
    Anton e Inter embarcadas (licença SIL OFL), o render é idêntico aqui e lá,
    e não depende de rede nem de fonte instalada.
    """
    FONTES = RAIZ / "fontes"
    faces = [("Titulo", "Anton-Regular.ttf", "400"),
             ("Corpo", "Inter-Variable.ttf", "100 900")]
    css = []
    for familia, arquivo, peso in faces:
        caminho = FONTES / arquivo
        if not caminho.exists():
            continue
        b64 = base64.b64encode(caminho.read_bytes()).decode()
        css.append(f"@font-face{{font-family:'{familia}';font-weight:{peso};"
                   f"font-display:block;"
                   f"src:url(data:font/ttf;base64,{b64}) format('truetype');}}")
    return "".join(css)


# ------------------------------------------------------------------ pedaços

def esc(txt: str) -> str:
    return txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


ICONES = {
    "gota": '<path d="M16 3C16 3 7 13 7 19a9 9 0 0 0 18 0c0-6-9-16-9-16z"/>',
    # Nado livre: cabeça, braço estendido à frente e a água embaixo.
    "nadador": ('<circle cx="21" cy="8" r="3.8"/>'
                '<path d="M5 10 15 16 28 12.5" fill="none" stroke="currentColor" '
                'stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>'
                '<path d="M2 22q4.5-3.4 9 0t9 0 9 0" fill="none" stroke="currentColor" '
                'stroke-width="2.6" stroke-linecap="round"/>'
                '<path d="M2 27.5q4.5-3.4 9 0t9 0 9 0" fill="none" stroke="currentColor" '
                'stroke-width="2.6" stroke-linecap="round"/>'),
    # Costas: mesma figura espelhada, braço indo para trás.
    "costas": ('<circle cx="11" cy="8" r="3.8"/>'
               '<path d="M27 10 17 16 4 12.5" fill="none" stroke="currentColor" '
               'stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>'
               '<path d="M2 22q4.5-3.4 9 0t9 0 9 0" fill="none" stroke="currentColor" '
               'stroke-width="2.6" stroke-linecap="round"/>'
               '<path d="M2 27.5q4.5-3.4 9 0t9 0 9 0" fill="none" stroke="currentColor" '
               'stroke-width="2.6" stroke-linecap="round"/>'),
    "trofeu": ('<path d="M11 5h10v6a5 5 0 0 1-10 0z"/>'
               '<path d="M11 7H8a3 3 0 0 0 3 3M21 7h3a3 3 0 0 1-3 3" fill="none" '
               'stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
               '<path d="M16 16v5M12 25h8v2h-8z" fill="none" stroke="currentColor" '
               'stroke-width="2.4" stroke-linecap="round"/>'),
    "calendario": ('<rect x="5" y="7" width="22" height="20" rx="3" fill="none" '
                   'stroke="currentColor" stroke-width="2.4"/>'
                   '<path d="M5 13h22M11 4v6M21 4v6" fill="none" stroke="currentColor" '
                   'stroke-width="2.4" stroke-linecap="round"/>'),
    "coracao": ('<path d="M16 27S5 20 5 13a6 6 0 0 1 11-3 6 6 0 0 1 11 3c0 7-11 14-11 14z"/>'),
}


def icone(nome: str, tam: int = 32) -> str:
    return (f'<svg class="ic" viewBox="0 0 32 32" width="{tam}" height="{tam}" '
            f'fill="currentColor">{ICONES[nome]}</svg>')


# Peça de quebra-cabeça: motivo da marca. Uma só forma, girada e recolorida em
# cada canto -- repetir a mesma peça sem rodar entrega o truque na hora.
# Dois pinos (topo e direita) e dois soquetes (base e esquerda). Peça com os
# quatro lados salientes vira flor, não quebra-cabeça.
PECA = ("M0,0 H35 C35,-14 65,-14 65,0 H100 V35 C114,35 114,65 100,65 V100 H65 "
        "C65,86 35,86 35,100 H0 V65 C14,65 14,35 0,35 Z")

PECAS_POS = [
    # (x%, y%, tamanho px, giro, cor, opacidade)
    (-4, 1, 190, -18, ROSA, 1.0),
    (57, -6, 150, 12, AZUL, 1.0),
    (88, 6, 165, 28, ROSA, 1.0),
    (-6, 27, 150, 8, AMARELO, 1.0),
    (86, 24, 155, -14, VERDE, 1.0),
    (-7, 63, 140, 22, AZUL, 1.0),
    (89, 74, 170, -8, ROSA, 1.0),
]


def pecas_html() -> str:
    out = []
    for x, y, tam, giro, cor, op in PECAS_POS:
        out.append(
            f'<svg class="peca" viewBox="-18 -18 136 136" width="{tam}" height="{tam}" '
            f'style="left:{x}%;top:{y}%;transform:rotate({giro}deg);opacity:{op}">'
            f'<path d="{PECA}" fill="{cor}"/></svg>')
    return "".join(out)


def series_html(series: list, compacto: bool = False) -> str:
    """Cada série é cabeçalho + detalhes + intervalo. O papel de cada linha vem
    da estrutura, não de adivinhar pelo texto.

    No modo compacto os detalhes vão para a mesma linha, separados por ponto.
    Um treino de 3.500m tem uma dúzia de séries: em linhas separadas, o ajuste
    automático derruba o corpo para ~16px, que ninguém lê no celular. Melhor
    perder o empilhamento do que perder a legibilidade.
    """
    out = []
    for i, s in enumerate(series):
        if i:
            out.append('<div class="vao"></div>')
        det = s.get("detalhes", [])
        intv = s.get("intervalo")

        if compacto:
            cauda = " · ".join(det)
            if intv:
                cauda += f'{" · " if cauda else ""}Int: {intv}'
            extra = f' <span class="cauda">{esc(cauda)}</span>' if cauda else ""
            out.append(f'<div class="serie">{esc(s["serie"])}{extra}</div>')
            continue

        out.append(f'<div class="serie">{esc(s["serie"])}</div>')
        for d in det:
            out.append(f'<div class="detalhe">{esc(d)}</div>')
        if intv:
            out.append(f'<div class="intervalo">Intervalo: {esc(intv)}</div>')
    return "".join(out)


def bloco_html(icone_nome: str, cor: str, titulo: str, metros: int, series: list,
               compacto: bool = False) -> str:
    return (
        f'<div class="linha-bloco">'
        f'  <div class="selo" style="--cor:{cor}">{icone(icone_nome, 46)}</div>'
        f'  <div class="corpo-bloco">'
        f'    <div class="tit-bloco"><span style="color:{cor}">{esc(titulo)}</span>'
        f'      <span class="traco">–</span> <span class="metros">{metros}m</span></div>'
        f'    {series_html(series, compacto)}'
        f'  </div>'
        f'</div>')


def cabecalho_html(logo: str | None) -> str:
    marca = (f'<img class="logo" src="{logo}" alt="">' if logo
             else '<div class="logo-falso">NATAÇÃO<br><b>CRIATIVA</b>'
                  '<div class="aviso">logo pendente</div></div>')
    return (f'<header>{marca}<div class="risco"></div>'
            f'<h1>Cada dia<br><em>1 treino</em></h1></header>')


def rodape_html(_logo: str | None, handle: str) -> str:
    splat = splat_uri()
    marca = (f'<img class="mini-logo" src="{splat}" alt="">' if splat
             else '<div class="mini-falso">NC</div>')
    return (f'<footer>{marca}'
            f'<div class="chamada">Fez esse treino?<br>'
            f'<b>Marca {esc(handle)}</b></div>'
            f'<div class="balao">{icone("coracao", 34)}</div></footer>')


# --------------------------------------------------------------------- CSS

def css() -> str:
    return f"""
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html, body {{ width:{LARGURA}px; height:{ALTURA}px; overflow:hidden; }}
  body {{
    font-family:"Corpo","Segoe UI",system-ui,sans-serif;
    background:#040c20; color:#fff; position:relative;
  }}

  /* ------------------------------------------------------------- fundo */
  .fundo {{ position:absolute; inset:0; z-index:0; overflow:hidden; }}
  .fundo .base {{
    position:absolute; inset:0;
    background:
      radial-gradient(120% 62% at 50% 100%, #0d3d78 0%, #071c3f 46%, #040c20 100%),
      linear-gradient(#08214a, #040c20);
    background-color:#05122c;
  }}
  .fundo svg.agua {{
    position:absolute; inset:0; width:100%; height:100%;
    mix-blend-mode:screen; opacity:.20;
  }}
  .peca {{ position:absolute; filter:drop-shadow(0 6px 14px rgba(0,0,0,.45)); }}
  .veu {{
    position:absolute; inset:0;
    background:radial-gradient(78% 55% at 50% 46%, rgba(4,12,32,.86) 0%,
                               rgba(4,12,32,.55) 55%, rgba(4,12,32,.25) 100%);
  }}

  .folha {{
    position:relative; z-index:1; width:100%; height:100%;
    display:flex; flex-direction:column; padding:30px 46px 24px;
  }}

  /* ----------------------------------------------------------- cabeçalho */
  header {{ display:flex; align-items:center; gap:22px; }}
  .logo {{ width:300px; height:auto; flex:none; }}
  .logo-falso {{
    width:300px; flex:none; text-align:center; line-height:1.05;
    font-family:"Titulo","Arial Narrow",sans-serif;
    font-size:44px; color:{AZUL}; letter-spacing:1px;
  }}
  .logo-falso b {{ color:#fff; }}
  .logo-falso .aviso {{
    font-family:"Corpo","Segoe UI",sans-serif; font-size:15px; letter-spacing:.5px;
    color:{AMARELO}; margin-top:8px; opacity:.8;
  }}
  .risco {{
    width:5px; align-self:stretch; border-radius:3px; flex:none;
    background:linear-gradient(180deg,{ROSA},{AMARELO},{VERDE},{AZUL});
  }}
  header h1 {{
    flex:1;
    font-family:"Titulo","Arial Narrow",Impact,sans-serif;
    font-size:86px; line-height:.9; letter-spacing:1px; text-transform:uppercase;
    text-shadow:0 5px 18px rgba(0,0,0,.6);
  }}
  header h1 em {{ font-style:normal; color:{AZUL}; }}

  /* ------------------------------------------------------------- réguas */
  .regua {{
    display:flex; align-items:center; gap:20px; margin-top:16px;
    font-family:"Titulo","Arial Narrow",sans-serif;
    font-size:36px; letter-spacing:5px; text-transform:uppercase;
  }}
  .regua::before, .regua::after {{
    content:""; flex:1; height:3px; border-radius:2px;
  }}
  .regua::before {{ background:linear-gradient(90deg,transparent,{ROSA},{AMARELO}); }}
  .regua::after  {{ background:linear-gradient(90deg,{AZUL},{VERDE},transparent); }}

  /* -------------------------------------------------------------- chips */
  .chips {{ display:flex; gap:14px; margin-top:14px; }}
  .chip {{
    display:flex; align-items:center; gap:10px;
    border-radius:999px; padding:8px 20px 8px 14px;
    font-size:25px; font-weight:700; color:#fff;
    box-shadow:0 5px 14px rgba(0,0,0,.4);
  }}
  .chip .ic {{ opacity:.95; }}

  .tarja {{
    margin-top:11px; display:flex; align-items:center; gap:16px;
    border:3px solid var(--cor); border-radius:18px;
    background:linear-gradient(90deg, color-mix(in srgb, var(--cor) 26%, #061630),
                               rgba(6,22,48,.94));
    padding:10px 22px;
  }}
  .tarja .bolinha {{
    width:24px; height:24px; border-radius:50%; background:var(--cor); flex:none;
    box-shadow:0 0 16px var(--cor);
  }}
  .tarja .nome {{
    flex:1; font-size:30px; font-weight:700; letter-spacing:.4px;
  }}
  .tarja .m {{
    font-family:"Titulo","Arial Narrow",sans-serif;
    font-size:40px; color:var(--cor);
  }}

  /* ------------------------------------------------------------- painel */
  .painel {{
    flex:1; margin-top:12px;
    border:2px solid rgba(120,180,255,.28); border-radius:26px;
    background:rgba(5,16,38,.94);
    box-shadow:0 16px 40px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.06);
    padding:12px 30px; display:flex; flex-direction:column; justify-content:center;
    overflow:hidden;
  }}
  .conteudo {{ font-size:var(--fs); line-height:1.3; }}

  .linha-bloco {{ display:flex; gap:22px; padding:calc(var(--fs) * .58) 0; }}
  .linha-bloco + .linha-bloco {{ border-top:2px solid rgba(120,180,255,.18); }}
  .selo {{
    width:calc(var(--fs) * 2.5); height:calc(var(--fs) * 2.5);
    border-radius:50%; background:var(--cor); color:#fff; flex:none;
    display:flex; align-items:center; justify-content:center;
    box-shadow:0 6px 16px rgba(0,0,0,.45);
  }}
  .selo .ic {{ width:60%; height:60%; }}
  .corpo-bloco {{ flex:1; border-left:3px solid rgba(120,180,255,.22); padding-left:22px; }}
  .tit-bloco {{
    font-family:"Titulo","Arial Narrow",sans-serif;
    font-size:calc(var(--fs) * 1.4); letter-spacing:.6px;
    margin-bottom:calc(var(--fs) * .16);
  }}
  .tit-bloco .traco, .tit-bloco .metros {{ color:#dce9fb; }}
  .serie {{ font-weight:700; color:#fff; }}
  .cauda {{ font-weight:400; color:#a9c2e0; }}
  .detalhe {{ font-weight:400; color:#a9c2e0; }}
  .intervalo {{ font-weight:700; color:{AMARELO}; }}
  .vao {{ height:calc(var(--fs) * .5); }}

  .total {{
    display:flex; align-items:center; gap:20px;
    border-top:2px solid rgba(120,180,255,.18);
    padding-top:calc(var(--fs) * .55); margin-top:calc(var(--fs) * .3);
  }}
  .total .selo {{ background:{AZUL}; }}
  .total .txt {{
    font-family:"Titulo","Arial Narrow",sans-serif;
    font-size:calc(var(--fs) * 1.7); letter-spacing:.5px;
  }}
  .total .txt b {{ color:{AZUL}; }}

  /* ------------------------------------------------------------- rodapé */
  footer {{
    margin-top:13px; display:flex; align-items:center; gap:20px;
    border:3px solid {ROSA}; border-radius:26px;
    background:rgba(6,20,46,.72); padding:11px 24px;
  }}
  .mini-logo {{ width:74px; height:74px; object-fit:contain; flex:none; }}
  .mini-falso {{
    width:74px; height:74px; border-radius:50%; flex:none;
    background:linear-gradient(135deg,{ROSA},{AMARELO},{VERDE},{AZUL});
    display:flex; align-items:center; justify-content:center;
    font-weight:800; font-size:30px; color:#06142e;
  }}
  .chamada {{ flex:1; font-size:30px; line-height:1.2; }}
  .chamada b {{ color:{AZUL}; }}
  .balao {{
    width:64px; height:64px; border-radius:20px; flex:none;
    background:{ROSA}; color:#fff;
    display:flex; align-items:center; justify-content:center;
    box-shadow:0 6px 16px rgba(0,0,0,.45);
  }}
"""


def fundo_html(semente: int) -> str:
    return f"""
  <div class="fundo">
    <div class="base"></div>
    <svg class="agua" xmlns="http://www.w3.org/2000/svg">
      <filter id="caustica" x="-5%" y="-5%" width="110%" height="110%">
        <feTurbulence type="fractalNoise" baseFrequency="0.010 0.016"
                      numOctaves="3" seed="{semente}" result="t"/>
        <feColorMatrix in="t" type="luminanceToAlpha" result="a"/>
        <feComponentTransfer in="a" result="v">
          <feFuncA type="table" tableValues="0 0 0.05 1 0.05 0 0"/>
        </feComponentTransfer>
        <feGaussianBlur in="v" stdDeviation="1.1" result="vb"/>
        <feFlood flood-color="#5fc9ff" result="cor"/>
        <feComposite in="cor" in2="vb" operator="in"/>
      </filter>
      <rect width="100%" height="100%" filter="url(#caustica)"/>
    </svg>
    {pecas_html()}
    <div class="veu"></div>
  </div>"""


# ------------------------------------------------------------------ slides

def pagina(miolo: str, semente: int) -> str:
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<style>{fontes_css()}{css()}</style></head><body>'
            f'{fundo_html(semente)}<div class="folha">{miolo}</div>'
            f'</body></html>')


def chips_html(quando: date, foco: str) -> str:
    return (
        f'<div class="chips">'
        f'  <div class="chip" style="background:{ROSA}">{icone("calendario", 26)}'
        f'    {quando.strftime("%d/%m/%Y")}</div>'
        f'  <div class="chip" style="background:{AMARELO};color:#3a2a00">'
        f'    {icone("calendario", 26)}{DIAS_SEMANA[quando.weekday()]}</div>'
        f'  <div class="chip" style="background:{AZUL}">{icone("gota", 26)}'
        f'    {esc(foco)}</div>'
        f'</div>')


def slide_treino(t: dict, chave: str, dados: dict, quando: date, logo,
                 compacto: bool = False) -> str:
    n = t["niveis"][chave]
    r = dados["rotulos"][chave]
    total = treino.total_do_nivel(n)
    m = {b: treino.metros_do_bloco(n[b]) for b in treino.BLOCOS}
    miolo = (
        cabecalho_html(logo)
        + '<div class="regua">Treino do dia</div>'
        + chips_html(quando, t["foco"])
        + f'<div class="tarja" style="--cor:{r["cor"]}">'
          f'  <div class="bolinha"></div>'
          f'  <div class="nome">{esc(r["nome"])}</div>'
          f'  <div class="m">{total}m</div>'
          f'</div>'
        + '<div class="painel"><div class="conteudo" id="conteudo" style="--fs:26px">'
        + bloco_html("gota", AZUL, "AQUECIMENTO", m["aquecimento"], n["aquecimento"], compacto)
        + bloco_html("nadador", ROSA, "PARTE PRINCIPAL", m["principal"], n["principal"], compacto)
        + bloco_html("costas", VERDE, "PARTE FINAL", m["final"], n["final"], compacto)
        + f'<div class="total"><div class="selo">{icone("trofeu", 46)}</div>'
          f'  <div class="txt">TOTAL: <b>{total}m</b></div></div>'
        + '</div></div>'
        + rodape_html(logo, dados["handle"])
    )
    return pagina(miolo, quando.toordinal() % 997)


def slide_capa(t: dict, dados: dict, quando: date, logo) -> str:
    opcoes = []
    for chave in ORDEM_NIVEIS:
        r, n = dados["rotulos"][chave], t["niveis"][chave]
        opcoes.append(
            f'<div class="opcao" style="--cor:{r["cor"]}">'
            f'  <div class="bolinha"></div>'
            f'  <div class="op-m">{treino.total_do_nivel(n)}m</div>'
            f'  <div class="op-nome">{esc(r["nome"])}</div>'
            f'</div>')
    miolo = (
        cabecalho_html(logo)
        + '<div class="regua">Escolha seu desafio</div>'
        + chips_html(quando, t["foco"])
        + '<div class="painel"><div class="conteudo capa" style="--fs:30px">'
          '<div class="pergunta">Qual é o seu treino de hoje?</div>'
        + "".join(opcoes)
        + '<div class="lema">Metragem é quantidade.<br>'
          '<b>Treinamento precisa ter propósito.</b></div>'
          '</div></div>'
        + rodape_html(logo, dados["handle"])
    )
    return pagina(miolo, quando.toordinal() % 997)


def slide_glossario(dados: dict, quando: date, logo) -> str:
    itens = "".join(
        f'<div class="verbete">'
        f'  <div class="termo">{esc(g["termo"])}</div>'
        f'  <div class="texto">{esc(g["texto"])}</div>'
        f'</div>'
        for g in dados["glossario"])
    miolo = (
        cabecalho_html(logo)
        + '<div class="regua">Entenda os termos</div>'
        + '<div class="painel"><div class="conteudo glossario" style="--fs:30px">'
        + itens
        + '<div class="lema">Cada exercício tem um propósito.<br>'
          '<b>Fez o treino? Conta pra gente nos comentários:</b><br>'
          'Intensidade 0 a 10 · Complexidade 0 a 10</div>'
          '</div></div>'
        + rodape_html(logo, dados["handle"])
    )
    return pagina(miolo, quando.toordinal() % 997)


CSS_EXTRA = f"""
  .capa .pergunta {{
    font-family:"Titulo","Arial Narrow",sans-serif;
    font-size:calc(var(--fs) * 1.7); text-align:center; color:#dce9fb;
    margin-bottom:calc(var(--fs) * .9);
  }}
  .opcao {{
    display:flex; align-items:center; gap:20px;
    border:3px solid var(--cor); border-radius:20px;
    background:linear-gradient(90deg, color-mix(in srgb, var(--cor) 22%, transparent),
                               rgba(255,255,255,.02));
    padding:calc(var(--fs) * .62) calc(var(--fs) * .8);
    margin-bottom:calc(var(--fs) * .55);
  }}
  .opcao .bolinha {{
    width:calc(var(--fs) * .9); height:calc(var(--fs) * .9); border-radius:50%;
    background:var(--cor); flex:none; box-shadow:0 0 18px var(--cor);
  }}
  .opcao .op-m {{
    font-family:"Titulo","Arial Narrow",sans-serif;
    font-size:calc(var(--fs) * 1.85); color:var(--cor); width:calc(var(--fs) * 4.6);
  }}
  .opcao .op-nome {{ flex:1; font-size:calc(var(--fs) * .98); font-weight:700; }}
  .lema {{
    margin-top:calc(var(--fs) * .8); text-align:center;
    font-size:calc(var(--fs) * .92); line-height:1.35; color:#a9c2e0;
  }}
  .lema b {{ color:#fff; }}

  .verbete {{ margin-bottom:calc(var(--fs) * .9); }}
  .verbete .termo {{
    font-family:"Titulo","Arial Narrow",sans-serif;
    font-size:calc(var(--fs) * 1.35); color:{AZUL}; letter-spacing:.8px;
    margin-bottom:calc(var(--fs) * .2);
  }}
  .verbete .texto {{ font-size:calc(var(--fs) * .95); line-height:1.34; color:#cfe0f5; }}
"""


# ----------------------------------------------------------------- render

AJUSTE = """() => {
  const painel = document.querySelector('.painel');
  const alvo   = document.getElementById('conteudo') || document.querySelector('.conteudo');
  if (!alvo) return 0;
  const cabe = (px) => {
    alvo.style.setProperty('--fs', px + 'px');
    return alvo.scrollHeight <= painel.clientHeight - 24;
  };
  let lo = 12, hi = 40, melhor = 12;
  for (let i = 0; i < 26; i++) {
    const meio = (lo + hi) / 2;
    if (cabe(meio)) { melhor = meio; lo = meio; } else { hi = meio; }
  }
  alvo.style.setProperty('--fs', melhor + 'px');
  return Math.round(melhor * 10) / 10;
}"""


# Abaixo disto o texto não se lê num feed de celular: 1080px de largura viram
# cerca de 400pt na tela real, então 24px aqui é ~9pt na mão do leitor.
MIN_LEGIVEL = 24


def render(construir, destino: Path, navegador) -> tuple:
    """`construir(compacto)` devolve o HTML. Tenta o layout arejado; se o ajuste
    automático tiver de encolher o corpo abaixo do legível, refaz compacto."""
    ultimo = (0.0, False)
    for compacto in (False, True):
        html = construir(compacto).replace("</style>", CSS_EXTRA + "</style>")
        pag = navegador.new_page(viewport={"width": LARGURA, "height": ALTURA},
                                 device_scale_factor=1)
        pag.set_content(html, wait_until="load")
        fs = pag.evaluate(AJUSTE)
        ultimo = (fs, compacto)
        if fs >= MIN_LEGIVEL or compacto:
            pag.screenshot(path=str(destino), type="jpeg", quality=92)
            pag.close()
            return ultimo
        pag.close()
    return ultimo


def gerar(quando: date, dados: dict, navegador, so_slide: int | None = None) -> list:
    t = treino_de(dados, quando)
    logo = logo_uri()
    SAIDA.mkdir(exist_ok=True)
    base = quando.isoformat()

    receitas = [
        ("1-capa", lambda c: slide_capa(t, dados, quando, logo)),
        ("2-verde", lambda c: slide_treino(t, "verde", dados, quando, logo, c)),
        ("3-amarelo", lambda c: slide_treino(t, "amarelo", dados, quando, logo, c)),
        ("4-vermelho", lambda c: slide_treino(t, "vermelho", dados, quando, logo, c)),
        ("5-glossario", lambda c: slide_glossario(dados, quando, logo)),
    ]

    feitos = []
    for i, (nome, faz) in enumerate(receitas, start=1):
        if so_slide and i != so_slide:
            continue
        destino = SAIDA / f"{base}_{nome}.jpg"
        fs, compacto = render(faz, destino, navegador)
        aviso = "  [compacto]" if compacto else ""
        if fs < MIN_LEGIVEL:
            aviso += f"  ATENÇÃO: abaixo de {MIN_LEGIVEL}px, texto apertado"
        print(f"  {destino.name}  (corpo {fs}px){aviso}")
        feitos.append(destino)

    if not so_slide:
        totais = " / ".join(f"{treino.total_do_nivel(t['niveis'][n])}m"
                            for n in ORDEM_NIVEIS)
        print(f"  → dia {t['dia']}/{len(dados['treinos'])} · "
              f"{t['bloco']} / {t['foco']} · {totais}")
    return feitos


def main():
    ap = argparse.ArgumentParser(description="Gera o carrossel do treino do dia.")
    ap.add_argument("--data", help="AAAA-MM-DD (padrão: hoje)")
    ap.add_argument("--so-slide", type=int, choices=[1, 2, 3, 4, 5],
                    help="Renderiza apenas um slide.")
    args = ap.parse_args()

    quando = date.fromisoformat(args.data) if args.data else date.today()
    dados = carregar()
    with sync_playwright() as p:
        nav = p.chromium.launch()
        gerar(quando, dados, nav, args.so_slide)
        nav.close()


if __name__ == "__main__":
    main()
