#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Confere se o roteiro cabe no tempo antes de gravar.

Estima a duracao contando silabas, nao palavras: "a" e "imediatamente"
contam igual por palavra, mas nao na boca do locutor. A referencia e 5,2
silabas por segundo, que e leitura de teleprompter em pt-BR sem correria
(a fala espontanea fica entre 5,8 e 6,2).

Uso:
    python3 roteiro.py roteiros/pix.txt [--limite 90] [--cues]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import legenda_texto as lt

VELOCIDADES = {          # silabas por segundo
    "pausado": 4.6,
    "normal": 5.2,
    "acelerado": 5.8,
}


def main():
    p = argparse.ArgumentParser(description="Confere a duracao do roteiro")
    p.add_argument("arquivo")
    p.add_argument("--limite", type=float, default=90.0, help="segundos")
    p.add_argument("--cues", action="store_true", help="mostra os blocos de legenda")
    p.add_argument("--cpl", type=int, default=38)
    args = p.parse_args()

    texto = lt.limpa_para_locucao(open(args.arquivo, encoding="utf-8").read())
    frases = lt.divide_em_frases(texto)
    palavras = lt.conta_palavras(texto)
    silabas = lt.conta_silabas(texto)

    print("Roteiro: %s" % args.arquivo)
    print("%d palavras | %d silabas | %d frases | %.1f palavras por frase"
          % (palavras, silabas, len(frases), palavras / max(1, len(frases))))
    print()
    for nome, sps in VELOCIDADES.items():
        d = lt.estima_duracao(texto, sps)
        marca = "  <-- ritmo de referencia" if nome == "normal" else ""
        aviso = "  ESTOURA" if d > args.limite else ""
        print("  ritmo %-10s %5.1fs%s%s" % (nome, d, aviso, marca))

    d = lt.estima_duracao(texto)
    print()
    if d > args.limite:
        sobra = d - args.limite
        cortar = int(sobra * 5.2 / 1.6)     # ~1,6 silabas por palavra em pt-BR
        print("Passou %.1fs do limite de %.0fs. Cortar cerca de %d palavras."
              % (sobra, args.limite, cortar))
    else:
        print("Cabe em %.0fs, com %.1fs de folga." % (args.limite, args.limite - d))

    longas = [f for f in frases if lt.conta_palavras(f) > 28]
    if longas:
        print("\nFrases longas demais para ler de uma vez (mais de 28 palavras):")
        for f in longas:
            print("  - %s..." % f[:70])

    if args.cues:
        cues = lt.monta_cues(texto, cpl=args.cpl)
        print("\n%d blocos de legenda:" % len(cues))
        for i, c in enumerate(cues, 1):
            print("%3d | %s" % (i, "\n    | ".join(c["linhas"])))


if __name__ == "__main__":
    main()
