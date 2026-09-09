#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Queima a legenda no video.

A legenda vai gravada na imagem (e nao como faixa separada) porque nas
redes sociais a faixa some: Instagram, TikTok e WhatsApp descartam
legenda embutida e mostram so o video.

Uso:
    python3 legendar.py --video entrada/v.mp4 --legenda legendas/v.ass \
        --saida saida/v_legendado.mp4
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import estilo_legenda


def resolucao(caminho):
    saida = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height", "-of", "csv=p=0:s=x", caminho],
        check=True, capture_output=True).stdout.decode().strip().split("x")
    return int(saida[0]), int(saida[1])


def queima(video, legenda, saida, perfil="padrao", crf=18, preset="medium"):
    """Regrava o video com a legenda desenhada por cima.

    O filtro `ass` respeita PlayResX/PlayResY do arquivo, entao o corpo da
    letra sai exatamente com os pixels calculados no estilo.
    """
    os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
    caminho = legenda.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    cmd = ["ffmpeg", "-y", "-i", video, "-vf", "ass='%s'" % caminho,
           "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart",
           "-c:a", "aac", "-b:a", "192k", saida]
    subprocess.run(cmd, check=True, capture_output=True)
    return saida


def main():
    p = argparse.ArgumentParser(description="Queima a legenda no video")
    p.add_argument("--video", required=True)
    p.add_argument("--legenda", required=True, help="arquivo .ass")
    p.add_argument("--saida", required=True)
    p.add_argument("--perfil", default="padrao", choices=sorted(estilo_legenda.PERFIS))
    p.add_argument("--crf", type=int, default=18, help="menor = melhor qualidade")
    args = p.parse_args()

    largura, altura = resolucao(args.video)
    m = estilo_legenda.medidas(largura, altura, args.perfil)
    print("Legendando %dx%d | %s %dpx | margem inferior %dpx"
          % (largura, altura, m["fonte"], m["corpo"], m["margem_v"]))
    saida = queima(args.video, args.legenda, args.saida, args.perfil, args.crf)
    tamanho = os.path.getsize(saida) / 1e6
    print("Pronto: %s (%.1f MB)" % (saida, tamanho))


if __name__ == "__main__":
    main()
