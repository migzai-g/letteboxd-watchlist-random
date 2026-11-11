# 🎬 Sorteador de Filme (Letterboxd)

Sem saber o que assistir? Digite seu usuário do [Letterboxd](https://letterboxd.com), escolha um tema (ou não) e o programa sorteia um filme da sua **watchlist**.

Não precisa instalar nada: usa só a biblioteca padrão do Python.

---

## Requisitos

- Python 3.8 ou superior
- Uma conta no Letterboxd com a **watchlist pública** (ou o arquivo CSV exportado, veja o plano B abaixo)

---

## Como usar

### 1. Modo interativo (o mais fácil)

```bash
python sorteador.py
```

O programa pergunta seu usuário e o tema, sorteia um filme e, se você apertar `Enter`, sorteia outro, sem repetir. Digite `n` para sair.

(Também é o que acontece ao clicar em "Run" no VS Code.)

### 2. Direto pelo terminal

```bash
python sorteador.py seu_usuario
python sorteador.py seu_usuario --tema terror
python sorteador.py seu_usuario --tema 11 -n 3
```

Você pode colocar só o nome (`migzai`), com arroba (`@migzai`) ou o link do perfil (`https://letterboxd.com/migzai/`).

### Opções

| Opção | Descrição |
|-------|-----------|
| `--tema TEMA` | Sorteia só entre filmes desse tema (nome ou número) |
| `-n N`, `--quantidade N` | Quantos filmes sortear (padrão: `1`, sem repetir) |
| `--temas` | Mostra a lista de temas disponíveis |
| `--csv ARQUIVO` | Usa o CSV exportado em vez de acessar o site (plano B) |

### Temas disponíveis

Ação · Aventura · Animação · Comédia · Crime · Documentário · Drama · Família · Fantasia · História · Terror · Música · Mistério · Romance · Ficção científica · Suspense · Guerra · Faroeste

Você pode digitar o nome (com ou sem acento, ex.: `acao`, `ficção científica`) ou o número que aparece em `--temas`.

---

## Exemplo de saída

```
$ python sorteador.py seu_usuario --tema terror
  lendo a watchlist... 34 filmes
34 filmes na lista (tema: Terror).

----------------------------------------------------
  Hoje você vai assistir:

    The Thing (1982)
    https://letterboxd.com/film/the-thing-1982/
----------------------------------------------------
```

---

## Plano B: usando o arquivo CSV

O Letterboxd não tem uma API pública, então o programa lê a página da sua watchlist. Se o site bloquear o acesso automático ou mudar o formato da página, use o arquivo exportado:

1. No Letterboxd, vá em **Settings → Import & Export → Export your data**
2. Baixe e descompacte o `.zip`
3. Rode com o `watchlist.csv`:

```bash
python sorteador.py --csv watchlist.csv
```

O repositório traz o `watchlist-exemplo.csv` para você testar.

> No modo CSV não dá para escolher o tema, porque o arquivo não informa o gênero dos filmes.

---

## Como funciona

1. **Montar o endereço** (`buscar_watchlist`): a watchlist fica em `letterboxd.com/USUARIO/watchlist/`, e com tema em `.../watchlist/genre/horror/`. O próprio Letterboxd faz o filtro por gênero.
2. **Ler as páginas** (`ExtratorFilmes`): cada página tem cerca de 28 filmes. O programa passa por todas (com uma pausa de meio segundo entre elas, para ser educado com o site) e extrai o nome e o link de cada filme do HTML.
3. **Sortear** (`random.shuffle`): a lista é embaralhada. Assim, sortear vários filmes ou apertar `Enter` de novo nunca repete.

### Estrutura do código (`sorteador.py`)

| Função | O que faz |
|--------|-----------|
| `resolver_tema()` | Converte "Terror" ou "11" no nome que o Letterboxd usa (`horror`) |
| `limpar_usuario()` | Aceita usuário, `@usuario` ou link do perfil |
| `baixar()` | Baixa o HTML de uma página |
| `ExtratorFilmes` | Encontra os filmes dentro do HTML |
| `buscar_watchlist()` | Percorre todas as páginas e junta os filmes |
| `ler_csv()` | Plano B: lê o `watchlist.csv` |
| `main()` | Junta tudo e mostra o resultado |

---

## Problemas comuns

- **"Não achei a watchlist":** confira o usuário. O perfil e a watchlist precisam estar públicos.
- **"O Letterboxd bloqueou o acesso":** use o plano B com `--csv`.
- **"Nenhum filme encontrado":** a watchlist pode estar vazia, não ter filmes desse tema, ou o Letterboxd mudou o formato da página. Teste com `--csv`.
- **Demora um pouco:** watchlists grandes têm muitas páginas, e o programa espera entre elas de propósito.

---

## Aviso

Projeto feito para estudo e uso pessoal. O programa lê só páginas públicas, em ritmo lento, e não guarda nenhum dado. Respeite os termos de uso do Letterboxd e não use para coletar dados em massa.

---

## Ideias para evoluir

- Sortear também entre filmes de uma **lista** específica (`letterboxd.com/usuario/list/nome-da-lista/`)
- Filtrar por década ou por duração
- Mostrar nota média, diretor e sinopse buscando a página de cada filme
- Escolher dois ou mais temas ao mesmo tempo
- Versão para músicas, sorteando de uma lista do last.fm

---

## Licença

Livre para estudar, usar e modificar.