"""
programa_aa.py - Programa "Cada Dia 1 Treino" no modo ÁGUAS ABERTAS do Método NC.

Treinos que preparam para mar, lago e travessias: sighting, respiração
adaptável, ritmo sem depender da parede, mudanças de ritmo como numa boia ou
largada, passagem negativa e força específica de braço.

Cada treino tem SETE partes, as da arte "1 Treino por dia · Águas abertas"
(cartao_aa.py), sempre nesta ordem:

    respiracao      Respiração         (LE, LD, bilateral)
    corretivos      Corretivos
    ativacao        Ativação
    pernas_braco    Pernas + braço
    desenvolvimento Desenvolvimento
    consolidacao    Consolidação
    recuperacao     Recuperação

Só Condicionamento (amarelo) e Aperfeiçoamento (vermelho): águas abertas pedem
nado contínuo leve estável, que o Pré-condicionamento ainda está construindo.

Série, PSE, pausas e zonas seguem as regras de programa_nc.py: cada parte é
auditada como o bloco do método a que corresponde (PARTE_NO_METODO). Aqui se
somam as regras do modo:

  - a semana segue as famílias de águas abertas, no mesmo dia da semana do
    programa de piscina (a âncora é a mesma);
  - todo treino declara a habilidade de águas abertas do dia e traz pelo menos
    uma tarefa específica (sighting, respiração, virada sem impulsão, boia...);
  - sem apneia nem submerso: não são pilar de preparação para águas abertas.

Uso:
    python scripts/programa_aa.py        # resumo dos 28 dias + auditoria
"""
import json
import re
from datetime import date
from pathlib import Path

import programa_nc as nc

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO = RAIZ / "programa_aa.json"

NIVEIS = ("amarelo", "vermelho")
PARTES = ("respiracao", "corretivos", "ativacao", "pernas_braco",
          "desenvolvimento", "consolidacao", "recuperacao")
NOME_DA_PARTE = {
    "respiracao": "Respiração",
    "corretivos": "Corretivos",
    "ativacao": "Ativação",
    "pernas_braco": "Pernas + braço",
    "desenvolvimento": "Desenvolvimento",
    "consolidacao": "Consolidação",
    "recuperacao": "Recuperação",
}
# Bloco do Método NC em que cada parte é auditada (zonas permitidas, onde entra corretivo).
PARTE_NO_METODO = {
    "respiracao": "ativacao",
    "corretivos": "preparacao",
    "ativacao": "preparacao",
    "pernas_braco": "consolidacao",
    "desenvolvimento": "desenvolvimento",
    "consolidacao": "consolidacao",
    "recuperacao": "recuperacao",
}

FOCO_DO_DIA = ("Navegação", "Ritmo de prova", "Mudança de ritmo", "Base contínua",
               "Progressão", "Força específica", "Recuperação")

# A arte tem uma faixa estreita por parte: poucas séries em cada uma.
MAX_SERIES_DA_PARTE = 2

_ESPECIFICO = re.compile(
    r"sighting|olhar à frente|boia|largada|grupo|sem impulsão|sem parede|\bLE\b|\bLD\b|"
    r"bilateral|lado da respiração|passagem negativa|contínuo", re.I)
_PROIBIDO = re.compile(r"apneia|submers", re.I)

treino_de = nc.treino_de


def carregar() -> dict:
    return json.loads(ARQUIVO.read_text(encoding="utf-8"))


def ancora(dados: dict | None = None) -> date:
    return date.fromisoformat((dados or carregar())["ancora"])


# ------------------------------------------------------------ contas do nível

def series_do_nivel(nivel: dict):
    for p in PARTES:
        for s in nivel["partes"].get(p, []):
            yield p, s


def total_do_nivel(nivel: dict) -> int:
    return sum(nc.metros_da_serie(s) for _, s in series_do_nivel(nivel))


def metros_da_parte(nivel: dict, parte: str) -> int:
    return sum(nc.metros_da_serie(s) for s in nivel["partes"].get(parte, []))


def metros_por_zona(nivel: dict) -> dict:
    out = {z: 0 for z in nc.ZONAS}
    for _, s in series_do_nivel(nivel):
        out[s["zona"]] += nc.metros_da_serie(s)
    return out


def minutos(nivel: dict, chave: str) -> int:
    seg = 0.0
    for _, s in series_do_nivel(nivel):
        n, _ = nc.repeticoes(s)
        e = nc.esforco_s(s, chave)
        iv = nc.intervalo(s)
        if iv and iv[0] == "@":
            seg += n * max(iv[1], e)
        else:
            seg += n * e + (n - 1) * (iv[1] if iv else 0)
        seg += nc.TRANSICAO_S
    return round(seg / 60)


def pct_predominante(nivel: dict) -> int:
    tot = total_do_nivel(nivel)
    return round(100 * metros_por_zona(nivel)[nivel["zona"]] / tot) if tot else 0


# ------------------------------------------------------------------ auditoria

def _texto(nivel: dict) -> str:
    return " ".join(
        " ".join([s["serie"], *s.get("detalhes", []),
                  *(s["corretivo"].values() if s.get("corretivo") else [])])
        for _, s in series_do_nivel(nivel))


def _auditar_nivel(rot: str, chave: str, t: dict, problemas: list) -> None:
    nivel = t["niveis"].get(chave)
    if not nivel:
        problemas.append(f"{rot}: falta o nível {chave}.")
        return
    rot = f"{rot}/{chave}"

    for campo in ("objetivo", "zona", "ajuste"):
        if not str(nivel.get(campo, "")).strip():
            problemas.append(f"{rot}: falta \"{campo}\".")
    partes = nivel.get("partes", {})
    for p in partes:
        if p not in PARTES:
            problemas.append(f"{rot}: parte desconhecida {p!r}.")
    for p in PARTES:
        if not partes.get(p):
            problemas.append(f"{rot}: {NOME_DA_PARTE[p]} vazia; a arte tem as sete partes.")
        elif len(partes[p]) > MAX_SERIES_DA_PARTE:
            problemas.append(f"{rot}: {NOME_DA_PARTE[p]} com {len(partes[p])} séries não cabe na faixa "
                             f"(até {MAX_SERIES_DA_PARTE}).")

    for p, s in series_do_nivel(nivel):
        antes = len(problemas)
        nc._auditar_serie(rot, chave, PARTE_NO_METODO[p], s, problemas)
        # A mensagem sai com o nome do bloco do método; troca pelo nome da parte.
        bloco = nc.NOME_DO_BLOCO[PARTE_NO_METODO[p]]
        for i in range(antes, len(problemas)):
            problemas[i] = problemas[i].replace(f" {bloco} '", f" {NOME_DA_PARTE[p].upper()} '")

    try:
        tot = total_do_nivel(nivel)
        zonas = metros_por_zona(nivel)
        dur = minutos(nivel, chave)
    except (ValueError, KeyError):
        return

    pred = nivel.get("zona")
    if pred not in nc.PREDOMINANTES_DO_NIVEL[chave]:
        problemas.append(f"{rot}: zona predominante {pred!r} não serve para o nível {chave}.")
    elif tot:
        pct = round(100 * zonas[pred] / tot)
        lo, hi = nc.FAIXA_PREDOMINANTE[pred]
        if not (lo <= pct <= hi):
            problemas.append(f"{rot}: {pred} é {pct}% do treino; a referência quando {pred} "
                             f"predomina é {lo}-{hi}%.")
        for z in ("A2", "A3", "AN"):
            if z != pred and zonas[z] >= zonas[pred]:
                problemas.append(f"{rot}: {z} ({zonas[z]}m) virou segunda predominância ao lado de {pred}.")
        if pred != "A1" and 100 * zonas["A1"] / tot > nc.TETO_A1_SECUNDARIO:
            problemas.append(f"{rot}: A1 passa de {nc.TETO_A1_SECUNDARIO}% num dia de {pred}.")
    if zonas["AA"] > 200:
        problemas.append(f"{rot}: {zonas['AA']}m de AA; velocidade é volume baixo (até 200m).")
    if zonas["AN"]:
        problemas.append(f"{rot}: AN fica fora da preparação para águas abertas.")

    lo, hi = nc.DURACAO_MIN[chave]
    if not (lo <= dur <= hi):
        problemas.append(f"{rot}: duração estimada {dur} min fora de {lo}-{hi} min do nível.")

    if not any(s.get("corretivo") for s in partes.get("corretivos", [])):
        problemas.append(f"{rot}: a parte Corretivos precisa de um corretivo.")
    texto = _texto(nivel)
    if not _ESPECIFICO.search(texto):
        problemas.append(f"{rot}: nenhuma tarefa específica de águas abertas.")
    if _PROIBIDO.search(texto):
        problemas.append(f"{rot}: apneia/submerso não entra na preparação para águas abertas.")


def validar(dados: dict) -> list:
    """Lista de problemas. Vazia = programa coerente com o método."""
    problemas = []
    treinos = dados["treinos"]

    if len(treinos) % 7:
        problemas.append(f"O ciclo tem {len(treinos)} dias; precisa ser múltiplo de 7.")
    date.fromisoformat(dados["ancora"])
    if not str(dados.get("seguranca", "")).strip():
        problemas.append("Falta o aviso de segurança do modo (\"seguranca\").")

    for i, t in enumerate(treinos):
        rot = f"dia {t.get('dia')}"
        if t.get("dia") != i + 1:
            problemas.append(f"{rot}: fora de ordem (esperado dia {i + 1}).")
        if t.get("foco") != FOCO_DO_DIA[i % 7]:
            problemas.append(f"{rot}: foco {t.get('foco')!r}; o dia {i % 7 + 1} da semana é "
                             f"{FOCO_DO_DIA[i % 7]}.")
        if t.get("mesociclo") != nc.MESOCICLOS[(i // 7) % len(nc.MESOCICLOS)]:
            problemas.append(f"{rot}: mesociclo {t.get('mesociclo')!r}.")
        if not str(t.get("habilidade", "")).strip():
            problemas.append(f"{rot}: falta a habilidade de águas abertas do dia.")
        extras = set(t.get("niveis", {})) - set(NIVEIS)
        if extras:
            problemas.append(f"{rot}: águas abertas é só para {', '.join(NIVEIS)}; sobrou {sorted(extras)}.")
        for chave in NIVEIS:
            _auditar_nivel(rot, chave, t, problemas)

    if problemas:
        return problemas

    for chave in NIVEIS:
        for i, t in enumerate(treinos):
            prox = treinos[(i + 1) % len(treinos)]
            if t["niveis"][chave]["zona"] in nc.FORTES and prox["niveis"][chave]["zona"] in nc.FORTES:
                problemas.append(f"dia {t['dia']}/{chave}: dois dias fortes seguidos.")
        for ini in range(0, len(treinos), 7):
            semana = treinos[ini:ini + 7]
            totais = [total_do_nivel(t["niveis"][chave]) for t in semana]
            if totais[6] >= min(totais[:6]):
                problemas.append(f"semana {ini // 7 + 1}/{chave}: a Recuperação ({totais[6]}m) "
                                 f"não é o menor treino da semana.")
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
            print(f"  dia {t['dia']:2d} {t['mesociclo']:11s} {t['foco']:17s} " + " | ".join(partes))
    if erros:
        print(f"{len(erros)} problema(s):")
        for e in erros:
            print(f"  - {e}")
        sys.exit(1)
    print(f"\nOK: {len(dados['treinos'])} dias, {len(dados['treinos']) * len(NIVEIS)} treinos de águas abertas.")
