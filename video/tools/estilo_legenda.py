# -*- coding: utf-8 -*-
"""Estilo visual da legenda (formato ASS).

Padrao da casa: fonte sobria, corpo moderado, sempre na parte inferior.
Sem caixa colorida, sem palavra saltando, sem caixa alta. O contorno fino
mais a sombra suave garantem leitura sobre fundo claro ou escuro sem que a
legenda vire o elemento principal da imagem.

Tamanho e margem saem da resolucao do video, entao o resultado fica igual
em 1080x1920 (vertical) e em 1920x1080 (horizontal).
"""

# Em ASS a cor e &HAABBGGRR: alfa, azul, verde, vermelho. Alfa 00 = opaco.
BRANCO = "&H00FFFFFF"
PRETO = "&H00000000"
SOMBRA = "&H90000000"          # preto a ~44% - adensa sem virar caixa

# corpo e margem sao fracao da resolucao; contorno e sombra sao fracao do
# corpo da letra, que e o que mantem a proporcao certa entre letra e traco.
PERFIS = {
    # nome:        (fonte,             corpo, contorno, sombra, margem)
    "padrao":      ("Inter SemiBold",  0.042, 0.055, 0.030, 0.120),
    "discreta":    ("Inter Medium",    0.037, 0.050, 0.026, 0.120),
    "destaque":    ("Inter SemiBold",  0.047, 0.060, 0.034, 0.120),
    "horizontal":  ("Inter SemiBold",  0.045, 0.055, 0.030, 0.065),
}


def medidas(largura, altura, perfil="padrao"):
    """Converte as proporcoes do perfil em pixels para esta resolucao.

    Em video vertical o corpo da letra se mede pela largura (e ela que
    limita quantos caracteres cabem na linha); em video horizontal, pela
    altura. Sem isso a legenda sai minuscula num formato e enorme no outro.
    """
    vertical = altura >= largura
    if not vertical and perfil == "padrao":
        perfil = "horizontal"
    fonte, corpo, contorno, sombra, margem = PERFIS[perfil]
    base = largura if vertical else altura
    px = round(base * corpo)
    return {
        "fonte": fonte,
        "corpo": px,
        "contorno": round(px * contorno, 1),
        "sombra": round(px * sombra, 1),
        # Margem maior no vertical: a parte de baixo da tela e onde as redes
        # sociais desenham legenda do post, perfil e botoes.
        "margem_v": round(altura * margem),
        "margem_h": round(largura * 0.075),
        "vertical": vertical,
    }


def cabecalho(largura, altura, perfil="padrao"):
    m = medidas(largura, altura, perfil)
    return (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        "YCbCr Matrix: TV.709\n"
        "PlayResX: %d\n"
        "PlayResY: %d\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Legenda,%s,%d,%s,%s,%s,%s,0,0,0,0,100,100,0,0,1,%s,%s,2,%d,%d,%d,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
        % (largura, altura, m["fonte"], m["corpo"], BRANCO, BRANCO, PRETO,
           SOMBRA, m["contorno"], m["sombra"], m["margem_h"], m["margem_h"],
           m["margem_v"])
    )


if __name__ == "__main__":
    for l, a in ((1080, 1920), (1920, 1080), (1080, 1080), (720, 1280)):
        m = medidas(l, a)
        print("%4dx%-4d  %-16s corpo %3dpx  contorno %.1f  margem inferior %3dpx"
              % (l, a, m["fonte"], m["corpo"], m["contorno"], m["margem_v"]))
