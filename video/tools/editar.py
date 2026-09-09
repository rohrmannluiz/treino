#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Edicoes do video, antes de legendar.

A ordem importa: cortar depois de legendar desencontra a legenda da fala.
Entao todo corte acontece aqui, e so o resultado final vai para o
alinhamento.

Subcomandos:
    cortar     trecho por tempo (mantem ou remove)
    silencios  tira as pausas longas entre as frases
    audio      normaliza o volume no padrao das redes sociais
    formato    ajusta o enquadramento (9:16, 1:1, 16:9)
    capa       salva um quadro como imagem
"""

import argparse
import os
import re
import subprocess
import sys


def roda(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, **kw)


def duracao(caminho):
    return float(roda(["ffprobe", "-v", "error", "-show_entries",
                       "format=duration", "-of", "csv=p=0",
                       caminho]).stdout.decode().strip())


def prepara(saida):
    os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
    return saida


def _tempo(txt):
    """Aceita 12.5, 1:05 ou 00:01:05.4."""
    partes = str(txt).split(":")
    segundos = 0.0
    for p in partes:
        segundos = segundos * 60 + float(p)
    return segundos


def cortar(args):
    """Recorta por tempo. Sempre recodifica: cortar copiando so acerta em
    quadro-chave, e o corte cai longe de onde foi pedido."""
    ini, fim = _tempo(args.de), _tempo(args.ate)
    if args.remover:
        # Tira o miolo: junta o que vem antes com o que vem depois.
        total = duracao(args.video)
        filtro = (
            "[0:v]trim=0:%f,setpts=PTS-STARTPTS[v0];"
            "[0:a]atrim=0:%f,asetpts=PTS-STARTPTS[a0];"
            "[0:v]trim=%f:%f,setpts=PTS-STARTPTS[v1];"
            "[0:a]atrim=%f:%f,asetpts=PTS-STARTPTS[a1];"
            "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]"
            % (ini, ini, fim, total, fim, total))
        cmd = ["ffmpeg", "-y", "-i", args.video, "-filter_complex", filtro,
               "-map", "[v]", "-map", "[a]"]
    else:
        cmd = ["ffmpeg", "-y", "-ss", str(ini), "-to", str(fim), "-i", args.video]
    cmd += ["-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            prepara(args.saida)]
    roda(cmd)
    print("Corte pronto: %s (%.2fs)" % (args.saida, duracao(args.saida)))


def detecta_silencios(video, limiar_db=-32, minimo=0.6):
    """Lista os silencios do video usando o silencedetect do ffmpeg."""
    saida = subprocess.run(
        ["ffmpeg", "-i", video, "-af",
         "silencedetect=noise=%ddB:d=%s" % (limiar_db, minimo), "-f", "null", "-"],
        capture_output=True).stderr.decode()
    inicios = [float(m) for m in re.findall(r"silence_start: (-?[\d.]+)", saida)]
    fins = [float(m) for m in re.findall(r"silence_end: (-?[\d.]+)", saida)]
    return list(zip(inicios, fins))


def silencios(args):
    """Encurta as pausas longas, sem colar as frases umas nas outras.

    Cada pausa e reduzida ao tamanho de folga (nao eliminada): corte seco
    entre frases soa afobado e atrapalha a leitura da legenda.
    """
    total = duracao(args.video)
    pausas = detecta_silencios(args.video, args.limiar, args.minimo)
    manter, cursor = [], 0.0
    for ini, fim in pausas:
        fim = min(fim, total)
        if fim - ini < args.minimo:
            continue
        corte_ini = ini + args.folga / 2
        corte_fim = max(corte_ini, fim - args.folga / 2)
        if corte_fim - corte_ini < 0.05:
            continue
        manter.append((cursor, corte_ini))
        cursor = corte_fim
    manter.append((cursor, total))
    manter = [(a, b) for a, b in manter if b - a > 0.05]

    if len(manter) <= 1:
        print("Nenhuma pausa longa encontrada; nada a cortar.")
        return

    partes = []
    for i, (a, b) in enumerate(manter):
        partes.append("[0:v]trim=%f:%f,setpts=PTS-STARTPTS[v%d];"
                      "[0:a]atrim=%f:%f,asetpts=PTS-STARTPTS[a%d];"
                      % (a, b, i, a, b, i))
    fluxos = "".join("[v%d][a%d]" % (i, i) for i in range(len(manter)))
    filtro = "".join(partes) + "%sconcat=n=%d:v=1:a=1[v][a]" % (fluxos, len(manter))
    roda(["ffmpeg", "-y", "-i", args.video, "-filter_complex", filtro,
          "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "18",
          "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac",
          "-b:a", "192k", prepara(args.saida)])
    nova = duracao(args.saida)
    print("Pausas encurtadas: %d cortes | %.2fs -> %.2fs (%.1fs a menos)"
          % (len(manter) - 1, total, nova, total - nova))


def mede_loudness(video, alvo, pico, faixa):
    """Primeira passagem: mede o volume real do arquivo."""
    import json
    saida = subprocess.run(
        ["ffmpeg", "-i", video, "-af",
         "loudnorm=I=%s:TP=%s:LRA=%s:print_format=json" % (alvo, pico, faixa),
         "-f", "null", "-"], capture_output=True).stderr.decode()
    bloco = saida[saida.rfind("{"):saida.rfind("}") + 1]
    return json.loads(bloco)


def audio(args):
    """Normaliza o volume pelo padrao EBU R128, em duas passagens.

    -14 LUFS e o alvo que Instagram, YouTube e TikTok usam para nivelar o
    som: entregando ja nesse nivel, a plataforma nao mexe mais no audio.

    Uma passagem so nao acerta o alvo (erra de 2 a 3 dB), porque o filtro
    trabalha adivinhando o volume conforme escuta. Medindo antes e passando
    o resultado na segunda rodada, a correcao vira uma conta fechada.
    """
    alvo, pico, faixa = args.alvo, -1.5, 11
    m = mede_loudness(args.video, alvo, pico, faixa)
    filtro = ("loudnorm=I=%s:TP=%s:LRA=%s:measured_I=%s:measured_TP=%s:"
              "measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true:print_format=summary"
              % (alvo, pico, faixa, m["input_i"], m["input_tp"],
                 m["input_lra"], m["input_thresh"], m["target_offset"]))
    roda(["ffmpeg", "-y", "-i", args.video, "-af", filtro, "-c:v", "copy",
          "-c:a", "aac", "-b:a", "192k", prepara(args.saida)])
    print("Audio normalizado: %s LUFS -> %s LUFS (%s)"
          % (m["input_i"], alvo, args.saida))

    # O pico manda: se levantar o volume ate o alvo fizer a onda estourar,
    # o filtro para antes. Vale avisar, senao parece que nao funcionou.
    ganho_pedido = alvo - float(m["input_i"])
    ganho_possivel = pico - float(m["input_tp"])
    if ganho_pedido > ganho_possivel + 0.5:
        print("  Aviso: o alvo pedia %+.1f dB, mas o pico do arquivo so "
              "permite %+.1f dB sem estourar." % (ganho_pedido, ganho_possivel))
        print("  A gravacao esta com picos altos e volume medio baixo. "
              "Grave mais perto do microfone e com ganho menor.")


FORMATOS = {"9:16": (1080, 1920), "1:1": (1080, 1080), "16:9": (1920, 1080),
            "4:5": (1080, 1350)}


def formato(args):
    """Reenquadra cortando o excedente, sem distorcer nem deixar tarja."""
    largura, altura = FORMATOS[args.para]
    filtro = ("scale=%d:%d:force_original_aspect_ratio=increase,"
              "crop=%d:%d" % (largura, altura, largura, altura))
    roda(["ffmpeg", "-y", "-i", args.video, "-vf", filtro,
          "-c:v", "libx264", "-crf", "18", "-preset", "medium",
          "-pix_fmt", "yuv420p", "-c:a", "copy", prepara(args.saida)])
    print("Reenquadrado para %s (%dx%d): %s" % (args.para, largura, altura, args.saida))


def capa(args):
    roda(["ffmpeg", "-y", "-ss", str(_tempo(args.em)), "-i", args.video,
          "-frames:v", "1", "-q:v", "2", prepara(args.saida)])
    print("Capa salva: %s" % args.saida)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("cortar", help="recorta por tempo")
    c.add_argument("--video", required=True); c.add_argument("--saida", required=True)
    c.add_argument("--de", required=True, help="ex: 3.5 ou 0:03.5")
    c.add_argument("--ate", required=True)
    c.add_argument("--remover", action="store_true",
                   help="remove esse trecho em vez de mante-lo")
    c.set_defaults(func=cortar)

    s = sub.add_parser("silencios", help="encurta as pausas longas")
    s.add_argument("--video", required=True); s.add_argument("--saida", required=True)
    s.add_argument("--minimo", type=float, default=0.7, help="pausa alvo, em segundos")
    s.add_argument("--folga", type=float, default=0.35,
                   help="quanto de silencio preservar em cada pausa")
    s.add_argument("--limiar", type=int, default=-32, help="dB abaixo do qual e silencio")
    s.set_defaults(func=silencios)

    a = sub.add_parser("audio", help="normaliza o volume")
    a.add_argument("--video", required=True); a.add_argument("--saida", required=True)
    a.add_argument("--alvo", type=float, default=-14.0, help="LUFS de destino")
    a.set_defaults(func=audio)

    f = sub.add_parser("formato", help="reenquadra")
    f.add_argument("--video", required=True); f.add_argument("--saida", required=True)
    f.add_argument("--para", default="9:16", choices=sorted(FORMATOS))
    f.set_defaults(func=formato)

    k = sub.add_parser("capa", help="salva um quadro")
    k.add_argument("--video", required=True); k.add_argument("--saida", required=True)
    k.add_argument("--em", default="1.0")
    k.set_defaults(func=capa)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
