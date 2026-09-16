"""
cartao_aa.py - Slides de ÁGUAS ABERTAS do carrossel (slides 5 e 6).

A arte é da marca: marca/aguas_abertas_modelo.jpg ("1 Treino por dia", com o
nadador no mar e sete espaços com ícone fixo, feita a partir da imagem da Nice de
16/09/2026, com o "2.000m" de exemplo apagado). Este script só escreve nos
espaços em destaque:

    faixa azul        ÁGUAS ABERTAS
    abaixo da faixa   a metragem total do dia
    7 cartões         número, nome da parte, metros e as séries (programa_aa.PARTES,
                      na ordem dos ícones: pulmão, óculos, cronômetro, nadador,
                      ondas com nadador, mão, ondas)
    bilhete amarelo   TOTAL

A arte é quadrada e o carrossel é 4:5: ela vai no meio do slide, e as faixas de
cima e de baixo (a própria arte desfocada) trazem o dia, o nível e o aviso de
segurança. Um slide por nível.
"""
import base64
from datetime import date
from pathlib import Path

import gerar_card as base
import programa_aa as aa

esc = base.esc
MODELO = base.MARCA / "aguas_abertas_modelo.jpg"
LADO = 1254  # tamanho da arte original; as posições abaixo estão nessa escala

ROSA, CIANO, AMARELO, VERDE = "#FF2E8A", "#2BC0FF", "#FFD21F", "#A6F22E"

# (parte, x, y, largura, altura do cabeçalho, altura da faixa, cor) de cada cartão.
CARTOES = (
    ("respiracao", 35, 615, 580, 82, 53, ROSA),
    ("corretivos", 625, 615, 595, 82, 53, CIANO),
    ("ativacao", 35, 757, 580, 83, 48, AMARELO),
    ("pernas_braco", 625, 757, 595, 83, 48, VERDE),
    ("desenvolvimento", 35, 897, 580, 81, 54, CIANO),
    ("consolidacao", 625, 897, 595, 81, 54, ROSA),
    ("recuperacao", 35, 1040, 520, 82, 38, VERDE),
)
# Onde começa o texto do cabeçalho (depois do ícone), relativo ao cartão.
TEXTO_X = 180


def metros(m: int) -> str:
    return f"{m:,}".replace(",", ".") + "m"


def _curta(s: dict) -> str:
    cab = s["serie"].replace(" Crawl", "")
    linha = f'{esc(cab)} <b class="z">{esc(s["zona"])}</b>'
    if s.get("intervalo"):
        linha += f' <span class="int">{esc(s["intervalo"])}</span>'
    return linha


def descricao(series: list) -> str:
    linha1 = "  |  ".join(_curta(s) for s in series)
    apoio = []
    for s in series:
        if cor := s.get("corretivo"):
            apoio.append(f"Corretivo: {cor['nome']} + nado completo")
        elif s.get("detalhes"):
            apoio.append(" · ".join(s["detalhes"]))
    linha2 = f'<div class="apoio">{esc("  |  ".join(apoio))}</div>' if apoio else ""
    return f'<div class="l1">{linha1}</div>{linha2}'


def _modelo_uri() -> str:
    return "data:image/jpeg;base64," + base64.b64encode(MODELO.read_bytes()).decode()


def slide(t: dict, chave: str, dados: dict, quando: date, _compacto: bool = False) -> str:
    n = t["niveis"][chave]
    r = dados["rotulos"][chave]
    total = aa.total_do_nivel(n)
    arte = _modelo_uri()
    dia = base.DIAS_SEMANA[quando.weekday()]

    cartoes = []
    for i, (parte, x, y, w, hc, hf, cor) in enumerate(CARTOES, start=1):
        series = n["partes"][parte]
        cartoes.append(
            f'<div class="num" style="left:{x}px;top:{y}px;color:{"#07213f" if cor in (AMARELO, VERDE) else "#fff"}">{i:02d}</div>'
            f'<div class="cab" style="left:{x + TEXTO_X}px;top:{y}px;width:{w - TEXTO_X - 16}px;height:{hc}px">'
            f'  <div class="nome">{esc(aa.NOME_DA_PARTE[parte])}</div>'
            f'  <div class="m" style="color:{cor}">{metros(aa.metros_da_parte(n, parte))}</div>'
            f'</div>'
            f'<div class="desc" style="left:{x + 14}px;top:{y + hc + 1}px;width:{w - 28}px;height:{hf - 2}px">'
            f'{descricao(series)}</div>')

    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>
{base.fontes_css()}
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:{base.LARGURA}px; height:{base.ALTURA}px; overflow:hidden; background:#03101f; }}
body {{ font-family:"Corpo","Segoe UI",sans-serif; color:#fff; position:relative; }}
.borrao {{ position:absolute; inset:-60px; background:url({arte}) center/cover; filter:blur(28px) brightness(.45); }}
.faixa-topo, .faixa-base {{ position:absolute; left:0; right:0; height:135px; display:flex; flex-direction:column;
  align-items:center; justify-content:center; text-align:center; }}
.faixa-topo {{ top:0; }}
.faixa-base {{ bottom:0; }}
.dia {{ font-family:"Titulo"; font-size:44px; letter-spacing:1px; line-height:1.05; text-transform:uppercase; }}
.nivel {{ margin-top:8px; font-weight:800; font-size:24px; }}
.nivel span {{ background:{r["cor"]}; color:#1a1300; border-radius:30px; padding:3px 16px; }}
.nivel i {{ font-style:normal; margin-left:10px; color:#cfe6ff; }}
.aviso {{ font-weight:800; font-size:26px; }}
.marca {{ margin-top:6px; font-size:22px; color:#9fd4ff; font-weight:600; }}

.arte {{ position:absolute; left:0; top:135px; width:1080px; height:1080px; overflow:hidden; }}
.escala {{ position:absolute; left:0; top:0; width:{LADO}px; height:{LADO}px;
  transform:scale({base.LARGURA / LADO}); transform-origin:0 0; }}
.escala img {{ position:absolute; inset:0; width:{LADO}px; height:{LADO}px; }}
.escala > div {{ position:absolute; }}

.titulo-faixa {{ left:180px; top:420px; width:490px; height:90px; display:flex; align-items:center; justify-content:center;
  transform:rotate(-4deg); font-family:"Titulo"; font-size:52px; line-height:1.3; color:#07213f; letter-spacing:1px; }}
.total-grande {{ left:300px; top:488px; width:540px; height:110px; display:flex; align-items:center; justify-content:center;
  font-family:"Corpo"; font-weight:900; font-size:98px; color:{VERDE}; letter-spacing:-2px;
  text-shadow:0 4px 0 #0a2a06, 0 0 18px rgba(0,0,0,.6); }}

.num {{ width:62px; height:66px; display:flex; align-items:center; justify-content:center;
  font-family:"Titulo"; font-size:30px; }}
.cab {{ display:flex; flex-direction:column; justify-content:center; }}
.cab .nome {{ font-family:"Titulo"; font-size:34px; line-height:1; text-transform:uppercase; letter-spacing:.5px; }}
.cab .m {{ font-family:"Titulo"; font-size:38px; line-height:1.02; }}
.desc {{ display:flex; flex-direction:column; justify-content:center; overflow:hidden;
  font-size:21px; line-height:1.18; color:#eaf4ff; white-space:nowrap; }}
.desc .z {{ color:#9fd4ff; font-weight:800; }}
.desc .int {{ color:{AMARELO}; font-weight:700; }}
.desc .apoio {{ color:#b9d3ee; font-size:.9em; }}

.total-rot {{ left:745px; top:1050px; height:80px; display:flex; align-items:center;
  font-family:"Titulo"; font-size:40px; color:#fff; }}
.total-valor {{ left:870px; top:1043px; width:340px; height:95px; display:flex; align-items:center; justify-content:flex-end;
  font-family:"Corpo"; font-weight:900; font-size:66px; color:{VERDE}; letter-spacing:-1px; }}
</style></head><body>
<div class="borrao"></div>
<div class="faixa-topo">
  <div class="dia">{dia}, {quando:%d/%m} · {esc(t["foco"])}</div>
  <div class="nivel"><span>{esc(r["nome"])}</span><i>Zona {esc(n["zona"])} · ~{aa.minutos(n, chave)} min</i></div>
</div>
<div class="arte"><div class="escala">
  <img src="{arte}" alt="">
  <div class="titulo-faixa">ÁGUAS ABERTAS</div>
  <div class="total-grande">{metros(total)}</div>
  {"".join(cartoes)}
  <div class="total-rot">TOTAL</div>
  <div class="total-valor">{metros(total)}</div>
</div></div>
<div class="faixa-base">
  <div class="aviso">No mar ou no lago, nunca nade sozinho.</div>
  <div class="marca">Fez esse treino? Marca {esc(dados["handle"])}</div>
</div>
</body></html>"""


# Encolhe o texto de cada faixa até caber (largura e altura), sem descer de 13px
# na escala da arte. Devolve o menor tamanho usado, já na escala do slide.
AJUSTE = """() => {
  let menor = 99;
  document.querySelectorAll('.desc').forEach((el) => {
    let px = 21;
    el.style.fontSize = px + 'px';
    while ((el.scrollWidth > el.clientWidth || el.scrollHeight > el.clientHeight) && px > 13) {
      px -= 0.5; el.style.fontSize = px + 'px';
    }
    menor = Math.min(menor, px);
  });
  return Math.round(menor * %s * 10) / 10;
}""" % (base.LARGURA / LADO)


def render(construir, destino: Path, navegador) -> float:
    pag = navegador.new_page(viewport={"width": base.LARGURA, "height": base.ALTURA}, device_scale_factor=1)
    pag.set_content(construir(False), wait_until="load")
    fs = pag.evaluate(AJUSTE)
    pag.screenshot(path=str(destino), type="jpeg", quality=92)
    pag.close()
    return fs
