"""
renovar_token.py - Renova o token de longa duração do Instagram.

O token vale 60 dias. Sem renovar, a publicação diária simplesmente para de
funcionar em dois meses e o único sinal é o feed parado -- por isso isto roda
sozinho toda semana, muito antes do vencimento.

A rota `Instagram API with Instagram Login` renova pelo endpoint
`refresh_access_token`. O token precisa ter mais de 24h de vida para ser aceito.

Imprime SOMENTE o token novo em stdout, para o workflow poder capturar:
    NOVO=$(python scripts/renovar_token.py)
Qualquer diagnóstico vai para stderr.
"""
import os
import sys

import requests

BASE = os.getenv("INSTAGRAM_API_BASE", "https://graph.instagram.com")


def main() -> int:
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    if not token:
        print("INSTAGRAM_ACCESS_TOKEN não está definido.", file=sys.stderr)
        return 1

    r = requests.get(f"{BASE}/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": token},
                     timeout=30)
    dados = r.json()

    if "access_token" not in dados:
        print(f"A renovação falhou: {dados}", file=sys.stderr)
        return 1

    dias = int(dados.get("expires_in", 0)) // 86400
    print(f"Token renovado; vale por mais {dias} dias.", file=sys.stderr)

    if dias < 30:
        print("ATENÇÃO: validade curta demais. Confira o app no Meta for "
              "Developers.", file=sys.stderr)

    print(dados["access_token"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
