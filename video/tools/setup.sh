#!/usr/bin/env bash
# Prepara a maquina para editar video.
#
# A sessao do Claude roda em container descartavel: nada do que e instalado
# sobrevive ate a proxima. Rodar isto antes de trabalhar leva alguns minutos
# na primeira vez e nada nas seguintes.
set -euo pipefail

echo "== conferindo o que ja existe =="
falta=0
for prog in ffmpeg ffprobe espeak-ng; do
    if command -v "$prog" >/dev/null 2>&1; then
        echo "  ok      $prog"
    else
        echo "  falta   $prog"
        falta=1
    fi
done

if [ "$(fc-list 2>/dev/null | grep -ci inter || true)" = "0" ]; then
    echo "  falta   fonte Inter"
    falta=1
else
    echo "  ok      fonte Inter"
fi

if [ "$falta" = "1" ]; then
    echo
    echo "== instalando ffmpeg, espeak-ng e fontes =="
    apt-get update -qq
    apt-get install -y -qq ffmpeg espeak-ng fonts-inter fonts-roboto fonts-open-sans
    fc-cache -f >/dev/null 2>&1 || true
fi

echo
echo "== bibliotecas python =="
if python3 -c "import librosa, soundfile, numpy" 2>/dev/null; then
    echo "  ok      librosa, soundfile, numpy"
else
    echo "  instalando..."
    pip install -q numpy scipy librosa soundfile
fi

echo
echo "== conferencia final =="
ffmpeg -version | head -1
if ffmpeg -version 2>/dev/null | grep -c enable-libass >/dev/null; then
    echo "libass: ok (queima de legenda disponivel)"
else
    echo "ERRO: este ffmpeg nao tem libass, nao da para queimar legenda"; exit 1
fi
espeak-ng --version | head -1
python3 -c "import librosa; print('librosa', librosa.__version__)"
printf "fonte Inter: %s variantes\n" "$(fc-list | grep -ci inter || true)"
echo
echo "Pronto."
