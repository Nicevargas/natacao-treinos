"""
preparar_logo.py - Transforma um logo de fundo branco nos dois PNG que o card usa.

    marca/logo.png    logo inteiro, recortado e com fundo transparente
    marca/splat.png   só o respingo colorido, quadrado, para o rodapé

Existe porque o logo chega em versões diferentes (print de tela, export, webp) e
sempre com fundo branco chapado. Refazer isso na mão a cada versão nova é onde
mora o erro.

Uso:
    python scripts/preparar_logo.py "C:/caminho/logo.webp"
"""
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
MARCA = RAIZ / "marca"

LIMIAR_CLARO = 232   # acima disto o pixel conta como fundo branco
LIMIAR_SOLIDO = 40   # alfa mínimo para o pixel valer no recorte


def fundo_conectado(rgb: np.ndarray) -> np.ndarray:
    """Marca o branco que se alcança a partir da borda.

    Um "todo pixel branco vira transparente" abriria buraco em qualquer branco
    interno do desenho. Alagar a partir da moldura só remove o que de fato é
    fundo.
    """
    h, w, _ = rgb.shape
    claro = rgb.min(axis=2) > LIMIAR_CLARO
    fora = np.zeros((h, w), bool)
    fila = deque()

    def semear(y, x):
        if claro[y, x] and not fora[y, x]:
            fora[y, x] = True
            fila.append((y, x))

    for x in range(w):
        semear(0, x); semear(h - 1, x)
    for y in range(h):
        semear(y, 0); semear(y, w - 1)

    while fila:
        y, x = fila.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w:
                semear(ny, nx)
    return fora


def recortar(origem: Path) -> Image.Image:
    src = Image.open(origem).convert("RGB")
    rgb = np.asarray(src).astype(np.int16)
    fora = fundo_conectado(rgb)

    # Na borda do desenho o pixel é uma mistura com o branco. Derivar o alfa da
    # distância ao branco, em vez de cortar seco, evita a franja clara que um
    # recorte duro deixa em volta das letras.
    dist = 255 - rgb.min(axis=2)
    alfa = np.clip(dist.astype(float) * 2.4, 0, 255)
    alfa[fora] = 0
    alfa[(~fora) & (dist > 40)] = 255

    im = Image.fromarray(np.dstack([np.asarray(src), alfa.astype(np.uint8)]), "RGBA")
    return im.crop(_caixa(im))


def _caixa(im: Image.Image):
    return im.split()[3].point(lambda v: 255 if v > LIMIAR_SOLIDO else 0).getbbox()


def separar_splat(logo: Image.Image) -> Image.Image:
    """O rodapé usa só o respingo, sem o letreiro.

    O corte sai do maior vão de colunas totalmente vazias -- é o espaço entre o
    respingo e a palavra. Cravar uma porcentagem quebraria assim que o logo
    viesse com outra proporção.
    """
    op = (np.asarray(logo.split()[3]) > LIMIAR_SOLIDO).sum(axis=0)
    vazias = np.where(op == 0)[0]
    if len(vazias) == 0:
        raise SystemExit("Não achei separação entre o respingo e o letreiro.")

    melhor_ini = melhor_fim = ini = vazias[0]
    for i in range(1, len(vazias)):
        if vazias[i] != vazias[i - 1] + 1:
            if vazias[i - 1] - ini > melhor_fim - melhor_ini:
                melhor_ini, melhor_fim = ini, vazias[i - 1]
            ini = vazias[i]
    if vazias[-1] - ini > melhor_fim - melhor_ini:
        melhor_ini, melhor_fim = ini, vazias[-1]

    splat = logo.crop((0, 0, int(melhor_ini) + 1, logo.height))
    splat = splat.crop(_caixa(splat))

    lado = max(splat.size) + max(splat.size) // 14      # respiro em volta
    quadro = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    quadro.paste(splat, ((lado - splat.width) // 2, (lado - splat.height) // 2), splat)
    return quadro


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    origem = Path(sys.argv[1])
    if not origem.exists():
        raise SystemExit(f"Arquivo não encontrado: {origem}")

    MARCA.mkdir(exist_ok=True)
    logo = recortar(origem)
    splat = separar_splat(logo)

    logo.save(MARCA / "logo.png")
    splat.save(MARCA / "splat.png")

    print(f"  origem      {Image.open(origem).size}")
    print(f"  logo.png    {logo.size}")
    print(f"  splat.png   {splat.size}")
    if logo.width < 300:
        print(f"\n  AVISO: o card exibe o logo a 300px e esta origem só tem "
              f"{logo.width}px úteis.\n  Vai sair macio. Um export maior resolve.")


if __name__ == "__main__":
    main()
