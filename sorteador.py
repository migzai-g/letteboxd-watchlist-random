import argparse
import csv
import random
import re
import sys
import time
import unicodedata
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SITE = "https://letterboxd.com"
MAX_PAGINAS = 100   
PAUSA = 0.6         


class ErroSorteador(Exception):
    """Erro com mensagem amigável para mostrar ao usuário."""



TEMAS = [
    ("Ação", "action"), ("Aventura", "adventure"), ("Animação", "animation"),
    ("Comédia", "comedy"), ("Crime", "crime"), ("Documentário", "documentary"),
    ("Drama", "drama"), ("Família", "family"), ("Fantasia", "fantasy"),
    ("História", "history"), ("Terror", "horror"), ("Música", "music"),
    ("Mistério", "mystery"), ("Romance", "romance"),
    ("Ficção científica", "science-fiction"), ("Suspense", "thriller"),
    ("Guerra", "war"), ("Faroeste", "western"),
]


APELIDOS = {
    "scifi": "science-fiction", "sci-fi": "science-fiction", "ficcao": "science-fiction",
    "acao": "action", "comedia": "comedy", "romantico": "romance",
    "misterio": "mystery", "musical": "music", "western": "western",
}


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, para comparar 'Ação' com 'acao'."""
    texto = unicodedata.normalize("NFD", texto.lower().strip())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def resolver_tema(entrada: str):
    """Converte o que o usuário digitou (número ou nome) no gênero do Letterboxd."""
    entrada = normalizar(entrada)
    if entrada.isdigit():
        n = int(entrada)
        return TEMAS[n - 1][1] if 1 <= n <= len(TEMAS) else None
    for nome, slug in TEMAS:
        if entrada in (normalizar(nome), slug):
            return slug
    return APELIDOS.get(entrada)


def nome_do_tema(slug: str) -> str:
    return next((nome for nome, s in TEMAS if s == slug), slug)


def listar_temas():
    print("Temas disponíveis:")
    for i, (nome, _) in enumerate(TEMAS, 1):
        print(f"  {i:>2}) {nome}")


class ExtratorFilmes(HTMLParser):

    def __init__(self):
        super().__init__()
        self.principais = {}  
        self.links = {}       
        self.fora = 0         

    @staticmethod
    def _slug(valor):
        """Aceita 'parasite-2019' e '/film/parasite-2019/' e devolve 'parasite-2019'."""
        valor = (valor or "").strip().strip("/")
        if valor.startswith("film/"):
            valor = valor[5:]
        return valor if valor and "/" not in valor else None

    def handle_endtag(self, tag):
        if tag in ("nav", "header", "footer") and self.fora > 0:
            self.fora -= 1

    def handle_starttag(self, tag, attrs):
        if tag in ("nav", "header", "footer"):
            self.fora += 1
        a = dict(attrs)
        slug = self._slug(a.get("data-item-slug") or a.get("data-film-slug"))
        if not slug:
            slug = self._slug(a.get("data-item-link") or a.get("data-target-link"))
        nome = a.get("data-item-name") or a.get("data-film-name")
        if slug:
            if nome or slug not in self.principais:
                self.principais[slug] = nome
        elif tag == "a" and not self.fora and a.get("href", "").startswith("/film/"):
            slug = self._slug(a["href"])
            if slug:
                self.links.setdefault(slug, None)


def extrair_filmes(html: str) -> dict:
    """Devolve {slug: nome} com os filmes encontrados na página."""
    extrator = ExtratorFilmes()
    extrator.feed(html)
    return extrator.principais or extrator.links


def nome_pelo_slug(slug: str) -> str:
    """Plano B quando o nome não vem na página: 'the-thing-1982' -> 'The Thing 1982'."""
    return slug.replace("-", " ").title()


def baixar(url: str) -> str:
    """Baixa o HTML de uma página (se identificando com um User-Agent)."""
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; sorteador-de-filme/1.0)",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    })
    with urlopen(req, timeout=20) as resposta:
        return resposta.read().decode("utf-8", errors="ignore")


def limpar_usuario(entrada: str) -> str:
    """Aceita 'migzai', '@migzai' ou o link do perfil inteiro."""
    entrada = re.sub(r"^.*letterboxd\.com/", "", entrada.strip())
    return entrada.lstrip("@").strip("/").split("/")[0]


def buscar_watchlist(usuario: str, genero=None) -> list:
    """
    Percorre as páginas da watchlist (e do tema, se houver) e devolve uma
    lista de filmes: [{"nome": ..., "url": ...}, ...]
    """
    base = f"{SITE}/{usuario}/watchlist/" + (f"genre/{genero}/" if genero else "")
    achados = {}

    for pagina in range(1, MAX_PAGINAS + 1):
        url = base if pagina == 1 else f"{base}page/{pagina}/"
        try:
            html = baixar(url)
        except HTTPError as erro:
            if erro.code == 404:
                if pagina == 1:
                    raise ErroSorteador(
                        f"Não achei a watchlist de '{usuario}'. Confira o usuário "
                        "(o perfil precisa ser público).")
                break  
            if erro.code in (403, 429):
                raise ErroSorteador(
                    "O Letterboxd bloqueou o acesso automático. Use o plano B: "
                    "exporte sua watchlist em CSV e rode  python sorteador.py --csv watchlist.csv")
            raise ErroSorteador(f"O Letterboxd respondeu com erro {erro.code}.")
        except URLError:
            raise ErroSorteador("Não consegui acessar a internet.")

        novos = {s: n for s, n in extrair_filmes(html).items() if s not in achados}
        if not novos:
            break  
        achados.update(novos)
        print(f"\r  lendo a watchlist... {len(achados)} filmes", end="", flush=True)
        time.sleep(PAUSA)
    print()

    return [
        {"nome": nome or nome_pelo_slug(slug), "url": f"{SITE}/film/{slug}/"}
        for slug, nome in achados.items()
    ]


def ler_csv(caminho: str) -> list:
    """
    Lê o watchlist.csv exportado pelo Letterboxd
    (Configurações > Importar e exportar > Exportar seus dados).
    Colunas usadas: Name, Year, Letterboxd URI.
    """
    try:
        with open(caminho.strip('"'), newline="", encoding="utf-8-sig") as arquivo:
            linhas = list(csv.DictReader(arquivo))
    except FileNotFoundError:
        raise ErroSorteador(f"Não encontrei o arquivo: {caminho}")

    filmes = []
    for linha in linhas:
        nome = (linha.get("Name") or "").strip()
        if not nome:
            continue
        ano = (linha.get("Year") or "").strip()
        filmes.append({
            "nome": f"{nome} ({ano})" if ano else nome,
            "url": (linha.get("Letterboxd URI") or "").strip(),
        })
    return filmes


def mostrar_filme(filme: dict):
    print("-" * 52)
    print(f"  Hoje você vai assistir:\n")
    print(f"    {filme['nome']}")
    if filme["url"]:
        print(f"    {filme['url']}")
    print("-" * 52)


def main():
    parser = argparse.ArgumentParser(description="Sorteia um filme da sua watchlist do Letterboxd.")
    parser.add_argument("usuario", nargs="?", help="seu usuário do Letterboxd")
    parser.add_argument("--tema", help="tema/gênero (ex.: terror, comédia, 3). Veja --temas")
    parser.add_argument("--csv", help="usar o watchlist.csv exportado em vez de acessar o site")
    parser.add_argument("-n", "--quantidade", type=int, default=1, help="quantos filmes sortear (padrão 1)")
    parser.add_argument("--temas", action="store_true", help="mostra a lista de temas e sai")
    args = parser.parse_args()

    if args.temas:
        listar_temas()
        return

    interativo = not args.usuario and not args.csv
    if interativo:
        args.usuario = limpar_usuario(input("Seu usuário do Letterboxd: "))
        if not args.usuario:
            sys.exit("Nenhum usuário informado.")
        print()
        listar_temas()
        args.tema = input("\nEscolha um tema (número ou nome, Enter = qualquer): ").strip() or None
        print()

    genero = None
    if args.tema:
        genero = resolver_tema(args.tema)
        if not genero:
            sys.exit(f"Tema '{args.tema}' não reconhecido. Veja a lista com:  python sorteador.py --temas")

    try:
        if args.csv:
            if genero:
                print("Aviso: o CSV não traz gêneros, então o tema foi ignorado.\n")
            filmes = ler_csv(args.csv)
        else:
            filmes = buscar_watchlist(limpar_usuario(args.usuario), genero)
    except ErroSorteador as erro:
        sys.exit(f"Erro: {erro}")

    if not filmes:
        tema = f" no tema {nome_do_tema(genero)}" if genero else ""
        sys.exit(f"Nenhum filme encontrado{tema}. A watchlist pode estar vazia, "
                 "ou o Letterboxd mudou o formato da página (tente o plano B com --csv).")

    tema = f" (tema: {nome_do_tema(genero)})" if genero else ""
    print(f"{len(filmes)} filmes na lista{tema}.\n")

    random.shuffle(filmes)  

    if interativo:
        
        for filme in filmes:
            mostrar_filme(filme)
            if input("\nEnter = sortear outro, ou digite n para sair: ").strip().lower() == "n":
                break
            print()
        else:
            print("\nAcabaram os filmes da lista!")
    else:
        for filme in filmes[: max(1, args.quantidade)]:
            mostrar_filme(filme)


if __name__ == "__main__":
    main()