"""
programa_nc.py - Programa "Cada Dia 1 Treino" no Método Natação Criativa.

Vale da âncora de programa_nc.json (15/09/2026) em diante. Antes dela o
carrossel sai de treinos.json; postar_treino.py escolhe pela data.

O método manda na ordem: OBJETIVO -> INTENSIDADE -> QUALIDADE -> VOLUME. Por
isso a auditoria não exige metragem redonda nem faixa de metros por nível: ela
confere se a intensidade, as pausas e a proporção da zona predominante fazem
sentido para o objetivo do dia e para o nível de quem nada.

Uma série:
    {"serie": "8x50m Crawl", "zona": "A1", "pse": "3-4", "intervalo": "#20\\"",
     "detalhes": ["25m mão fechada", "25m nado completo"],
     "corretivo": {"nome": "...", "objetivo": "...", "dica": "..."}}

  zona       A0 (recuperação ativa), A1, A2, A3, AN ou AA
  pse        faixa da percepção de esforço, 0 a 10 ("3-4"), ou "máx" no AA
  intervalo  aberto "#20\\"" (descansa 20 s) ou fechado "@1'45\\"" (sai a cada 1'45")
  corretivo  o antigo "educativo": nasce de um objetivo e volta ao nado completo

A distância sai do cabeçalho ("8x50m" = 400m); os detalhes repartem o que já foi
contado e não somam.

Uso:
    python scripts/programa_nc.py        # resumo dos 28 dias + auditoria
"""
import json
import re
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO = RAIZ / "programa_nc.json"

NIVEIS = ("verde", "amarelo", "vermelho")
BLOCOS = ("ativacao", "preparacao", "desenvolvimento", "consolidacao", "recuperacao")
NOME_DO_BLOCO = {
    "ativacao": "ATIVAÇÃO",
    "preparacao": "PREPARAÇÃO",
    "desenvolvimento": "DESENVOLVIMENTO",
    "consolidacao": "CONSOLIDAÇÃO",
    "recuperacao": "RECUPERAÇÃO",
}
# "Só os blocos necessários": preparação e consolidação podem faltar.
OBRIGATORIOS = ("ativacao", "desenvolvimento", "recuperacao")

ZONAS = ("A0", "A1", "A2", "A3", "AN", "AA")
FORTES = ("A3", "AN")

# PSE aceitável em cada zona (escala 0-10). AA é prescrito por duração, não PSE.
PSE_DA_ZONA = {"A0": (1, 3), "A1": (2, 4), "A2": (5, 7), "A3": (8, 10), "AN": (10, 10)}

# O que cada nível pode receber. Pré-condicionamento ainda não sustenta ~12 min
# de nado contínuo leve: nada de A3/AN, e A2 só como toque curto.
ZONAS_DO_NIVEL = {
    "verde": {"A0", "A1", "A2", "AA"},
    "amarelo": {"A0", "A1", "A2", "A3", "AA"},
    "vermelho": {"A0", "A1", "A2", "A3", "AN", "AA"},
}
PREDOMINANTES_DO_NIVEL = {
    "verde": {"A1"},
    "amarelo": {"A1", "A2", "A3"},
    "vermelho": {"A1", "A2", "A3", "AN"},
}
# Intervalo fechado (@) só para quem controla o próprio ritmo.
INTERVALOS_DO_NIVEL = {"verde": "#", "amarelo": "#", "vermelho": "#@"}

# Referência de volume da zona predominante, em % do treino (A1 até ~50%,
# A2 ~40%, A3 ~30%, AN ~10-15%). Referência, não soma: a faixa dá folga.
FAIXA_PREDOMINANTE = {"A1": (35, 55), "A2": (30, 45), "A3": (20, 33), "AN": (8, 16)}
# Zona que não é a do dia não pode virar uma segunda predominância.
TETO_A1_SECUNDARIO = 50
TETO_A2_VERDE = 15

# Onde cada zona pode aparecer. AA só na PREPARAÇÃO: velocidade com o sistema
# nervoso descansado, antes do desenvolvimento.
ZONAS_DO_BLOCO = {
    "ativacao": {"A0", "A1"},
    "preparacao": {"A0", "A1", "AA"},
    "desenvolvimento": {"A0", "A1", "A2", "A3", "AN"},
    "consolidacao": {"A0", "A1", "A2", "A3"},
    "recuperacao": {"A0"},
}

# Ritmo de referência (segundos por 100 m em A1) de quem está em cada nível, e
# o quanto cada zona acelera ou freia. Serve para estimar duração e conferir se
# a pausa do A3 respeita esforço:pausa -- não é prescrição de ritmo individual.
RITMO_A1 = {"verde": 180, "amarelo": 140, "vermelho": 110}
FATOR_DA_ZONA = {"A0": 1.12, "A1": 1.0, "A2": 0.92, "A3": 0.85, "AN": 0.80, "AA": 0.70}
FATOR_CORRETIVO = 1.25
TRANSICAO_S = 30
# Faixa plausível de duração de uma aula em cada nível; o domingo de Recuperação
# é curto de propósito, por isso o piso é baixo.
DURACAO_MIN = {"verde": (25, 55), "amarelo": (30, 70), "vermelho": (35, 80)}

MAX_SERIES = 11
MAX_CONTINUO_VERDE = 300

FOCO_DO_DIA = ("Técnica", "Resistência", "Velocidade", "Estilos", "Ritmo",
               "Força específica", "Recuperação")
MESOCICLOS = ("Base", "Construção", "Pico", "Regeneração")
FOCOS_COM_CORRETIVO = {"Técnica", "Estilos"}

_REPS = re.compile(r"^(\d+)\s*x\s*(\d+)\s*m\b", re.I)
_SIMPLES = re.compile(r"^(\d+)\s*m\b", re.I)
_INTERVALO = re.compile(r"""^([#@])\s*(?:(\d+)')?\s*(?:(\d+)")?$""")
_PSE = re.compile(r"^(\d+)(?:\s*[-–]\s*(\d+))?$")
_SEGUNDOS = re.compile(r"(\d+)\s*(?:[-–a]\s*(\d+))?\s*s\b")


# ------------------------------------------------------------------ leitura

def carregar() -> dict:
    return json.loads(ARQUIVO.read_text(encoding="utf-8"))


def ancora(dados: dict | None = None) -> date:
    return date.fromisoformat((dados or carregar())["ancora"])


def treino_de(dados: dict, quando: date) -> dict:
    lista = dados["treinos"]
    return lista[(quando - date.fromisoformat(dados["ancora"])).days % len(lista)]


def repeticoes(serie: dict) -> tuple[int, int]:
    """(repetições, metros de cada uma)."""
    cab = serie["serie"]
    if m := _REPS.match(cab):
        return int(m.group(1)), int(m.group(2))
    if m := _SIMPLES.match(cab):
        return 1, int(m.group(1))
    raise ValueError(f"série sem distância legível no cabeçalho: {cab!r}")


def metros_da_serie(serie: dict) -> int:
    n, d = repeticoes(serie)
    return n * d


def intervalo(serie: dict) -> tuple[str, int] | None:
    """("#" ou "@", segundos) ou None."""
    txt = serie.get("intervalo")
    if not txt:
        return None
    m = _INTERVALO.match(txt.strip())
    if not m or not (m.group(2) or m.group(3)):
        raise ValueError(f"intervalo ilegível: {txt!r} (use #20\" ou @1'45\")")
    return m.group(1), int(m.group(2) or 0) * 60 + int(m.group(3) or 0)


def series_do_nivel(nivel: dict):
    for b in BLOCOS:
        for s in nivel["blocos"].get(b, []):
            yield b, s


def total_do_nivel(nivel: dict) -> int:
    return sum(metros_da_serie(s) for _, s in series_do_nivel(nivel))


def metros_do_bloco(nivel: dict, bloco: str) -> int:
    return sum(metros_da_serie(s) for s in nivel["blocos"].get(bloco, []))


def metros_por_zona(nivel: dict) -> dict:
    out = {z: 0 for z in ZONAS}
    for _, s in series_do_nivel(nivel):
        out[s["zona"]] += metros_da_serie(s)
    return out


def esforco_s(serie: dict, chave: str) -> float:
    """Tempo estimado de UMA repetição para quem está no nível."""
    _, dist = repeticoes(serie)
    ritmo = RITMO_A1[chave] * FATOR_DA_ZONA[serie["zona"]]
    if serie.get("corretivo"):
        ritmo *= FATOR_CORRETIVO
    return dist / 100 * ritmo


def minutos(nivel: dict, chave: str) -> int:
    seg = 0.0
    for _, s in series_do_nivel(nivel):
        n, _ = repeticoes(s)
        e = esforco_s(s, chave)
        iv = intervalo(s)
        if iv and iv[0] == "@":
            seg += n * max(iv[1], e)
        else:
            seg += n * e + (n - 1) * (iv[1] if iv else 0)
        seg += TRANSICAO_S
    return round(seg / 60)


def pct_predominante(nivel: dict) -> int:
    tot = total_do_nivel(nivel)
    return round(100 * metros_por_zona(nivel)[nivel["zona"]] / tot) if tot else 0


# ---------------------------------------------------------------- auditoria

def _auditar_serie(rot: str, chave: str, bloco: str, s: dict, problemas: list) -> None:
    cab = s.get("serie", "?")
    onde = f"{rot} {NOME_DO_BLOCO[bloco]} '{cab}'"

    try:
        n, dist = repeticoes(s)
    except ValueError as e:
        problemas.append(f"{onde}: {e}")
        return

    zona = s.get("zona")
    if zona not in ZONAS:
        problemas.append(f"{onde}: zona {zona!r} inválida (use {', '.join(ZONAS)}).")
        return
    if zona not in ZONAS_DO_NIVEL[chave]:
        problemas.append(f"{onde}: {zona} não é para o nível {chave}.")
    if zona not in ZONAS_DO_BLOCO[bloco]:
        problemas.append(f"{onde}: {zona} não cabe em {NOME_DO_BLOCO[bloco]}.")

    # PSE coerente com a zona -- sem isso, "A2" vira só um nome ao lado da série.
    pse = str(s.get("pse", "")).strip()
    if zona == "AA":
        if pse.lower() != "máx":
            problemas.append(f"{onde}: AA leva PSE \"máx\".")
    else:
        m = _PSE.match(pse)
        if not m:
            problemas.append(f"{onde}: PSE {pse!r} ilegível (use \"3-4\").")
        else:
            lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
            zlo, zhi = PSE_DA_ZONA[zona]
            if not (zlo <= lo <= hi <= zhi):
                problemas.append(f"{onde}: PSE {pse} fora da faixa de {zona} ({zlo}-{zhi}).")

    try:
        iv = intervalo(s)
    except ValueError as e:
        problemas.append(f"{onde}: {e}")
        iv = None
    if n > 1 and not iv:
        problemas.append(f"{onde}: série com repetições precisa de intervalo (# ou @).")
    if n == 1 and iv:
        problemas.append(f"{onde}: nado contínuo não leva intervalo.")
    if iv and iv[0] not in INTERVALOS_DO_NIVEL[chave]:
        problemas.append(f"{onde}: intervalo fechado (@) só no nível vermelho; use #.")

    esf = esforco_s(s, chave)
    pausa = None
    if iv:
        pausa = iv[1] if iv[0] == "#" else iv[1] - esf
        if iv[0] == "@" and pausa < 10:
            problemas.append(f"{onde}: saída a cada {s['intervalo']} deixa ~{max(0, round(pausa))} s "
                             f"de pausa para quem nada nesse nível; alongue a saída.")

    if dist % 25 and zona != "AA":
        problemas.append(f"{onde}: repetição de {dist}m não fecha na piscina de 25 m.")
    if chave == "verde" and n == 1 and dist > MAX_CONTINUO_VERDE:
        problemas.append(f"{onde}: {dist}m contínuos é demais para pré-condicionamento "
                         f"(até {MAX_CONTINUO_VERDE}m).")

    detalhes = " ".join(s.get("detalhes", [])).lower()
    if re.search(r"\bforte\b|\btiro\b", f"{cab} {detalhes}".lower()):
        problemas.append(f"{onde}: \"forte\"/\"tiro\" sem definição; a zona e a PSE dizem a intensidade.")

    if zona == "A1" and pausa is not None and pausa > 30:
        problemas.append(f"{onde}: A1 pede pausa curta (até 30 s).")
    if zona == "A2" and pausa is not None and not (10 <= pausa <= 60):
        problemas.append(f"{onde}: A2 pede pausa moderada (10-60 s), não {round(pausa)} s.")
    if zona == "A2" and chave == "verde" and dist > 100:
        problemas.append(f"{onde}: no pré-condicionamento o A2 é toque curto (até 100m por repetição).")

    if zona == "A3":
        limite = 50 if chave == "amarelo" else 100
        if dist > limite:
            problemas.append(f"{onde}: A3 em repetições curtas (até {limite}m neste nível).")
        if n < 3:
            problemas.append(f"{onde}: A3 é intervalado; use pelo menos 3 repetições.")
        if pausa is not None and not (0.8 * esf <= pausa <= 3 * esf):
            problemas.append(f"{onde}: pausa de {round(pausa)} s fora da relação esforço:pausa "
                             f"~1:1-1:2 (esforço estimado {round(esf)} s).")

    if zona == "AN":
        if dist > 50:
            problemas.append(f"{onde}: AN em repetições de até 50m.")
        if pausa is not None and pausa < 120:
            problemas.append(f"{onde}: AN pede recuperação grande (2 min ou mais).")

    if zona == "AA":
        if dist > 25:
            problemas.append(f"{onde}: AA é esforço curto (até 25m).")
        secs = [int(g2 or g1) for g1, g2 in _SEGUNDOS.findall(detalhes)]
        if not secs or max(secs) > 10:
            problemas.append(f"{onde}: AA é prescrito por duração; diga nos detalhes o esforço "
                             f"em segundos (até 10 s, ex.: \"acelerar 6-8 s\").")
        if pausa is not None and pausa < 45:
            problemas.append(f"{onde}: AA precisa de recuperação ampla (45 s ou mais).")

    cor = s.get("corretivo")
    if cor is not None:
        faltam = [k for k in ("nome", "objetivo", "dica") if not str(cor.get(k, "")).strip()]
        if faltam:
            problemas.append(f"{onde}: corretivo sem {', '.join(faltam)}.")
        if bloco not in ("preparacao", "consolidacao"):
            problemas.append(f"{onde}: corretivo entra na PREPARAÇÃO ou na CONSOLIDAÇÃO.")
        if zona not in ("A0", "A1"):
            problemas.append(f"{onde}: corretivo é trabalho técnico (A0/A1), não {zona}.")
        if "completo" not in detalhes:
            problemas.append(f"{onde}: corretivo tem de voltar ao nado completo "
                             f"(ex.: \"25m nado completo\").")


def _auditar_nivel(rot: str, chave: str, t: dict, problemas: list) -> None:
    nivel = t["niveis"].get(chave)
    if not nivel:
        problemas.append(f"{rot}: falta o nível {chave}.")
        return
    rot = f"{rot}/{chave}"

    for campo in ("objetivo", "zona", "ajuste"):
        if not str(nivel.get(campo, "")).strip():
            problemas.append(f"{rot}: falta \"{campo}\".")
    blocos = nivel.get("blocos", {})
    for b in blocos:
        if b not in BLOCOS:
            problemas.append(f"{rot}: bloco desconhecido {b!r}.")
    for b in OBRIGATORIOS:
        if not blocos.get(b):
            problemas.append(f"{rot}: {NOME_DO_BLOCO[b]} vazio.")

    series = list(series_do_nivel(nivel))
    if len(series) > MAX_SERIES:
        problemas.append(f"{rot}: {len(series)} séries não se leem num slide (até {MAX_SERIES}).")
    for b, s in series:
        _auditar_serie(rot, chave, b, s, problemas)

    try:
        tot = total_do_nivel(nivel)
        zonas = metros_por_zona(nivel)
        dur = minutos(nivel, chave)
    except (ValueError, KeyError):
        return  # já relatado série a série

    pred = nivel.get("zona")
    if pred not in PREDOMINANTES_DO_NIVEL[chave]:
        problemas.append(f"{rot}: zona predominante {pred!r} não serve para o nível {chave}.")
    elif tot:
        pct = round(100 * zonas[pred] / tot)
        lo, hi = FAIXA_PREDOMINANTE[pred]
        if not (lo <= pct <= hi):
            problemas.append(f"{rot}: {pred} é {pct}% do treino; a referência quando {pred} "
                             f"predomina é {lo}-{hi}%.")
        for z in ("A2", "A3", "AN"):
            if z != pred and zonas[z] >= zonas[pred]:
                problemas.append(f"{rot}: {z} ({zonas[z]}m) virou segunda predominância "
                                 f"ao lado de {pred} ({zonas[pred]}m).")
        if pred != "A1" and 100 * zonas["A1"] / tot > TETO_A1_SECUNDARIO:
            problemas.append(f"{rot}: A1 passa de {TETO_A1_SECUNDARIO}% num dia de {pred}.")
        if chave == "verde" and 100 * zonas["A2"] / tot > TETO_A2_VERDE:
            problemas.append(f"{rot}: A2 passa de {TETO_A2_VERDE}% no pré-condicionamento.")
    if zonas["AA"] > 200:
        problemas.append(f"{rot}: {zonas['AA']}m de AA; velocidade neuromuscular é volume baixo (até 200m).")
    if zonas["AN"] and t.get("mesociclo") != "Pico":
        problemas.append(f"{rot}: AN só na semana de Pico.")

    lo, hi = DURACAO_MIN[chave]
    if not (lo <= dur <= hi):
        problemas.append(f"{rot}: duração estimada {dur} min fora de {lo}-{hi} min do nível.")

    if t.get("foco") in FOCOS_COM_CORRETIVO and not any(s.get("corretivo") for _, s in series):
        problemas.append(f"{rot}: dia de {t['foco']} sem corretivo.")


def validar(dados: dict) -> list:
    """Lista de problemas. Vazia = programa coerente com o método."""
    problemas = []
    treinos = dados["treinos"]

    if len(treinos) % 7:
        problemas.append(f"O ciclo tem {len(treinos)} dias; precisa ser múltiplo de 7.")
    # A âncora pode cair em qualquer dia: com o ciclo múltiplo de 7, cada foco
    # fica preso sempre ao mesmo dia da semana (o dia da âncora é o da Técnica).
    date.fromisoformat(dados["ancora"])

    for i, t in enumerate(treinos):
        rot = f"dia {t.get('dia')}"
        if t.get("dia") != i + 1:
            problemas.append(f"{rot}: fora de ordem (esperado dia {i + 1}).")
        if t.get("foco") != FOCO_DO_DIA[i % 7]:
            problemas.append(f"{rot}: foco {t.get('foco')!r}; o dia {i % 7 + 1} da semana é "
                             f"{FOCO_DO_DIA[i % 7]}.")
        if t.get("mesociclo") != MESOCICLOS[(i // 7) % len(MESOCICLOS)]:
            problemas.append(f"{rot}: mesociclo {t.get('mesociclo')!r}; semana {i // 7 + 1} é "
                             f"{MESOCICLOS[(i // 7) % len(MESOCICLOS)]}.")
        for chave in NIVEIS:
            _auditar_nivel(rot, chave, t, problemas)

    if problemas:
        return problemas  # as regras de semana dependem de treinos legíveis

    for chave in NIVEIS:
        # Microciclo: sessão forte seguida de sessão restauradora (48-72 h).
        for i, t in enumerate(treinos):
            prox = treinos[(i + 1) % len(treinos)]
            if t["niveis"][chave]["zona"] in FORTES and prox["niveis"][chave]["zona"] in FORTES:
                problemas.append(f"dia {t['dia']}/{chave}: dois dias fortes seguidos "
                                 f"({t['niveis'][chave]['zona']} e {prox['niveis'][chave]['zona']}).")
        # Domingo de recuperação é o menor treino da semana.
        for ini in range(0, len(treinos), 7):
            semana = treinos[ini:ini + 7]
            totais = [total_do_nivel(t["niveis"][chave]) for t in semana]
            if totais[6] > min(totais[:6]):
                problemas.append(f"semana {ini // 7 + 1}/{chave}: a Recuperação ({totais[6]}m) "
                                 f"não é o menor treino da semana.")
        # Regeneração tira carga do Pico, dia a dia.
        if len(treinos) >= 28:
            for d in range(7):
                pico = total_do_nivel(treinos[14 + d]["niveis"][chave])
                regen = total_do_nivel(treinos[21 + d]["niveis"][chave])
                if regen >= pico:
                    problemas.append(f"dia {22 + d}/{chave}: Regeneração ({regen}m) não reduz "
                                     f"o Pico ({pico}m).")
    return problemas


if __name__ == "__main__":
    import sys
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass

    dados = carregar()
    erros = validar(dados)
    if not erros:
        for t in dados["treinos"]:
            partes = []
            for chave in NIVEIS:
                n = t["niveis"][chave]
                partes.append(f"{total_do_nivel(n):>4}m {n['zona']} {pct_predominante(n):>2}% "
                              f"{minutos(n, chave):>2}min")
            print(f"  dia {t['dia']:2d} {t['mesociclo']:11s} {t['foco']:16s} " + " | ".join(partes))
    if erros:
        print(f"{len(erros)} problema(s):")
        for e in erros:
            print(f"  - {e}")
        sys.exit(1)
    print(f"\nOK: {len(dados['treinos'])} dias, {len(dados['treinos']) * 3} treinos no Método NC.")
