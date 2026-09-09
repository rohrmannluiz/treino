---
name: video
description: Fluxo de vídeo do Luiz, em dois tempos. (1) Transformar notícia, matéria, artigo ou release em roteiro de teleprompter de no máximo 90 segundos, em texto corrido. (2) Depois que ele gravar, legendar e editar o vídeo enviado. Use SEMPRE que ele mandar um link de notícia, texto de matéria ou artigo pedindo roteiro, vídeo ou "transforma isso em vídeo"; e SEMPRE que mandar um arquivo de vídeo para legendar, cortar, ajustar áudio, mudar formato ou tirar pausas — inclusive quando só disser "põe a legenda", "corta o começo", "tira as pausas" ou "deixa pronto pro Reels".
---

# Vídeo: roteiro, legenda e edição

Projeto em `video/`. Leia `video/README.md` para o detalhe técnico e
`video/roteiros/MODELO.md` para o padrão de escrita.

## Antes de qualquer coisa que toque em arquivo de vídeo

```bash
bash video/tools/setup.sh
```

A máquina da sessão é descartada ao fim de cada uma: sem isso não há
ffmpeg, espeak-ng nem as bibliotecas. Rodar de novo quando já está tudo
instalado não custa nada.

## Etapa 1 — notícia vira roteiro

1. Leia a matéria inteira. Se vier link, busque o conteúdo.
2. Escreva em texto corrido, parágrafos, sem marcação de cena. É o que ele
   vai ler no teleprompter.
3. Siga a estrutura e as regras de `video/roteiros/MODELO.md`: gancho na
   primeira frase, frases de até 25 palavras, voz ativa, número falado por
   extenso, nada de travessão ou parêntese no meio da frase.
4. Alvo de 190 a 215 palavras — cabe em 90s mesmo lendo pausado.
5. Salve em `video/roteiros/<assunto>.txt` e confira:

```bash
python3 video/tools/roteiro.py video/roteiros/<assunto>.txt
```

Se estourar, corte conteúdo — não acelere a leitura. O texto do roteiro é
a fonte da legenda depois, então ele precisa ficar salvo.

Entregue o roteiro na conversa, em texto, pronto para copiar. Diga a
duração estimada e o número de palavras.

## Etapa 2 — vídeo gravado vira vídeo final

Ordem obrigatória: **primeiro toda edição que muda a duração, depois a
legenda.** Cortar depois de legendar desencontra a legenda da fala.

```bash
# 1. o arquivo enviado vai para video/entrada/
# 2. cortes, se ele pediu
python3 video/tools/editar.py silencios --video video/entrada/x.mp4 --saida video/saida/x_c.mp4
python3 video/tools/editar.py cortar --video ... --de 0:03 --ate 0:08 [--remover]
python3 video/tools/editar.py audio --video ... --saida ...      # volume padrão de rede social
python3 video/tools/editar.py formato --video ... --para 9:16

# 3. legenda alinhada ao roteiro que ele leu
python3 video/tools/alinhar.py --video video/saida/x_c.mp4 \
    --roteiro video/roteiros/x.txt --saida video/legendas/x

# 4. queima na imagem
python3 video/tools/legendar.py --video video/saida/x_c.mp4 \
    --legenda video/legendas/x.ass --saida video/saida/x_final.mp4
```

Confira o resultado antes de entregar: extraia um quadro em cima de uma
fala e olhe a imagem.

```bash
python3 video/tools/editar.py capa --video video/saida/x_final.mp4 --saida /tmp/conf.png --em 0:05
```

Entregue o arquivo final com `SendUserFile`.

## A legenda

Fonte sóbria (Inter SemiBold), branca com contorno preto fino, no máximo
duas linhas de 38 caracteres, na parte inferior, a 12% da altura da borda.
Corpo moderado: 45px em 1080x1920. Nunca caixa alta, nunca palavra
saltando, nunca caixa colorida.

Se ele pedir maior ou menor, use `--perfil destaque` ou `--perfil discreta`
no `legendar.py`. Se pedir outra coisa (cor, posição, fonte), ajuste
`video/tools/estilo_legenda.py` — é lá que mora o padrão.

## Quando a legenda não bate com a fala

O alinhamento parte do princípio de que ele leu o roteiro. Se improvisou,
peça o que mudou ou transcreva de ouvido o trecho divergente, corrija o
`.txt` e rode o `alinhar.py` de novo. Não tem reconhecimento de fala
disponível nesta máquina: os modelos são baixados de hosts que a política
de rede bloqueia.
