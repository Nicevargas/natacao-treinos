"""
cartao_nc.py - Slides do carrossel no Método Natação Criativa (desde 15/09/2026).

Mesma identidade de gerar_card.py (fundo, cabeçalho, rodapé, fontes e o ajuste
automático da fonte). Muda o miolo:

    1  capa        "Qual é o seu nível?" com zona, metros e duração de cada nível
    2  verde       Pré-condicionamento
    3  amarelo     Condicionamento
    4  vermelho    Aperfeiçoamento
    5  glossário   como ler: blocos, zonas e PSE, # e @, corretivo

Em cada treino: o objetivo do dia no alto, os blocos NC que existem naquele
nível, e em cada série a zona, o intervalo, a PSE e o corretivo com a dica.
"""
from datetime import date
from pathlib import Path

import gerar_card as base
import programa_nc as nc

esc = base.esc
AZUL, ROSA, AMARELO, VERDE = base.AZUL, base.ROSA, base.AMARELO, base.VERDE
CIANO = "#5FC9FF"

base.ICONES.setdefault(
    "alvo", '<circle cx="16" cy="16" r="11" fill="none" stroke="currentColor" stroke-width="3"/>'
            '<circle cx="16" cy="16" r="4.5"/>')
base.ICONES.setdefault(
    "onda", '<path d="M3 12q4.3-4 8.6 0t8.6 0 8.6 0M3 20q4.3-4 8.6 0t8.6 0 8.6 0" fill="none" '
            'stroke="currentColor" stroke-width="3" stroke-linecap="round"/>')

ESTILO_DO_BLOCO = {
    "ativacao": ("gota", AZUL),
    "preparacao": ("alvo", AMARELO),
    "desenvolvimento": ("nadador", ROSA),
    "consolidacao": ("costas", VERDE),
    "recuperacao": ("onda", CIANO),
}

# Cor da etiqueta de zona: das mais leves (frias) às mais intensas (quentes).
COR_DA_ZONA = {"A0": "#8FB4D8", "A1": VERDE, "A2": AMARELO, "A3": "#FF8A00",
               "AN": ROSA, "AA": "#9B7BFF"}
TEXTO_CLARO = {"AN", "AA"}


def chip_zona(zona: str, rotulo: str | None = None) -> str:
    cor_txt = "#fff" if zona in TEXTO_CLARO else "#06142e"
    return (f'<span class="zona" style="--z:{COR_DA_ZONA[zona]};color:{cor_txt}">'
            f'{esc(rotulo or zona)}</span>')


def series_html(series: list, compacto: bool) -> str:
    """Cabeçalho + etiqueta de zona + intervalo, e uma linha de apoio.

    A PSE de cada série não entra no slide: a etiqueta de zona já diz a
    intensidade e o glossário traz a PSE de cada zona. No corretivo, a repartição
    ("25m X · 25m nado completo") dá lugar a uma linha só com o nome e a dica --
    num treino de cinco blocos, as duas não cabem legíveis.
    """
    out = []
    for i, s in enumerate(series):
        if i:
            out.append('<div class="vao"></div>')
        cab = f'{esc(s["serie"])} {chip_zona(s["zona"])}'
        if s.get("intervalo"):
            cab += f' <span class="int">{esc(s["intervalo"])}</span>'
        if cor := s.get("corretivo"):
            apoio = (f'<span class="corretivo"><b>Corretivo:</b> {esc(cor["nome"])} + nado completo '
                     f'— “{esc(cor["dica"])}”</span>')
        elif s.get("detalhes"):
            apoio = f'<span class="cauda">{esc(" · ".join(s["detalhes"]))}</span>'
        else:
            apoio = ""
        if compacto or not apoio:
            out.append(f'<div class="serie">{cab} {apoio}</div>')
        else:
            out.append(f'<div class="serie">{cab}</div><div class="detalhe">{apoio}</div>')
    return "".join(out)


def bloco_html(nivel: dict, bloco: str, compacto: bool) -> str:
    series = nivel["blocos"].get(bloco)
    if not series:
        return ""
    icone, cor = ESTILO_DO_BLOCO[bloco]
    return (
        f'<div class="linha-bloco">'
        f'  <div class="selo" style="--cor:{cor}">{base.icone(icone, 46)}</div>'
        f'  <div class="corpo-bloco">'
        f'    <div class="tit-bloco"><span style="color:{cor}">{nc.NOME_DO_BLOCO[bloco]}</span>'
        f'      <span class="traco">–</span> <span class="metros">{nc.metros_do_bloco(nivel, bloco)}m</span></div>'
        f'    {series_html(series, compacto)}'
        f'  </div>'
        f'</div>')


def slide_treino(t: dict, chave: str, dados: dict, quando: date, logo, compacto: bool = False) -> str:
    n = t["niveis"][chave]
    r = dados["rotulos"][chave]
    total = nc.total_do_nivel(n)
    miolo = (
        base.cabecalho_html(logo)
        + '<div class="regua">Treino do dia</div>'
        + base.chips_html(quando, t["foco"])
        + f'<div class="tarja" style="--cor:{r["cor"]}">'
          f'  <div class="bolinha"></div>'
          f'  <div class="nome">{esc(r["nome"])}</div>'
          f'  {chip_zona(n["zona"], "Zona " + n["zona"])}'
          f'  <div class="m">{total}m <span class="dur">~{nc.minutos(n, chave)} min</span></div>'
          f'</div>'
        + '<div class="painel"><div class="conteudo" id="conteudo" style="--fs:26px">'
        + f'<div class="objetivo">{esc(n["objetivo"])}</div>'
        + "".join(bloco_html(n, b, compacto) for b in nc.BLOCOS)
        + '</div></div>'
        + base.rodape_html(logo, dados["handle"])
    )
    return pagina(miolo, quando)


def slide_capa(t: dict, dados: dict, quando: date, logo) -> str:
    opcoes = []
    for chave in nc.NIVEIS:
        r, n = dados["rotulos"][chave], t["niveis"][chave]
        opcoes.append(
            f'<div class="opcao" style="--cor:{r["cor"]}">'
            f'  <div class="bolinha"></div>'
            f'  <div class="op-txt">'
            f'    <div class="op-nome">{esc(r["nome"])}</div>'
            f'    <div class="op-sub">{chip_zona(n["zona"])} {nc.total_do_nivel(n)}m · ~{nc.minutos(n, chave)} min</div>'
            f'  </div>'
            f'</div>')
    miolo = (
        base.cabecalho_html(logo)
        + '<div class="regua">Escolha seu nível</div>'
        + base.chips_html(quando, t["foco"])
        + '<div class="painel"><div class="conteudo capa" style="--fs:30px">'
          '<div class="pergunta">Qual é o seu nível hoje?</div>'
        + "".join(opcoes)
        + '<div class="lema">Objetivo → intensidade → qualidade → volume.<br>'
          '<b>Treinamento precisa ter propósito.</b></div>'
          '</div></div>'
        + base.rodape_html(logo, dados["handle"])
    )
    return pagina(miolo, quando)


def slide_glossario(dados: dict, quando: date, logo) -> str:
    itens = "".join(
        f'<div class="verbete"><div class="termo">{esc(g["termo"])}</div>'
        f'<div class="texto">{esc(g["texto"])}</div></div>'
        for g in dados["glossario"])
    zonas = " ".join(chip_zona(z) for z in nc.ZONAS)
    miolo = (
        base.cabecalho_html(logo)
        + '<div class="regua">Como ler o treino</div>'
        + '<div class="painel"><div class="conteudo glossario" style="--fs:30px">'
        + f'<div class="faixa-zonas">{zonas}</div>'
        + itens
        + '<div class="lema"><b>Fez o treino? Conta pra gente nos comentários:</b><br>'
          'Intensidade 0 a 10 · Complexidade 0 a 10</div>'
          '</div></div>'
        + base.rodape_html(logo, dados["handle"])
    )
    return pagina(miolo, quando)


CSS_NC = f"""
  .zona {{
    display:inline-block; background:var(--z); border-radius:10px;
    padding:0 .38em; font-size:.8em; font-weight:800; line-height:1.4;
    vertical-align:.08em; letter-spacing:.3px;
  }}
  .int {{ font-weight:700; color:{AMARELO}; }}
  .corretivo {{ color:#ffd98a; font-weight:500; }}
  .corretivo b {{ color:{AMARELO}; }}
  .objetivo {{
    font-size:calc(var(--fs) * .98); line-height:1.3; color:#e6f0fc; font-weight:600;
    border-left:5px solid {AZUL}; padding:2px 0 2px 16px;
    margin:calc(var(--fs) * .2) 0 calc(var(--fs) * .3);
  }}
  .tarja .zona {{ font-size:26px; padding:2px 12px; margin-right:6px; }}
  .tarja .dur {{ font-family:"Corpo","Segoe UI",sans-serif; font-size:22px; font-weight:700; color:#dce9fb; }}
  /* Cinco blocos por slide: título e respiro um pouco menores que no programa antigo. */
  .tit-bloco {{ font-size:calc(var(--fs) * 1.22); margin-bottom:calc(var(--fs) * .1); }}
  .linha-bloco {{ padding:calc(var(--fs) * .4) 0; }}
  .vao {{ height:calc(var(--fs) * .35); }}
  .opcao .op-txt {{ flex:1; }}
  .opcao .op-nome {{
    font-family:"Titulo","Arial Narrow",sans-serif;
    font-size:calc(var(--fs) * 1.45); color:var(--cor); line-height:1.1;
  }}
  .opcao .op-sub {{ font-size:calc(var(--fs) * .95); font-weight:700; color:#dce9fb; margin-top:4px; }}
  .faixa-zonas {{ display:flex; gap:12px; justify-content:center; margin-bottom:calc(var(--fs) * .7); }}
  .faixa-zonas .zona {{ font-size:calc(var(--fs) * 1.05); }}
  .glossario .verbete {{ margin-bottom:calc(var(--fs) * .7); }}
"""


def pagina(miolo: str, quando: date) -> str:
    return base.pagina(miolo, quando.toordinal() % 997).replace("</style>", CSS_NC + "</style>", 1)


def gerar(quando: date, dados: dict, navegador, so_slide: int | None = None) -> list:
    t = nc.treino_de(dados, quando)
    logo = base.logo_uri()
    base.SAIDA.mkdir(exist_ok=True)
    prefixo = quando.isoformat()

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
        destino = base.SAIDA / f"{prefixo}_{nome}.jpg"
        fs, compacto = base.render(faz, destino, navegador)
        aviso = "  [compacto]" if compacto else ""
        if fs < base.MIN_LEGIVEL:
            aviso += f"  ATENÇÃO: abaixo de {base.MIN_LEGIVEL}px, texto apertado"
        print(f"  {destino.name}  (corpo {fs}px){aviso}")
        feitos.append(destino)

    if not so_slide:
        resumo = " / ".join(f"{t['niveis'][n]['zona']} {nc.total_do_nivel(t['niveis'][n])}m"
                            for n in nc.NIVEIS)
        print(f"  → dia {t['dia']}/{len(dados['treinos'])} · {t['mesociclo']} / {t['foco']} · {resumo}")
    return feitos


def programa_da_data(quando: date) -> tuple[dict, bool]:
    """(dados, é_nc). O Método NC vale da âncora de programa_nc.json em diante."""
    dados_nc = nc.carregar()
    if quando >= nc.ancora(dados_nc):
        return dados_nc, True
    return base.carregar(), False
