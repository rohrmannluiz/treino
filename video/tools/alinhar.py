#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Alinha o roteiro ao audio do video gravado e gera as legendas.

O video e lido no teleprompter, entao o texto ja e conhecido: o problema
nao e descobrir O QUE foi dito (reconhecimento de fala), e sim QUANDO cada
trecho foi dito. Isso e alinhamento forcado, e da resultado melhor que um
ASR porque nunca erra a palavra nem a acentuacao.

Como funciona:
  1. extrai o audio do video em 16 kHz mono e corta o silencio das pontas;
  2. sintetiza cada FRASE do roteiro com espeak-ng em pt-BR e emenda tudo
     com uma pausa curta entre elas, guardando onde cada frase comeca;
  3. compara os dois audios por MFCC + DTW, o que produz uma funcao que
     traduz "tempo no audio sintetico" em "tempo no audio real";
  4. dentro de cada frase, reparte o tempo entre as palavras conforme o
     numero de silabas, e monta os blocos de legenda a partir disso.

A sintese e feita por frase, e nao por bloco de legenda, porque o espeak
so produz entonacao natural com a frase inteira; cortada no meio, a
prosodia fica artificial e o alinhamento perde precisao.

Uso:
    python3 alinhar.py --video entrada/v.mp4 --roteiro roteiros/r.txt \
        --saida legendas/v
"""

import argparse
import os
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import legenda_texto as lt

SR = 16000          # taxa de amostragem da analise
HOP = 320           # 20 ms por frame: precisao de sobra para legenda
PAUSA_SINT = 0.30   # silencio entre frases no audio de referencia
DUR_MIN = 0.85      # guia de legendagem Netflix pt-BR: 5/6 de segundo
DUR_MAX = 7.0
INTERVALO = 0.08    # respiro entre dois blocos consecutivos
CPS_MAX = 17.0      # caracteres por segundo (limite de leitura confortavel)


def roda(cmd):
    return subprocess.run(cmd, check=True, capture_output=True)


def extrai_audio(video, destino):
    roda(["ffmpeg", "-y", "-i", video, "-vn", "-ac", "1", "-ar", str(SR),
          "-acodec", "pcm_s16le", destino])
    return destino


def carrega(caminho, aparar=False, limiar_db=35):
    """Le o audio e, se pedido, corta o silencio das pontas.

    Aparar importa: a gravacao tem o locutor se ajeitando antes e depois da
    fala, e esse silencio nao existe no audio sintetico. Com as duas faixas
    comecando e terminando na fala, o alinhamento compara coisas iguais.
    """
    import librosa
    y, _ = librosa.load(caminho, sr=SR, mono=True)
    inteiro, deslocamento = y, 0.0
    if aparar:
        aparado, faixa = librosa.effects.trim(y, top_db=limiar_db,
                                              frame_length=1024, hop_length=HOP)
        if len(aparado) > SR * 0.5:          # so confia no corte se sobrou fala
            deslocamento = faixa[0] / SR
            y = aparado
    return y, deslocamento, inteiro


def sintetiza_frases(frases, pasta, velocidade=160):
    """Gera o audio de referencia e o instante em que cada frase comeca nele."""
    import librosa
    import soundfile as sf

    silencio = np.zeros(int(PAUSA_SINT * SR), dtype=np.float32)
    partes, marcas, cursor = [], [], 0.0
    for i, frase in enumerate(frases):
        alvo = os.path.join(pasta, "frase_%03d.wav" % i)
        roda(["espeak-ng", "-v", "pt-br", "-s", str(velocidade), "-w", alvo, frase])
        audio, sr = sf.read(alvo)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        audio = np.asarray(audio, dtype=np.float32)
        if sr != SR:      # o espeak entrega 22050 Hz; sem isso o tempo sai errado
            audio = librosa.resample(audio, orig_sr=sr, target_sr=SR)
        if i:
            partes.append(silencio)
            cursor += PAUSA_SINT
        partes.append(audio)
        marcas.append([cursor, cursor + len(audio) / SR])
        cursor += len(audio) / SR

    completo = np.concatenate(partes) if partes else np.zeros(1, dtype=np.float32)
    caminho = os.path.join(pasta, "roteiro.wav")
    sf.write(caminho, completo, SR)
    return caminho, marcas


def features(y):
    """MFCC normalizado: descreve o formato do som, ignorando o timbre.

    Descartar o coeficiente 0 (energia) e normalizar por media e desvio deixa
    a comparacao entre a voz sintetica e a voz real muito mais estavel.
    """
    import librosa
    m = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=13, hop_length=HOP, n_fft=1024)
    m = m[1:]
    m = (m - m.mean(axis=1, keepdims=True)) / (m.std(axis=1, keepdims=True) + 1e-8)
    return np.vstack([m, librosa.feature.delta(m)])


def mapa_de_tempo(feat_sint, feat_real):
    """Para cada frame do audio sintetico, diz a que frame do real ele corresponde.

    As duas faixas ja comecam e terminam na fala, entao o alinhamento vai de
    ponta a ponta. Deixar o DTW livre para encaixar so um pedaco faria ele
    escolher o atalho: espremer o roteiro inteiro em poucos segundos.
    """
    import librosa
    _, wp = librosa.sequence.dtw(X=feat_sint, Y=feat_real,
                                 metric="cosine", subseq=False)
    wp = wp[::-1]                                   # do inicio para o fim
    mapa = np.full(feat_sint.shape[1], np.nan)
    for i, j in wp:
        if np.isnan(mapa[i]):
            mapa[i] = j                             # primeira ocorrencia = inicio
    validos = ~np.isnan(mapa)
    mapa = np.interp(np.arange(len(mapa)), np.flatnonzero(validos), mapa[validos])
    return np.maximum.accumulate(mapa)              # o tempo nunca anda para tras


def tempos_por_palavra(frases, tempos_frase):
    """Reparte o tempo de cada frase entre suas palavras, na conta das silabas.

    Silabas medem melhor que caracteres quanto tempo uma palavra ocupa na
    fala: "a" e "extraordinariamente" tem o mesmo peso por palavra, mas nao
    na boca do locutor.
    """
    inicios, fins = [], []
    for frase, (t0, t1) in zip(frases, tempos_frase):
        palavras = frase.split()
        silabas = [max(1, lt.conta_silabas(p)) for p in palavras]
        total = sum(silabas)
        acumulado = 0
        for s in silabas:
            inicios.append(t0 + (t1 - t0) * acumulado / total)
            acumulado += s
            fins.append(t0 + (t1 - t0) * acumulado / total)
    return inicios, fins


def ajusta_tempos(tempos, textos, duracao_video):
    """Aplica as regras de legibilidade da legenda.

    Sem sobreposicao, nunca curto demais para ler nem longo demais na tela,
    e respeitando o teto de caracteres por segundo.
    """
    ajustados = []
    for (ini, fim), texto in zip(tempos, textos):
        if ajustados and ini < ajustados[-1][1] + INTERVALO:
            ini = ajustados[-1][1] + INTERVALO
        minimo = max(DUR_MIN, len(texto) / CPS_MAX)
        fim = min(max(fim, ini + minimo), ini + DUR_MAX)
        ajustados.append([ini, fim])

    for i in range(len(ajustados) - 1, -1, -1):     # nao passar do fim do video
        if ajustados[i][1] > duracao_video:
            ajustados[i][1] = duracao_video
            if ajustados[i][0] > ajustados[i][1] - 0.3:
                ajustados[i][0] = max(0.0, ajustados[i][1] - DUR_MIN)
    return ajustados


def duracao(caminho):
    saida = roda(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                  "-of", "csv=p=0", caminho]).stdout.decode().strip()
    return float(saida)


def resolucao(caminho):
    saida = roda(["ffprobe", "-v", "error", "-select_streams", "v:0",
                  "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x",
                  caminho]).stdout.decode().strip().split("x")
    return int(saida[0]), int(saida[1])


def hhmmss(t, sep=","):
    t = max(0.0, t)
    h, resto = divmod(t, 3600)
    m, s = divmod(resto, 60)
    return "%02d:%02d:%02d%s%03d" % (h, m, int(s), sep, round(s % 1 * 1000))


def escreve_srt(cues, tempos, destino):
    with open(destino, "w", encoding="utf-8") as f:
        for i, (cue, (ini, fim)) in enumerate(zip(cues, tempos), 1):
            f.write("%d\n%s --> %s\n%s\n\n"
                    % (i, hhmmss(ini), hhmmss(fim), "\n".join(cue["linhas"])))
    return destino


def escreve_ass(cues, tempos, destino, largura, altura):
    import estilo_legenda
    with open(destino, "w", encoding="utf-8") as f:
        f.write(estilo_legenda.cabecalho(largura, altura))
        for cue, (ini, fim) in zip(cues, tempos):
            f.write("Dialogue: 0,%s,%s,Legenda,,0,0,0,,%s\n"
                    % (hhmmss(ini, ".")[:-1], hhmmss(fim, ".")[:-1],
                       "\\N".join(cue["linhas"])))
    return destino


def main():
    p = argparse.ArgumentParser(description="Alinha roteiro e video, gera legendas")
    p.add_argument("--video", required=True)
    p.add_argument("--roteiro", required=True)
    p.add_argument("--saida", required=True, help="caminho base, sem extensao")
    p.add_argument("--cpl", type=int, default=38, help="caracteres por linha")
    p.add_argument("--linhas", type=int, default=2)
    p.add_argument("--velocidade", type=int, default=160, help="espeak, palavras/min")
    args = p.parse_args()

    texto = lt.limpa_para_locucao(open(args.roteiro, encoding="utf-8").read())
    frases = lt.divide_em_frases(texto)
    palavras = texto.split()
    cues = lt.monta_cues(palavras, cpl=args.cpl, linhas=args.linhas)
    if not cues:
        sys.exit("Roteiro vazio.")

    dur_video = duracao(args.video)
    largura, altura = resolucao(args.video)
    print("Video: %.2fs, %dx%d | %d frases, %d blocos de legenda"
          % (dur_video, largura, altura, len(frases), len(cues)))

    with tempfile.TemporaryDirectory() as tmp:
        real = extrai_audio(args.video, os.path.join(tmp, "real.wav"))
        sint, marcas = sintetiza_frases(frases, tmp, args.velocidade)

        y_sint, _, _ = carrega(sint)
        y_real, deslocamento, _ = carrega(real, aparar=True)
        f_sint, f_real = features(y_sint), features(y_real)
        print("Alinhando %d frames de roteiro contra %d de gravacao "
              "(a fala comeca em %.2fs)..."
              % (f_sint.shape[1], f_real.shape[1], deslocamento))
        mapa = mapa_de_tempo(f_sint, f_real)

    def para_real(t_sint):
        frame = min(int(round(t_sint * SR / HOP)), len(mapa) - 1)
        return float(mapa[frame]) * HOP / SR + deslocamento

    tempos_frase = [[para_real(a), para_real(b)] for a, b in marcas]
    ini_pal, fim_pal = tempos_por_palavra(frases, tempos_frase)

    brutos = [[ini_pal[c["primeira_palavra"]], fim_pal[c["ultima_palavra"]]]
              for c in cues]
    tempos = ajusta_tempos(brutos, [c["texto"] for c in cues], dur_video)

    os.makedirs(os.path.dirname(os.path.abspath(args.saida)), exist_ok=True)
    srt = escreve_srt(cues, tempos, args.saida + ".srt")
    ass = escreve_ass(cues, tempos, args.saida + ".ass", largura, altura)
    print("Legendas: %s e %s" % (srt, ass))
    print("Fala de %.2fs a %.2fs" % (tempos[0][0], tempos[-1][1]))


if __name__ == "__main__":
    main()
