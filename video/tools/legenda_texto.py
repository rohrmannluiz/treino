# -*- coding: utf-8 -*-
"""Segmentacao de texto em blocos de legenda (cues) para portugues do Brasil.

Usado tanto pelo roteiro.py (estimativa de duracao) quanto pelo alinhar.py
(geracao das legendas). As regras seguem o guia de legendagem da Netflix
para pt-BR: no maximo 2 linhas, 42 caracteres por linha, 17 caracteres por
segundo, duracao entre 0,83s e 7s.
"""

import re
import unicodedata

VOGAIS = "aeiouáéíóúâêôàãõü"

# Palavras que nunca devem terminar uma linha: a quebra fica antes delas.
NAO_TERMINA_LINHA = {
    "a", "o", "as", "os", "um", "uma", "uns", "umas", "de", "do", "da", "dos",
    "das", "em", "no", "na", "nos", "nas", "por", "pelo", "pela", "para", "pra",
    "com", "sem", "sob", "sobre", "entre", "ate", "até", "que", "e", "ou", "mas",
    "se", "ao", "aos", "à", "às", "meu", "minha", "seu", "sua", "este", "esta",
    "esse", "essa", "aquele", "aquela", "qual", "quais", "quando", "onde",
}

FIM_DE_FRASE = ".!?…"
PAUSA_MEDIA = ",;:"


def normaliza_espacos(texto):
    """Junta o texto num paragrafo unico com espacamento regular."""
    return re.sub(r"\s+", " ", texto).strip()


def so_letras(palavra):
    return re.sub(r"[^\w]", "", palavra, flags=re.UNICODE)


def conta_silabas(texto):
    """Conta silabas aproximadas em pt-BR.

    Cada grupo de vogais contiguas conta como uma silaba (ditongos viram
    uma so). Subestima hiatos como 'sa-i-da', mas o erro fica abaixo de 5%
    em texto corrido, o suficiente para estimar duracao de locucao.
    """
    total = 0
    for palavra in texto.lower().split():
        limpa = so_letras(palavra)
        if not limpa:
            continue
        grupos = re.findall(r"[%s]+" % VOGAIS, limpa)
        total += max(1, len(grupos))
    return total


def conta_palavras(texto):
    return len([p for p in texto.split() if so_letras(p)])


def divide_em_frases(texto):
    """Quebra o texto em frases, mantendo a pontuacao no fim de cada uma."""
    texto = normaliza_espacos(texto)
    frases = re.split(r"(?<=[%s])\s+" % re.escape(FIM_DE_FRASE), texto)
    return [f.strip() for f in frases if f.strip()]


def divide_em_clausulas(frase):
    """Quebra uma frase longa nas pausas internas (virgula, ponto e virgula)."""
    partes = re.split(r"(?<=[%s])\s+" % re.escape(PAUSA_MEDIA), frase)
    return [p.strip() for p in partes if p.strip()]


def _custo_quebra(esquerda, direita):
    """Menor custo = melhor ponto de quebra entre duas linhas."""
    custo = abs(len(esquerda) - len(direita))          # prefere linhas parelhas
    ultima = so_letras(esquerda.split()[-1].lower()) if esquerda.split() else ""
    if ultima in NAO_TERMINA_LINHA:
        custo += 100                                   # nao separa artigo/preposicao
    if esquerda and esquerda[-1] in PAUSA_MEDIA:
        custo -= 20                                    # quebra apos pausa e natural
    return custo


def quebra_em_linhas(texto, cpl):
    """Divide um cue em no maximo duas linhas de ate `cpl` caracteres."""
    texto = normaliza_espacos(texto)
    if len(texto) <= cpl:
        return [texto]

    palavras = texto.split()
    melhor, melhor_custo = None, None
    for i in range(1, len(palavras)):
        esq = " ".join(palavras[:i])
        dir_ = " ".join(palavras[i:])
        if len(esq) > cpl or len(dir_) > cpl:
            continue
        custo = _custo_quebra(esq, dir_)
        if melhor_custo is None or custo < melhor_custo:
            melhor, melhor_custo = (esq, dir_), custo

    if melhor:
        return list(melhor)

    # Nao coube em duas linhas: corta na ultima palavra que ainda cabe,
    # preservando a ordem do texto.
    corte, atual = 0, 0
    for i, p in enumerate(palavras):
        custo = len(p) + (1 if i else 0)
        if atual + custo > cpl:
            break
        atual += custo
        corte = i + 1
    corte = max(1, corte)
    return [" ".join(palavras[:corte]), " ".join(palavras[corte:])]


def _pontuacao_final(palavra):
    """Classifica a pausa que a palavra encerra: 2=frase, 1=pausa, 0=nenhuma."""
    fim = palavra.rstrip('")\u201d\u2019')
    if fim and fim[-1] in FIM_DE_FRASE:
        return 2
    if fim and fim[-1] in PAUSA_MEDIA:
        return 1
    return 0


def monta_cues(texto, cpl=38, linhas=2):
    """Transforma o roteiro corrido na lista de blocos de legenda.

    Enche cada cue ate o limite (cpl * linhas) e escolhe o corte que cai na
    melhor fronteira: fim de frase primeiro, depois pausa media, por ultimo
    o limite de espaco. Nunca corta deixando artigo ou preposicao pendurada.
    """
    limite = cpl * linhas
    if isinstance(texto, list):
        palavras = list(texto)                   # ja tokenizado pelo alinhador
    else:
        palavras = normaliza_espacos(limpa_para_locucao(texto)).split()
    cues, i = [], 0

    while i < len(palavras):
        # Candidatos: todo j tal que palavras[i:j] cabe no cue.
        candidatos, tamanho = [], 0
        for j in range(i, len(palavras)):
            tamanho += len(palavras[j]) + (1 if j > i else 0)
            if tamanho > limite and j > i:
                break
            candidatos.append((j + 1, tamanho))
        if not candidatos:
            candidatos = [(i + 1, len(palavras[i]))]

        melhor, melhor_nota = None, None
        for fim, tamanho in candidatos:
            ultima = palavras[fim - 1]
            pont = _pontuacao_final(ultima)
            ocupacao = tamanho / limite
            # Fim de frase corta sempre. Pausa media so vale a pena se o cue
            # ja esta cheio: senao vira um flash curto demais na tela.
            if pont == 2:
                nota = 3.0 + ocupacao
            elif pont == 1 and ocupacao >= 0.6:
                nota = 1.2 + ocupacao
            else:
                nota = ocupacao
            if pont == 0 and so_letras(ultima.lower()) in NAO_TERMINA_LINHA:
                nota -= 5.0
            resto = len(palavras) - fim
            if 0 < resto <= 2:          # evita sobra orfa no ultimo cue
                nota -= 1.5
            if melhor_nota is None or nota > melhor_nota:
                melhor, melhor_nota = fim, nota

        bloco = normaliza_espacos(" ".join(palavras[i:melhor]))
        if bloco:
            cues.append({"texto": bloco,
                         "linhas": quebra_em_linhas(bloco, cpl),
                         "primeira_palavra": i,     # indices no texto completo,
                         "ultima_palavra": melhor - 1})   # para achar os tempos
        i = melhor

    return cues


def estima_duracao(texto, silabas_por_segundo=5.2, pausa_frase=0.35):
    """Estima a duracao da locucao em segundos.

    5,2 silabas/s corresponde a uma leitura de teleprompter confortavel em
    pt-BR (fala espontanea fica entre 5,8 e 6,2). Soma uma pausa curta por
    fim de frase, que e onde o locutor respira.
    """
    silabas = conta_silabas(texto)
    frases = len(divide_em_frases(texto))
    return silabas / silabas_por_segundo + max(0, frases - 1) * pausa_frase


def limpa_para_locucao(texto):
    """Remove marcacoes que nao devem ser lidas nem legendadas."""
    texto = re.sub(r"\[[^\]]*\]", " ", texto)   # [pausa], [corte]
    texto = re.sub(r"^#+\s*", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"\*\*?([^*]+)\*\*?", r"\1", texto)
    return normaliza_espacos(texto)
