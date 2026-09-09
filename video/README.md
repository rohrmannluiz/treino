# Vídeo — roteiro, legenda e edição

Fluxo de dois tempos: primeiro o roteiro, depois o vídeo gravado.

## Etapa 1 — da notícia ao roteiro

Mande a notícia ou o artigo (link, texto colado ou arquivo). Sai um roteiro
em texto corrido, em parágrafos, pronto para o teleprompter, com no máximo
90 segundos de leitura.

O roteiro vai para `roteiros/`. Antes de gravar, dá para conferir o tempo:

```bash
python3 tools/roteiro.py roteiros/pix.txt --cues
```

Mostra palavras, sílabas, duração estimada em três ritmos e como o texto
vai ficar dividido na tela.

## Etapa 2 — do vídeo gravado ao vídeo final

Mande o arquivo gravado. Ele vai para `entrada/`, e o resultado sai em
`saida/`. A legenda é gerada a partir do roteiro que você leu — não de um
reconhecimento de fala —, então ela nunca erra palavra, nome próprio nem
acento.

```bash
# 1. edições que mudam a duração (se houver) vêm sempre antes
python3 tools/editar.py silencios --video entrada/pix.mp4 --saida saida/pix_cortado.mp4

# 2. gera a legenda alinhada à fala
python3 tools/alinhar.py --video saida/pix_cortado.mp4 --roteiro roteiros/pix.txt \
    --saida legendas/pix

# 3. queima a legenda na imagem
python3 tools/legendar.py --video saida/pix_cortado.mp4 --legenda legendas/pix.ass \
    --saida saida/pix_final.mp4
```

**A ordem importa.** Cortar depois de legendar desencontra a legenda da
fala. Todo corte acontece antes do alinhamento.

## O padrão da legenda

| | |
|---|---|
| Fonte | Inter SemiBold (sóbria, desenhada para tela) |
| Corpo | 4,2% da largura no vertical, 4,5% da altura no horizontal — 45px em 1080x1920 |
| Posição | Inferior, centralizada, a 12% da altura da borda (fora da área onde Instagram e TikTok desenham a interface) |
| Cor | Branco, contorno preto fino e sombra suave — legível sobre fundo claro ou escuro |
| Linhas | No máximo 2, até 38 caracteres cada |
| Ritmo | No máximo 17 caracteres por segundo; cada bloco fica de 0,85s a 7s na tela |

Sem caixa colorida, sem caixa alta, sem palavra saltando. Os limites de
linha, duração e velocidade de leitura seguem o guia de legendagem da
Netflix para pt-BR.

Para mudar o peso visual: `--perfil discreta` (menor) ou `--perfil destaque`
(maior) no `legendar.py`.

## Ferramentas

| Comando | O que faz |
|---|---|
| `tools/setup.sh` | Instala ffmpeg, espeak-ng, fontes e bibliotecas |
| `tools/roteiro.py` | Estima a duração do roteiro e mostra a divisão em legendas |
| `tools/alinhar.py` | Casa o roteiro com a fala e gera `.srt` e `.ass` |
| `tools/legendar.py` | Queima a legenda no vídeo |
| `tools/editar.py` | `cortar`, `silencios`, `audio`, `formato`, `capa` |

`tools/setup.sh` precisa rodar uma vez por sessão: a máquina é descartada
ao fim de cada uma e nada fica instalado.

## Como a legenda é sincronizada

O vídeo é lido no teleprompter, então o texto já é conhecido. O problema
não é descobrir *o que* foi dito, e sim *quando* — o que se resolve por
alinhamento forçado, e não por reconhecimento de fala:

1. o áudio do vídeo é extraído e o silêncio das pontas, cortado;
2. cada frase do roteiro é sintetizada com espeak-ng em pt-BR e emendada
   numa faixa de referência;
3. as duas faixas são comparadas por MFCC e casadas com DTW, o que produz
   a correspondência entre o tempo da referência e o tempo da gravação;
4. dentro de cada frase, o tempo é repartido entre as palavras conforme o
   número de sílabas.

Sintetizar por frase, e não por bloco de legenda, é o que faz a técnica
funcionar: o espeak só produz entonação natural com a frase inteira, e
cortada no meio a prosódia fica artificial. Em teste controlado, essa
mudança levou o erro médio de 1,07s para 0,02s.

**Ressalva honesta:** esse número vem de uma gravação sintética (voz do
próprio espeak, com timbre e ritmo deslocados), porque o ambiente não tem
acesso a nenhum modelo de voz humana para teste. Com voz real o erro será
maior. Se acontecer de a legenda entrar adiantada ou atrasada, é só avisar
que eu calibro.

## Limitações

- O alinhamento pressupõe que você leu o roteiro. Se improvisar bastante,
  me mande o que mudou — com o texto certo, a legenda volta a bater.
- `editar.py audio` avisa quando o alvo de volume não cabe no arquivo:
  isso é sinal de gravação com pico alto e volume médio baixo, que se
  resolve na captação, não na edição.
- A estimativa de duração do roteiro usa 5,2 sílabas por segundo. É uma
  média de locução; depois de alguns vídeos seus dá para calibrar com o
  seu ritmo real.
