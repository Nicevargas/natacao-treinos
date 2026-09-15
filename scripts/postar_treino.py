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

import cartao_nc     # noqa: E402
import gerar_card    # noqa: E402
import programa_nc   # noqa: E402
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

# Frase fixa da legenda, usada para reconhecer um post nosso no meio do feed.
# Se ela mudar em montar_legenda(), tem que mudar aqui junto.
ASSINATURA = "Cada Dia, 1 Treino não queremos apenas somar metros"

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


# Legenda do Método NC (desde 15/09/2026). A frase de ASSINATURA e a linha
# "Dia, dd/mm" continuam na legenda: é por elas que publicado_na_conta() acha o
# nosso carrossel no feed.
SOBRE_O_FOCO_NC = {
    "Técnica": "Hoje o ganho é de percepção: os corretivos da Preparação voltam ao nado completo no Desenvolvimento.",
    "Resistência": "Ritmo moderado que daria para sustentar por 20 a 30 minutos. Constância vale mais que velocidade.",
    "Velocidade": "Acelerações curtas com o corpo descansado, antes da série principal. Qualidade máxima e pausa generosa.",
    "Estilos": "Costas, peito e borboleta com corretivos. Nadar o que você não gosta costuma destravar o que você gosta.",
    "Ritmo": "Passagem negativa: começar controlado e terminar mais rápido. É assim que se aprende a dosar o esforço.",
    "Força específica": "Palmar, pull buoy e nadadeira ensinam sensação. O que importa é o que muda quando você tira o material.",
    "Recuperação": "Dia leve de propósito. Recuperação faz parte do treino: pular este dia atrapalha a semana seguinte.",
}

SOBRE_O_MESOCICLO = {
    "Base": "Semana 1 do ciclo: Base, construindo o alicerce.",
    "Construção": "Semana 2 do ciclo: Construção, o volume sobe um pouco.",
    "Pico": "Semana 3 do ciclo: Pico, a semana mais intensa das quatro.",
    "Regeneração": "Semana 4 do ciclo: Regeneração, menos volume para absorver o que foi feito.",
}


def montar_legenda_nc(t: dict, dados: dict, quando: date) -> str:
    rot = dados["rotulos"]
    dia_semana = gerar_card.DIAS_SEMANA[quando.weekday()]
    # Mesmo objetivo nos três níveis (dia de técnica, por exemplo) sai uma vez só.
    objetivos = [t["niveis"][n]["objetivo"] for n in programa_nc.NIVEIS]
    um_so = len(set(objetivos)) == 1
    niveis = "\n".join(
        f"{rot[n]['emoji']} {rot[n]['nome']}: {t['niveis'][n]['zona']} · "
        f"{programa_nc.total_do_nivel(t['niveis'][n])}m · "
        f"~{programa_nc.minutos(t['niveis'][n], n)} min"
        + ("" if um_so else f"\n🎯 {t['niveis'][n]['objetivo']}")
        for n in programa_nc.NIVEIS)
    if um_so:
        niveis += f"\n\n🎯 Objetivo do dia: {objetivos[0]}"

    return (
        f"🏊 Qual é o seu nível hoje?\n\n"
        f"{dia_semana}, {quando.strftime('%d/%m')} — foco em {t['foco']}. "
        f"{SOBRE_O_FOCO_NC.get(t['foco'], '')}\n\n"
        f"No Cada Dia, 1 Treino não queremos apenas somar metros. Cada bloco tem um "
        f"propósito: Ativação → Preparação → Desenvolvimento → Consolidação → Recuperação.\n\n"
        f"Escolha seu nível:\n{niveis}\n\n"
        f"📌 Como ler: A0 a A3, AN e AA são as zonas de intensidade; PSE é o esforço de 0 a 10; "
        f"#20\" é descanso de 20 s e @ é saída com tempo fixo.\n\n"
        f"{SOBRE_O_MESOCICLO.get(t['mesociclo'], '')}\n\n"
        f"⚠️ Sentiu dor, tontura ou falta de ar incomum? Pare o treino.\n\n"
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

    Procura o NOSSO carrossel, não qualquer post do dia. A conta publica reels
    e outros conteúdos todos os dias; a primeira versão disto só comparava a
    data e por isso deu falso positivo em 30/08, casando com um reel e fazendo
    as duas execuções agendadas saírem sem publicar, relatando sucesso.

    A identificação usa duas marcas juntas: a frase fixa da nossa legenda e a
    linha de dia/data daquele dia específico. Uma só não bastaria -- a frase se
    repete todo dia, e a data aparece em qualquer post da mesma data.

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
        # Limite folgado: a conta chega a publicar 4 vezes por dia, então 10
        # itens podem não alcançar o carrossel da manhã.
        r = requests.get(f"{base}/{versao}/me/media",
                         params={"fields": "id,timestamp,permalink,caption",
                                 "limit": 30, "access_token": token},
                         timeout=30)
        itens = r.json().get("data") or []
    except Exception as e:
        print(f"  (não deu para consultar o feed: {type(e).__name__}; "
              f"seguindo pelo registro local)")
        return None

    marca_do_dia = f"{gerar_card.DIAS_SEMANA[quando.weekday()]}, {quando:%d/%m}"

    for item in itens:
        legenda = item.get("caption") or ""
        if ASSINATURA not in legenda or marca_do_dia not in legenda:
            continue
        return item.get("permalink") or item.get("id")
    return None


def anotar(quando: date, t: dict, arquivos: list) -> None:
    REGISTRO.parent.mkdir(exist_ok=True)
    dados = json.loads(REGISTRO.read_text(encoding="utf-8")) if REGISTRO.exists() else {}
    dados[quando.isoformat()] = {
        "dia_do_ciclo": t["dia"], "bloco": t.get("mesociclo", t.get("bloco")), "foco": t["foco"],
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
    # Até 14/09/2026 saiu treinos.json; da âncora de programa_nc.json (15/09) em
    # diante, o Método NC. A troca acontece sozinha, pela data.
    dados, e_nc = cartao_nc.programa_da_data(quando)
    programa = programa_nc if e_nc else treino

    # Programa quebrado não pode virar post. Barrar aqui é mais barato do que
    # descobrir pelo feed.
    if erros := programa.validar(dados):
        print("O programa de treinos está inválido; nada foi publicado:")
        for e in erros:
            print(f"  - {e}")
        return 1

    t = programa.treino_de(dados, quando)

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

    totais = " / ".join(f"{programa.total_do_nivel(t['niveis'][n])}m"
                        for n in gerar_card.ORDEM_NIVEIS)
    print(f"Treino de {quando.isoformat()} — dia {t['dia']}/{len(dados['treinos'])}, "
          f"{t.get('mesociclo', t.get('bloco'))} / {t['foco']}, {totais}"
          f"{' (Método NC)' if e_nc else ''}")

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        slides = gerar_card.gerar(quando, dados, nav)
        nav.close()

    legenda = montar_legenda_nc(t, dados, quando) if e_nc else montar_legenda(t, dados, quando)
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
