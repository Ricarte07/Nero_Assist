"""
Memória pessoal do Nero.

Armazena fatos, pessoas, girias e preferências do senhor Ricarte
em nero_memoria.json e os injeta no system prompt de cada conversa.

Comandos reconhecidos (fala ou texto):
  Salvar  : "lembra que X" / "aprende que X" / "anota que X" / "guarda que X"
  Apagar  : "esquece X" / "apaga da memória X" / "remove da memória X"
  Listar  : "o que você sabe sobre mim" / "lista sua memória" / "mostra sua memória"
"""

import json
import os
import re

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_MEM_FILE = os.path.join(_BASE_DIR, "nero_memoria.json")

# ── Padrões de comandos ────────────────────────────────────────────────────

# Salvar: começa com o verbo imperativo
_ADD_RE = re.compile(
    r"^(lembra|aprende|anota|guarda|salva)\s+(que\s+)?(.+)$",
    re.IGNORECASE | re.DOTALL,
)

# Apagar: "esquece X" / "apaga (da memória) X" / "remove (da memória) X"
_DEL_RE = re.compile(
    r"^(esquece|apaga|remove|deleta)\s+(da\s+mem[oó]ria\s+|isso\s+da\s+mem[oó]ria\s*)?(.+)$",
    re.IGNORECASE,
)

# Listar: qualquer forma de pedir o que Nero sabe/lembra
_LIST_RE = re.compile(
    r"(o\s+que\s+(voc[eê]|vc)\s+(sabe|lembra|tem\s+na\s+mem[oó]ria)"
    r"|lista\s+(sua\s+)?mem[oó]ria"
    r"|mostra\s+(sua\s+)?mem[oó]ria"
    r"|o\s+que\s+est[aá]\s+na\s+(sua\s+)?mem[oó]ria"
    r"|sua\s+mem[oó]ria\s+pessoal)",
    re.IGNORECASE,
)


# ── Funções de armazenamento ───────────────────────────────────────────────

def load() -> list[str]:
    """Carrega e retorna a lista de memórias salvas."""
    try:
        with open(_MEM_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            memorias = data.get("memorias", [])
            if memorias:
                print(f"[NERO MEM] {len(memorias)} memória(s) carregada(s).")
            return memorias
    except Exception as e:
        print(f"[NERO MEM] Erro ao carregar: {e}")
        return []


def _save(memorias: list[str]) -> None:
    with open(_MEM_FILE, "w", encoding="utf-8") as f:
        json.dump({"memorias": memorias}, f, ensure_ascii=False, indent=2)


def add(texto: str) -> str:
    """Adiciona uma memória. Retorna mensagem de confirmação."""
    texto = texto.strip().rstrip(".")
    if not texto:
        return "Não entendi o que salvar."
    memorias = load()
    # Evita duplicata exata
    if texto.lower() in [m.lower() for m in memorias]:
        return "Isso já estava na minha memória, senhor Ricarte."
    memorias.append(texto)
    _save(memorias)
    print(f"[NERO MEM] + '{texto}'")
    return f"Anotado. Vou lembrar que {texto}."


def remove(termo: str) -> str:
    """Remove memórias que contenham o termo. Retorna confirmação."""
    termo = termo.strip().rstrip(".").lower()
    if not termo:
        return "Não entendi o que apagar."
    memorias = load()
    antes = len(memorias)
    memorias = [m for m in memorias if termo not in m.lower()]
    removidas = antes - len(memorias)
    if removidas == 0:
        return f"Não encontrei nada sobre '{termo}' na minha memória."
    _save(memorias)
    print(f"[NERO MEM] - {removidas} item(ns) com '{termo}'")
    return f"Pronto. Removi {removidas} item(ns) relacionado(s) a '{termo}'."


def list_all() -> str:
    """Retorna todas as memórias formatadas como texto."""
    memorias = load()
    if not memorias:
        return (
            "Minha memória pessoal está vazia. "
            "Você pode me ensinar coisas dizendo, por exemplo: "
            "'lembra que João é meu sócio' ou 'aprende que bora significa vamos começar'."
        )
    linhas = "\n".join(f"• {m}" for m in memorias)
    return f"Aqui está o que tenho na memória:\n{linhas}"


# ── Injeção no system prompt ───────────────────────────────────────────────

def format_for_prompt() -> str:
    """Retorna bloco de memória para inserir no system prompt do Groq."""
    memorias = load()
    if not memorias:
        return ""
    linhas = "\n".join(f"- {m}" for m in memorias)
    return (
        "\n\n[MEMÓRIA PESSOAL DO SENHOR RICARTE]\n"
        + linhas
        + "\n[FIM DA MEMÓRIA PESSOAL]\n"
        "Use essas informações para personalizar suas respostas quando relevante."
    )


# ── Detecção e execução de comandos ───────────────────────────────────────

def handle_command(texto: str) -> str | None:
    """
    Verifica se o texto é um comando de memória.
    Retorna a resposta (string) se for um comando, ou None caso contrário.
    """
    texto_clean = texto.strip()

    # Listar (verificar antes de salvar, pois "o que você lembra" pode ter "lembra")
    if _LIST_RE.search(texto_clean):
        return list_all()

    # Salvar
    m = _ADD_RE.match(texto_clean)
    if m:
        conteudo = m.group(3).strip()
        return add(conteudo)

    # Apagar
    m = _DEL_RE.match(texto_clean)
    if m:
        conteudo = m.group(3).strip()
        return remove(conteudo)

    return None  # não é comando de memória
