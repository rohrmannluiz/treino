# Treino — app do programa de musculação

App instalável (PWA) publicado por GitHub Pages em
<https://rohrmannluiz.github.io/treino/>.

## Arquivos

| Arquivo | Papel |
|---|---|
| `index.html` | O app inteiro: layout, fontes embutidas, dados do programa e lógica. **É a fonte da verdade.** |
| `sw.js` | Service worker. Cuida do funcionamento offline e de entregar versões novas. |
| `manifest.webmanifest` | Metadados de instalação (nome, cor, ícones). |
| `icon-*.png` | Ícones LRF da tela inicial. Não mexer sem pedido explícito. |

Os exercícios ficam na constante `DAYS`, uma única linha JSON dentro do
`index.html`. Cada exercício é uma lista na ordem:

```
[nome, séries, faixa de reps, observação, busca do YouTube, descanso, método]
```

## Como atualizar o treino

1. Alterar a linha `const DAYS = [...]` no `index.html`.
2. Subir o `index.html` no repositório (mesmo nome, substitui sozinho).
3. Abrir o app no iPhone uma vez com internet. Ele recarrega sozinho.

Ao mudar qualquer coisa, subir também a constante `VERSAO` no `index.html`.
Ela aparece no rodapé do app e é a única forma de saber, olhando a tela, se a
versão nova chegou.

Não é preciso apagar nem reinstalar o app, e o histórico de cargas continua
intacto — ele vive no aparelho, não no arquivo.

## Cuidados aprendidos na prática

**O `sw.js` não pode usar `cache.addAll()`.** É tudo ou nada: um único arquivo
faltando faz a instalação inteira falhar em silêncio e o app fica sem service
worker nenhum — sem offline, e sem o mecanismo que entrega atualizações. Foi o
que aconteceu quando o `manifest.webmanifest` sumiu do repositório. Cada arquivo
agora é cacheado por conta própria, com `catch`.

**Ao mexer no `sw.js`, mudar também a constante `CACHE`.** Sem isso o worker novo
não instala.

**O histórico é indexado pelo nome do exercício**, não pela posição na ficha.
Reordenar ou remover exercícios não embaralha mais as cargas. A chave é o nome
normalizado (`Supino inclinado` → `supino-inclinado`), então **renomear um
exercício desliga o histórico dele**. Para renomear sem perder a progressão, é
preciso migrar a chave antiga junto.

**A skill `treinos` gera este app.** O `scripts/gerar_site.py` foi atualizado para
produzir exatamente esta versão — conferido bloco a bloco contra o `index.html`
publicado: CSS, JavaScript e corpo do HTML idênticos. O `scripts/programa.json`
continua sendo a fonte dos exercícios, e o `versao` dele (`2026-09-c`) é o que
aparece no rodapé do app.

Na prática, mudar o treino é editar o `programa.json` na skill, subir o `versao`,
rodar `python scripts/gerar_site.py` e subir o `index.html` gerado aqui.

O `scripts/gerar_app.py` da skill, que produz um `treino.html` único sem
hospedagem, continua defasado — gera a versão anterior, sem cronômetro nem
repetições. Ele não afeta este repositório, mas não sirva esse arquivo como se
fosse o app atual.

## Backup

O histórico fica só no aparelho (`localStorage`), sem servidor. Em Histórico:

- **Exportar** — no iPhone abre a folha de compartilhamento (salvar em Arquivos,
  mandar por e-mail). No computador baixa o `.json`.
- **Copiar JSON** — joga o backup na área de transferência.
- **Importar** — cola um backup e substitui o histórico do aparelho.

Vale exportar de vez em quando. Limpar os dados do Safari apaga o histórico.

## Diagnóstico quando algo não aparece

1. Abrir o endereço numa janela anônima no computador. Janela anônima não usa
   service worker, então mostra o que está de fato no servidor. Se aqui já está
   errado, o problema é o arquivo que subiu, não o cache.
2. Conferir o carimbo de versão no rodapé do app.
3. No iPhone: abrir com internet, fechar de vez (deslizar para cima no seletor
   de apps) e abrir de novo.
4. Se persistir: apagar o app da tela inicial e readicionar pelo Safari. O
   histórico sobrevive, porque está preso ao domínio e não ao ícone.
