# Como o roteiro é escrito

Texto corrido, em parágrafos, para ler no teleprompter. Sem marcação de
cena, sem "corta para", sem indicação de trilha: só o que sai da boca.

## Tamanho

Teto de **90 segundos**, o que dá **190 a 215 palavras**.

A conta é por sílaba, não por palavra: 5,2 sílabas por segundo é locução em
pt-BR sem correria, e cada fim de frase custa mais uma pausa curta. Nesse
ritmo caberiam umas 230 palavras — a faixa é menor de propósito, para o
roteiro continuar dentro dos 90s mesmo num dia em que a leitura sair mais
pausada. O exemplo abaixo tem 182 palavras: 72s lendo normal, 81s lendo
devagar.

Confira antes de gravar:

```bash
python3 ../tools/roteiro.py meu_roteiro.txt
```

## Estrutura

| Trecho | Papel | Tamanho |
|---|---|---|
| Gancho | O fato mais forte, já na primeira frase. Sem "hoje eu vou falar sobre" | 1 frase |
| Contexto | O que o espectador precisa saber para entender | 2 a 3 frases |
| Miolo | Os números e o que de fato mudou | 3 a 4 frases |
| Efeito | O que isso muda para quem está assistindo | 2 a 3 frases |
| Fecho | Uma frase que fecha, sem pedir like | 1 frase |

## Regras de escrita

- Frases de até 25 palavras. Frase longa trava a leitura e estoura a linha
  da legenda.
- Voz ativa: "o Banco Central mudou a regra", não "a regra foi mudada".
- Número falado como se fala: "mil e duzentos reais", não "R$ 1.200,00";
  "quase um terço", não "31,7%".
- Sigla só depois de explicada, e apenas se for reaparecer.
- Nada de travessão, parêntese ou aspas no meio da frase: no teleprompter
  viram tropeço.
- Cada parágrafo é um bloco de respiração. Duas a quatro frases.

## Exemplo

> O Banco Central mudou a regra do Pix, e quem transfere valor alto pelo
> celular vai sentir já em janeiro.
>
> A partir do dia primeiro, toda transferência acima de mil reais feita
> pelo aplicativo passa por uma verificação extra. O cliente também pode
> definir o próprio limite direto no banco, e mudar quando quiser. Segundo
> a autarquia, a medida responde ao aumento de golpes no último ano.
>
> Na prática, três coisas mudam. A confirmação de transferências altas
> deixa de ser imediata na madrugada. O banco passa a avisar por
> notificação sempre que o limite for alterado. E o pedido de estorno em
> caso de golpe ganha prazo próprio, separado da contestação comum.
>
> Para quem usa o Pix no dia a dia, no supermercado, na feira, dividindo a
> conta do almoço, nada disso muda. A regra mira o valor alto e o horário
> incomum, que é onde o golpe acontece.
>
> Quem tem limite baixo e nunca transfere de madrugada não precisa fazer
> nada. Os outros ganham uma tela a mais no caminho, e alguns minutos de
> espera que podem evitar um prejuízo grande.
