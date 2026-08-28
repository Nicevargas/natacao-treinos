"""
treino.py - Leitura, cálculo e validação do programa de treinos.

A metragem NÃO é escrita à mão em lugar nenhum: ela sai das séries. Com 84
treinos, um total digitado à mão diverge das séries mais cedo ou mais tarde, e
o erro só apareceria depois de publicado.

Uma série é:
    {"serie": "8x50m Crawl", "detalhes": ["25m forte", "25m leve"], "intervalo": "20\\""}

O cabeçalho carrega a distância ("8x50m" = 400m). Os detalhes descrevem o que
fazer dentro da série e NÃO somam -- são a repartição do que já foi contado.
"""
import json
import re
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO = RAIZ / "treinos.json"

BLOCOS = ("aquecimento", "principal", "final")
NIVEIS = ("verde", "amarelo", "vermelho")

# Faixa de metragem aceitável por nível. O post de referência da conta trabalha
# em 1.200 / 2.000 / 3.500; sair muito disso descaracteriza o nível -- um
# "menor volume" de 1.800m não é menor volume, e um 🔴 de 5.000m vira outra coisa.
FAIXAS = {"verde": (900, 1700), "amarelo": (1700, 2700), "vermelho": (2500, 4100)}

# Total quebrado (2.650m) denuncia série montada no olho e fica feio no card.
PASSO = 100

_REPS = re.compile(r"^(\d+)\s*x\s*(\d+)\s*m\b", re.I)
_SIMPLES = re.compile(r"^(\d+)\s*m\b", re.I)


def metros_da_serie(serie: dict) -> int:
    cab = serie["serie"]
    if m := _REPS.match(cab):
        return int(m.group(1)) * int(m.group(2))
    if m := _SIMPLES.match(cab):
        return int(m.group(1))
    raise ValueError(f"Série sem distância legível no cabeçalho: {cab!r}")


def metros_do_bloco(series: list) -> int:
    return sum(metros_da_serie(s) for s in series)


def total_do_nivel(nivel: dict) -> int:
    return sum(metros_do_bloco(nivel[b]) for b in BLOCOS)


def carregar() -> dict:
    return json.loads(ARQUIVO.read_text(encoding="utf-8"))


def treino_de(dados: dict, quando: date) -> dict:
    ancora = date.fromisoformat(dados["ancora"])
    lista = dados["treinos"]
    return lista[(quando - ancora).days % len(lista)]


# --------------------------------------------------------------- validação

def validar(dados: dict) -> list:
    """Devolve a lista de problemas encontrados. Vazia = programa saudável."""
    problemas = []
    treinos = dados["treinos"]

    if len(treinos) % 7 != 0:
        problemas.append(f"O ciclo tem {len(treinos)} dias; precisa ser múltiplo de 7 "
                         f"para travar cada posição num dia da semana fixo.")

    ancora = date.fromisoformat(dados["ancora"])
    if ancora.weekday() != 0:
        problemas.append(f"A âncora {ancora} cai numa {ancora.strftime('%A')}; "
                         f"precisa ser segunda-feira ou o padrão semanal desalinha.")

    vistos = set()
    for t in treinos:
        rot = f"dia {t['dia']}"
        if t["dia"] in vistos:
            problemas.append(f"{rot}: número de dia repetido.")
        vistos.add(t["dia"])

        totais = {}
        for nome in NIVEIS:
            if nome not in t["niveis"]:
                problemas.append(f"{rot}: falta o nível {nome}.")
                continue
            nivel = t["niveis"][nome]
            for b in BLOCOS:
                if not nivel.get(b):
                    problemas.append(f"{rot}/{nome}: bloco '{b}' vazio.")
            try:
                tot = totais[nome] = total_do_nivel(nivel)
            except ValueError as e:
                problemas.append(f"{rot}/{nome}: {e}")
                continue

            piso, teto = FAIXAS[nome]
            if not (piso <= tot <= teto):
                problemas.append(f"{rot}/{nome}: {tot}m fora da faixa "
                                 f"{piso}-{teto}m do nível.")
            if tot % PASSO:
                problemas.append(f"{rot}/{nome}: {tot}m não fecha em múltiplo "
                                 f"de {PASSO}m.")

        # Volume tem que crescer do verde para o vermelho.
        ordem = [totais.get(n) for n in NIVEIS]
        if all(v is not None for v in ordem) and not (ordem[0] < ordem[1] < ordem[2]):
            problemas.append(f"{rot}: totais fora de ordem crescente: {ordem}.")

        # A regra da conta: subir de nível é ACRESCENTAR exercício, nunca esticar
        # um que já existe. Cabeçalho repetido entre níveis denuncia as duas
        # coisas -- ou repetição pura, ou o mesmo exercício inflado.
        cabecas = {}
        for nome in NIVEIS:
            if nome not in t["niveis"]:
                continue
            for b in BLOCOS:
                for s in t["niveis"][nome].get(b, []):
                    chave = s["serie"].strip().lower()
                    if chave in cabecas and cabecas[chave] != nome:
                        problemas.append(
                            f"{rot}: '{s['serie']}' aparece em {cabecas[chave]} "
                            f"e em {nome}; os níveis não devem repetir exercício.")
                    cabecas[chave] = nome

    return problemas


if __name__ == "__main__":
    import sys
    dados = carregar()
    erros = validar(dados)

    for t in dados["treinos"]:
        tot = [total_do_nivel(t["niveis"][n]) for n in NIVEIS if n in t["niveis"]]
        print(f"  dia {t['dia']:2d}/{len(dados['treinos'])}  {t['bloco']:12s} "
              f"{t['foco']:13s} {' / '.join(f'{v}m' for v in tot)}")

    if erros:
        print(f"\n{len(erros)} problema(s):")
        for e in erros:
            print(f"  - {e}")
        sys.exit(1)
    print(f"\nOK: {len(dados['treinos'])} dias, {len(dados['treinos'])*3} treinos.")
