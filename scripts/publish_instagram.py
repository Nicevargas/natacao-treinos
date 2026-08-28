"""
publish_instagram.py - Publicacao automatica no Instagram
Conta: @natacaocriativa
Rota: Instagram API with Instagram Login (graph.instagram.com)

Adaptado do pipeline da @nicevargas.mkt. A unica diferenca real e que a
hospedagem das imagens vem do .env, em vez de estar fixa no codigo -- assim
as duas contas usam o mesmo script sem se misturar.

Uso:
    python publish_instagram.py --images foto.jpg --caption "legenda"
    python publish_instagram.py --images "slides/*.jpg" --caption "legenda"
    python publish_instagram.py --images a.jpg b.jpg --caption "legenda" --dry-run
"""
import argparse
import glob as globlib
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# O console do Windows usa cp1252 e quebra ao imprimir emoji da legenda.
# A legenda em si vai para a API em UTF-8 -- isto afeta so o que aparece na tela.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

# ---------------------------------------------------------------- credenciais

SCRIPT_DIR = Path(__file__).resolve().parent
ENV_FILE = None
for candidate in [SCRIPT_DIR / ".env", *(p / ".env" for p in SCRIPT_DIR.parents)]:
    if candidate.exists():
        ENV_FILE = candidate
        load_dotenv(candidate)
        break

TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
# Opcional de proposito. Nesta rota nenhuma chamada usa este ID -- todas vao
# por /me -- entao exigi-lo so criava mais um segredo para manter sem ganho
# nenhum de seguranca. Quem impede publicar na conta errada e a comparacao de
# INSTAGRAM_USERNAME logo abaixo, essa sim indispensavel.
IG_ID = os.getenv("INSTAGRAM_BUSINESS_ID")
API_BASE = os.getenv("INSTAGRAM_API_BASE", "https://graph.instagram.com")
VERSION = os.getenv("META_API_VERSION", "v23.0")
BASE_URL = f"{API_BASE}/{VERSION}"

ESPERADA = os.getenv("INSTAGRAM_USERNAME")

# Nesta rota o endpoint /me resolve a conta autenticada sem ambiguidade
# entre o ID com escopo de app e o ID de negocio.
ACCOUNT = "me"


def die(msg: str) -> None:
    print(f"\nERRO: {msg}")
    sys.exit(1)


def check_credentials() -> None:
    if not TOKEN:
        die("INSTAGRAM_ACCESS_TOKEN nao encontrado. Confira o .env "
            "(ou o segredo do repositorio, se estiver no GitHub Actions).")
    if not ESPERADA:
        die("INSTAGRAM_USERNAME nao definido. Sem ele nao ha como garantir que "
            "o token e da conta certa, e publicar na conta errada e irreversivel.")
    resp = requests.get(
        f"{BASE_URL}/{ACCOUNT}",
        params={"fields": "username", "access_token": TOKEN},
        timeout=30,
    )
    data = resp.json()
    if "username" not in data:
        die(
            "Token invalido ou expirado.\n"
            f"Resposta da API: {data}\n"
            "Gere um novo token e atualize INSTAGRAM_ACCESS_TOKEN no .env"
        )
    conta = data["username"]
    # Publicar na conta errada e irreversivel: melhor abortar do que confiar
    # que o .env carregado foi o certo.
    if ESPERADA and conta != ESPERADA:
        die(
            f"Conta inesperada. O token autentica @{conta}, "
            f"mas este projeto e da @{ESPERADA}.\n"
            "Voce provavelmente carregou o .env do outro cliente."
        )
    print(f"  Conta autenticada: @{conta}")


def chave_natural(caminho: str) -> list:
    """Ordena slide_2 antes de slide_10.

    O sorted() puro e alfabetico: com 10 ou mais slides ele poe slide_10 logo
    depois de slide_1 e o carrossel sai fora de ordem — o fecho vira o segundo
    slide. Quebrar o nome em trechos de texto e de numero resolve, e nao muda
    nada para nomes sem numero.
    """
    nome = Path(caminho).name
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", nome)]


def expand(patterns: list) -> list:
    """Expande curingas (o shell do Windows nao expande sozinho)."""
    files = []
    for pattern in patterns:
        matches = sorted(globlib.glob(pattern), key=chave_natural)
        if matches:
            files.extend(matches)
        elif Path(pattern).exists():
            files.append(pattern)
        else:
            die(f"Arquivo nao encontrado: {pattern}")
    return files


# ------------------------------------------------------------------ hospedagem

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) publish_instagram/1.0"

REPO = Path(os.getenv("GITHUB_REPO_DIR") or SCRIPT_DIR.parent).resolve()
RAW = (os.getenv("GITHUB_RAW_BASE") or "").rstrip("/")


def _up_github(path: Path):
    """
    Host principal: um repositorio publico do GitHub.

    A Meta precisa de uma URL publica que ela consiga baixar. Servir do
    raw.githubusercontent.com evita depender de host de terceiro -- que foi
    exatamente o que quebrou (catbox bloqueado na rede, 0x0.st desativado).
    """
    import shutil
    import subprocess

    if not RAW:
        return None

    destino = REPO / "publicadas"
    destino.mkdir(exist_ok=True)
    alvo = destino / path.name
    if not alvo.exists() or alvo.read_bytes() != path.read_bytes():
        shutil.copyfile(path, alvo)

    def git(*args):
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)

    git("add", "publicadas")
    if git("diff", "--cached", "--quiet").returncode != 0:      # ha algo novo
        git("commit", "-m", "Add slides for Instagram publishing")
        if git("push", "origin", "main").returncode != 0:
            return None

    url = f"{RAW}/{path.name}"
    # O raw.githubusercontent leva alguns segundos para enxergar o commit novo.
    # Uma checagem unica falha por corrida e joga a publicacao nos hosts
    # alternativos, que estao quebrados nesta rede -- entao vale insistir.
    espera = 2
    for tentativa in range(6):
        try:
            if requests.head(url, timeout=30, allow_redirects=True).status_code == 200:
                return url
        except Exception:
            pass
        if tentativa < 5:
            print(f"    aguardando o raw publicar {path.name} ({espera}s)")
            time.sleep(espera)
            espera *= 2
    return None


def _up_0x0(path: Path):
    with open(path, "rb") as fh:
        r = requests.post("https://0x0.st", files={"file": (path.name, fh)},
                          headers={"User-Agent": UA}, timeout=120)
    u = r.text.strip()
    return u if u.startswith("https://") else None


def _up_tmpfiles(path: Path):
    with open(path, "rb") as fh:
        r = requests.post("https://tmpfiles.org/api/v1/upload",
                          files={"file": (path.name, fh)},
                          headers={"User-Agent": UA}, timeout=120)
    u = (r.json().get("data") or {}).get("url", "")
    # a API devolve a pagina de visualizacao; o download direto leva /dl/
    return u.replace("tmpfiles.org/", "tmpfiles.org/dl/", 1) if u.startswith("http") else None


def _up_catbox(path: Path):
    with open(path, "rb") as fh:
        r = requests.post("https://catbox.moe/user/api.php",
                          data={"reqtype": "fileupload"},
                          files={"fileToUpload": (path.name, fh)},
                          headers={"User-Agent": UA}, timeout=120)
    u = r.text.strip()
    return u if u.startswith("https://") else None


HOSTS = [("github raw", _up_github), ("0x0.st", _up_0x0),
         ("tmpfiles.org", _up_tmpfiles), ("catbox.moe", _up_catbox)]


def host_image(image_path: str) -> str:
    """
    Hospeda a imagem numa URL publica.

    A API do Instagram nao aceita upload de arquivo local: ela exige uma URL
    publica que os servidores da Meta consigam baixar. Tenta os hosts em ordem
    -- redes diferentes bloqueiam hosts diferentes, entao vale ter alternativa.
    A imagem fica acessivel por link a quem tiver a URL.
    """
    path = Path(image_path)
    erros = []
    for nome, fn in HOSTS:
        try:
            url = fn(path)
            if url:
                print(f"  {path.name} -> {url}  [{nome}]")
                return url
            erros.append(f"{nome}: resposta invalida")
        except Exception as e:
            erros.append(f"{nome}: {type(e).__name__}")
    die("Nenhum host aceitou o upload de " + path.name + "\n  " + "\n  ".join(erros))


# -------------------------------------------------------------------- API calls

def _post_retry(url: str, payload: dict, what: str, tries: int = 5) -> dict:
    """
    A Meta devolve erros marcados 'is_transient' com alguma frequencia.
    Nesses casos a orientacao dela e repetir -- entao repetimos com espera
    crescente em vez de abortar a publicacao inteira.
    """
    espera = 4
    for tentativa in range(1, tries + 1):
        result = requests.post(url, data=payload, timeout=120).json()
        if "id" in result:
            return result
        err = result.get("error", {})
        if not err.get("is_transient") or tentativa == tries:
            die(f"Falha ao {what}: {result}")
        print(f"    erro temporario da Meta, tentativa {tentativa}/{tries} "
              f"- aguardando {espera}s")
        time.sleep(espera)
        espera *= 2
    return {}


def create_container(image_url: str, caption: str = None, carousel_item: bool = False) -> str:
    payload = {"access_token": TOKEN, "image_url": image_url}
    if carousel_item:
        payload["is_carousel_item"] = "true"
    if caption is not None:
        payload["caption"] = caption

    result = _post_retry(f"{BASE_URL}/{ACCOUNT}/media", payload, "criar container")
    print(f"  Container: {result['id']}")
    return result["id"]


def create_carousel(children: list, caption: str) -> str:
    result = _post_retry(f"{BASE_URL}/{ACCOUNT}/media", {
        "access_token": TOKEN,
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": caption,
    }, "montar carrossel")
    print(f"  Carrossel: {result['id']}")
    return result["id"]


def wait_ready(container_id: str, tries: int = 20, delay: int = 5) -> None:
    for attempt in range(tries):
        resp = requests.get(
            f"{BASE_URL}/{container_id}",
            params={"fields": "status_code,status", "access_token": TOKEN},
            timeout=30,
        )
        data = resp.json()
        status = data.get("status_code", "")
        if status == "FINISHED":
            return
        if status == "ERROR":
            die(f"Container falhou no processamento: {data}")
        print(f"  Processando... ({attempt * delay}s)")
        time.sleep(delay)
    die("Timeout: o container nao ficou pronto a tempo.")


def publish(container_id: str) -> str:
    result = _post_retry(f"{BASE_URL}/{ACCOUNT}/media_publish",
                         {"access_token": TOKEN, "creation_id": container_id},
                         "publicar")
    return result["id"]


def permalink(post_id: str) -> str:
    resp = requests.get(
        f"{BASE_URL}/{post_id}",
        params={"fields": "permalink", "access_token": TOKEN},
        timeout=30,
    )
    return resp.json().get("permalink", "(link indisponivel)")


# --------------------------------------------------------------------- fluxo

def run(patterns: list, caption: str, dry_run: bool = False) -> None:
    print(f"\n.env carregado de: {ENV_FILE}")
    check_credentials()

    images = expand(patterns)
    if len(images) > 10:
        die(f"Maximo de 10 imagens por post (recebi {len(images)}).")

    tipo = "post unico" if len(images) == 1 else f"carrossel de {len(images)} slides"
    print(f"\nModo: {tipo}")
    for img in images:
        size_kb = Path(img).stat().st_size / 1024
        print(f"  - {img} ({size_kb:.0f} KB)")
    print(f"\nLegenda ({len(caption)} caracteres):")
    print(f"  {caption[:200]}{'...' if len(caption) > 200 else ''}")

    if dry_run:
        print("\n[DRY RUN] Nada foi enviado nem publicado.")
        print("Remova --dry-run para publicar de verdade.")
        return

    print("\nPasso 1/4 - Hospedando imagens...")
    urls = [host_image(img) for img in images]

    if len(images) == 1:
        print("\nPasso 2/4 - Criando container...")
        container_id = create_container(urls[0], caption=caption)
    else:
        print("\nPasso 2/4 - Criando containers dos slides...")
        children = [create_container(u, carousel_item=True) for u in urls]
        print("\n  Montando o carrossel...")
        container_id = create_carousel(children, caption)

    print("\nPasso 3/4 - Aguardando processamento...")
    wait_ready(container_id)

    print("\nPasso 4/4 - Publicando...")
    post_id = publish(container_id)

    print("\nPublicado com sucesso!")
    print(f"  Post ID: {post_id}")
    print(f"  Link:    {permalink(post_id)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Publica imagens no Instagram (@natacaocriativa).")
    parser.add_argument("--images", nargs="+", required=True, help="Arquivos ou curingas (1 a 10).")
    parser.add_argument("--caption", required=True, help="Legenda do post.")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem enviar nada.")
    args = parser.parse_args()
    run(args.images, args.caption, args.dry_run)
