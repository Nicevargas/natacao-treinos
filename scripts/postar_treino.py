"""
postar_treino.py - Gera o carrossel do dia, monta a legenda e publica.

Ponto de entrada único da automação. Roda igual no notebook e no runner do
GitHub Actions; muda só de onde vem o token (arquivo .env aqui, segredo do
repositório lá).

Uso:
    python scripts/postar_treino.py --dry-run     # mostra tudo, não publica
    python scripts/postar_treino.py               # publica de verdade
    python scripts/postar_treino.py --data 2026-09-05
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gerar_card    # noqa: E402
import treino        # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

RAIZ = Path(__file__).resolve().parent.parent
REGISTRO = RAIZ / "publicadas" / "registro.json"

# O Brasil não tem mais horário de verão desde 2019, então o deslocamento é
# fixo. Fuso explícito, e não o do sistema: o runner do GitHub roda em UTC.
BRASILIA = timezone(timedelta(hours=-3))


# ------------------------------------------------------------------ legenda

# Uma frase por foco. São 7 focos x 4 blocos = 28 combinações, então o ciclo
# inteiro sai sem repetir legenda -- texto idêntico todo dia é sinal de spam
# para o Instagram.
SOBRE_O_FOCO = {
    "Técnica": "Hoje o ganho não é de fôlego, é de percepção. Nadar devagar prestando atenção rende mais do que nadar rápido no automático.",
    "Aeróbico": "Ritmo constante do início ao fim. É esse tipo de treino, sem brilho nenhum, que constrói o fundo que aparece nos outros dias.",
    "Velocidade": "Tiro curto e descanso longo. Se o intervalo parecer generoso, é porque o esforço tem que ser de verdade máximo.",
    "Estilos": "Os quatro nados no mesmo treino. Nadar o que você não gosta costuma ser o que destrava o que você gosta.",
    "Volume": "O treino mais longo da semana. O objetivo não é velocidade: é chegar no fim com a técnica inteira.",
    "Material": "Nadadeira, palmar e pull buoy entram para ensinar sensação, não para facilitar. O que importa é o que muda quando você tira.",
    "Regenerativo": "Dia leve de propósito. Recuperação faz parte do treino — pular esse dia é o que atrapalha a semana seguinte.",
}

SOBRE_O_BLOCO = {
    "Base": "Semana 1 do ciclo — bloco de Base, construindo o alicerce.",
    "Construção": "Semana 2 do ciclo — bloco de Construção, o volume sobe.",
    "Pico": "Semana 3 do ciclo — bloco de Pico, a semana mais dura das quatro.",
    "Regeneração": "Semana 4 do ciclo — bloco de Regeneração, absorver o que foi feito.",
}

TAGS = ("#NatacaoCriativa #CadaDia1Treino #TreinoDeNatacao #Natacao "
        "#SwimmingWorkout #Nadar #Piscina #Swim #NatacaoMaster #AguasAbertas")


def montar_legenda(t: dict, dados: dict, quando: date) -> str:
    rot = dados["rotulos"]
    tot = {n: treino.total_do_nivel(t["niveis"][n]) for n in gerar_card.ORDEM_NIVEIS}
    dia_semana = gerar_card.DIAS_SEMANA[quando.weekday()]

    escolhas = "\n".join(
        f"{rot[n]['emoji']} {tot[n]}m | {rot[n]['nome']}"
        for n in gerar_card.ORDEM_NIVEIS)

    return (
        f"🏊 {tot['verde']}m, {tot['amarelo']}m ou {tot['vermelho']}m: "
        f"qual é o seu treino de hoje?\n\n"
        f"{dia_semana}, {quando.strftime('%d/%m')} — foco em {t['foco']}. "
        f"{SOBRE_O_FOCO.get(t['foco'], '')}\n\n"
        f"No Cada Dia, 1 Treino não queremos apenas somar metros. "
        f"Cada exercício tem um propósito.\n\n"
        f"Escolha seu desafio:\n{escolhas}\n\n"
        f"Os três são treinos diferentes, não o mesmo treino esticado: "
        f"para subir de nível entra exercício novo, não mais metragem no mesmo "
        f"exercício. O {rot['vermelho']['emoji']} é o único que traz EDUCATIVOS.\n\n"
        f"{SOBRE_O_BLOCO.get(t['bloco'], '')}\n\n"
        f"💡 Metragem é quantidade. Treinamento precisa ter propósito.\n\n"
        f"🔥 Fez o treino? Marca {dados['handle']} e conta:\n"
        f"Intensidade: 0 a 10\n"
        f"Complexidade: 0 a 10\n\n"
        f"👇 Sua percepção nos comentários ajuda a montar os próximos.\n\n"
        f"{TAGS}"
    )


# ----------------------------------------------------------------- registro

def ja_publicado(quando: date):
    """Registro local do que já saiu. Sobrevive entre runs do Actions porque é
    commitado -- o runner em si é máquina descartável.

    Não serve sozinho como trava: ele só é gravado DEPOIS de publicar, então um
    push que falhe deixa o dia publicado sem registro. Quem fecha esse buraco é
    publicado_na_conta(), abaixo."""
    if not REGISTRO.exists():
        return None
    return json.loads(REGISTRO.read_text(encoding="utf-8")).get(quando.isoformat())


def publicado_na_conta(quando: date) -> str | None:
    """Pergunta à própria conta se já há publicação com a data pedida.

    Esta é a trava que vale. Com três tentativas de cron por dia, confiar só no
    arquivo commitado é frágil: basta o push do registro falhar para a tentativa
    seguinte republicar o mesmo carrossel. O feed é a fonte de verdade e não
    depende do git ter dado certo.

    Falha de rede aqui devolve None (segue para o registro local) em vez de
    abortar: barrar a publicação por causa de uma consulta instável seria pior
    que o risco que ela cobre.
    """
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    if not token:
        return None

    base = os.getenv("INSTAGRAM_API_BASE", "https://graph.instagram.com")
    versao = os.getenv("META_API_VERSION", "v23.0")
    try:
        r = requests.get(f"{base}/{versao}/me/media",
                         params={"fields": "id,timestamp,permalink",
                                 "limit": 10, "access_token": token},
                         timeout=30)
        itens = r.json().get("data") or []
    except Exception as e:
        print(f"  (não deu para consultar o feed: {type(e).__name__}; "
              f"seguindo pelo registro local)")
        return None

    for item in itens:
        carimbo = item.get("timestamp", "")
        try:
            # A Meta devolve com fuso; converter para Brasília antes de comparar,
            # senão um post das 21h vira o dia seguinte.
            quando_saiu = datetime.fromisoformat(carimbo).astimezone(BRASILIA).date()
        except ValueError:
            continue
        if quando_saiu == quando:
            return item.get("permalink") or item.get("id")
    return None


def anotar(quando: date, t: dict, arquivos: list) -> None:
    REGISTRO.parent.mkdir(exist_ok=True)
    dados = json.loads(REGISTRO.read_text(encoding="utf-8")) if REGISTRO.exists() else {}
    dados[quando.isoformat()] = {
        "dia_do_ciclo": t["dia"], "bloco": t["bloco"], "foco": t["foco"],
        "slides": [a.name for a in arquivos],
    }
    REGISTRO.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")


# -------------------------------------------------------------------- fluxo

def main() -> int:
    ap = argparse.ArgumentParser(description="Publica o carrossel do treino do dia.")
    ap.add_argument("--data", help="AAAA-MM-DD (padrão: hoje)")
    ap.add_argument("--dry-run", action="store_true", help="Mostra tudo sem publicar.")
    ap.add_argument("--forcar", action="store_true",
                    help="Publica mesmo se o dia já constar no registro.")
    args = ap.parse_args()

    quando = date.fromisoformat(args.data) if args.data else date.today()
    dados = treino.carregar()

    # Programa quebrado não pode virar post. Barrar aqui é mais barato do que
    # descobrir pelo feed.
    if erros := treino.validar(dados):
        print("O programa de treinos está inválido; nada foi publicado:")
        for e in erros:
            print(f"  - {e}")
        return 1

    t = treino.treino_de(dados, quando)

    if not args.forcar and not args.dry_run:
        # A conta primeiro: é a fonte de verdade e não depende de o git ter
        # conseguido gravar o registro.
        if onde := publicado_na_conta(quando):
            print(f"A conta já tem publicação de {quando.isoformat()}: {onde}. "
                  f"Nada a fazer.")
            return 0
        if anterior := ja_publicado(quando):
            print(f"O treino de {quando.isoformat()} já consta no registro "
                  f"(dia {anterior['dia_do_ciclo']} do ciclo). Nada a fazer.")
            return 0

    totais = " / ".join(f"{treino.total_do_nivel(t['niveis'][n])}m"
                        for n in gerar_card.ORDEM_NIVEIS)
    print(f"Treino de {quando.isoformat()} — dia {t['dia']}/{len(dados['treinos'])}, "
          f"{t['bloco']} / {t['foco']}, {totais}")

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        slides = gerar_card.gerar(quando, dados, nav)
        nav.close()

    legenda = montar_legenda(t, dados, quando)
    print(f"\nLegenda ({len(legenda)} caracteres):\n{'-'*60}\n{legenda}\n{'-'*60}\n")

    cmd = [sys.executable, str(RAIZ / "scripts" / "publish_instagram.py"),
           "--images", *[str(s) for s in slides], "--caption", legenda]
    if args.dry_run:
        cmd.append("--dry-run")

    if (r := subprocess.run(cmd, cwd=str(RAIZ))).returncode != 0:
        print("\nA publicação falhou. O registro não foi tocado.")
        return r.returncode

    if not args.dry_run:
        anotar(quando, t, slides)
        print(f"\nRegistrado em {REGISTRO.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
