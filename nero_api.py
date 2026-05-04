"""
Nero API — Interface web para o assistente pessoal.

Uso:
    pip install fastapi uvicorn
    python nero_api.py

Acesse no celular (mesmo Wi-Fi): http://SEU_IP_LOCAL:8000
"""

import asyncio
import io
import json
import os
import re
import socket
import wave as wave_module
from datetime import date

from duckduckgo_search import DDGS
from dotenv import load_dotenv
import nero_memoria
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from groq import AsyncGroq
from pydantic import BaseModel
import uvicorn

# Carrega .env usando caminho absoluto (evita problema ao rodar de outro diretório)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_BASE_DIR, ".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
API_TOKEN    = os.getenv("API_TOKEN", "")
groq = AsyncGroq(api_key=GROQ_API_KEY, timeout=30.0)

_CAPABILITIES = (
    " Suas capacidades são: "
    "(1) responder perguntas e conversar normalmente; "
    "(2) buscar informações atuais na internet automaticamente quando necessário (notícias, placar, cotações, clima, etc.); "
    "(3) enviar mensagens pelo WhatsApp — o senhor Ricarte diz 'manda mensagem para [nome] dizendo [mensagem]' e o sistema de automação envia; "
    "(4) memorizar informações pessoais com 'lembra que [info]'; "
    "(5) apagar memórias com 'esquece [info]'; "
    "(6) listar memórias com 'o que você sabe sobre mim'; "
    "(7) modo professor de francês — ative pelo botão FR na tela ou diga 'modo francês'; volte ao PT com 'modo normal'. "
    "Quando perguntado sobre o que você faz ou suas funcionalidades, apresente todas essas capacidades de forma natural."
)

SYSTEM_PROMPTS = {
    "default": (
        "Você é Nero, assistente pessoal inteligente e educado do senhor Ricarte. "
        "Responda sempre em português brasileiro, de forma concisa e natural para ser lido na tela. "
        "Nunca use listas, markdown ou formatação especial — apenas texto corrido. "
        "Quando resultados de busca na internet forem fornecidos no contexto entre [BUSCA WEB] e [FIM DA BUSCA], "
        "use essas informações para responder — elas são atuais e confiáveis. "
        "NUNCA diga que seus conhecimentos têm limite de data; se precisar de informação atual ela já estará no contexto. "
        "IMPORTANTE: Você JAMAIS deve afirmar que enviou, está enviando ou enviará uma mensagem de WhatsApp. "
        "O envio é feito exclusivamente pelo sistema de automação do PC, não por você. "
        "Se o senhor Ricarte pedir para enviar mensagem e o sistema não confirmar, diga apenas: "
        "'Não consegui processar o comando. Tente dizer: manda mensagem para nome dizendo sua mensagem.'"
        + _CAPABILITIES
    ),
    "french": (
        "Tu es Nero, professeur de français personnel et bienveillant du monsieur Ricarte. "
        "Parle TOUJOURS en français, même si l'utilisateur écrit en portugais ou dans une autre langue. "
        "Corrige poliment les fautes de français, donne des explications claires et encourageantes. "
        "Réponds de façon concise et naturelle pour être lu sur écran. "
        "N'utilise jamais de listes, de markdown ou de mise en forme spéciale — seulement du texte simple. "
        "Quand des résultats de recherche web sont fournis entre [BUSCA WEB] et [FIM DA BUSCA], "
        "utilise ces informations pour répondre — elles sont actuelles et fiables. "
        "Ne jamais dire que tes connaissances ont une date limite; si une information actuelle est nécessaire, elle sera déjà dans le contexte."
    ),
}

# Detecção de troca de modo no texto do usuário
_MODE_FRENCH_RE = re.compile(
    r"\b(modo franc[eê]s|professor de franc[eê]s|fala franc[eê]s|ativa.*franc[eê]s|modo fr)\b",
    re.IGNORECASE,
)
_MODE_DEFAULT_RE = re.compile(
    r"\b(modo normal|modo portugu[eê]s|volta.*normal|modo pt|modo padr[aã]o|desativa.*franc[eê]s)\b",
    re.IGNORECASE,
)

async def classify_and_query(message: str, today: str) -> tuple[bool, str]:
    """
    Decide em UMA chamada rápida (llama-3.1-8b-instant) se a mensagem precisa
    de busca na web e, se sim, retorna a query otimizada.
    Retorna (precisa_busca, query).
    """
    try:
        response = await groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Hoje é {today}. Analise a mensagem e decida se precisa de busca na internet.\n"
                        "PRECISA de busca: eventos recentes, resultados esportivos, cotações de moeda/cripto, "
                        "clima/temperatura, notícias, preços de mercado, eleições, lançamentos, "
                        "qualquer informação que mude com o tempo.\n"
                        "NÃO precisa: conversas, perguntas gerais, definições, história, ciência, "
                        "matemática, comandos ao assistente, memória pessoal, opiniões.\n\n"
                        "Responda EXATAMENTE assim:\n"
                        "- Se NÃO precisar: responda apenas 'NO'\n"
                        "- Se precisar: responda apenas a query de busca em português, sem explicações\n"
                        "Exemplos:\n"
                        "Mensagem: oi tudo bem? → NO\n"
                        "Mensagem: resultado do Fortaleza ontem → Fortaleza resultado jogo ontem\n"
                        "Mensagem: cotação do dólar agora → cotação dólar hoje\n"
                        "Mensagem: quanto é 2+2 → NO\n"
                        "Mensagem: previsão do tempo Fortaleza → previsão do tempo Fortaleza hoje"
                    )
                },
                {"role": "user", "content": message}
            ],
            max_tokens=25,
            temperature=0,
        )
        result = response.choices[0].message.content.strip()
        if not result or result.upper() == "NO":
            return False, ""
        print(f"[NERO API] Busca detectada, query: '{result}'")
        return True, result
    except Exception as e:
        print(f"[NERO API] classify_and_query falhou ({e}), sem busca.")
        return False, ""


def _search_web_sync(query: str, max_results: int = 3) -> str:
    """Executa a busca de forma síncrona (chamado via asyncio.to_thread)."""
    print(f"[NERO API] Buscando na web: '{query}'")

    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)
            response = client.search(query=query, max_results=max_results)
            results = response.get("results", [])
            if results:
                parts = [f"{r['title']}: {r['content']}" for r in results]
                print(f"[NERO API] Tavily: {len(results)} resultado(s)")
                return "\n\n".join(parts)
        except Exception as e:
            print(f"[NERO API] Tavily falhou, tentando DuckDuckGo: {e}")

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "Nenhum resultado encontrado para essa busca."
        parts = [f"{r['title']}: {r['body']}" for r in results]
        print(f"[NERO API] DuckDuckGo: {len(results)} resultado(s)")
        return "\n\n".join(parts)
    except Exception as e:
        return f"Erro na busca: {e}"


async def search_web(query: str) -> str:
    """Roda a busca em thread separada com timeout de 7 segundos."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_search_web_sync, query),
            timeout=7.0,
        )
    except asyncio.TimeoutError:
        print("[NERO API] Busca expirou após 7s.")
        return "A busca demorou demais. Responda com o que sabe."


# ── Histórico persistente ──────────────────────────────────────────────────
_HISTORY_FILE = os.path.join(_BASE_DIR, "nero_history.json")
MAX_HISTORY   = 20


def load_history() -> list:
    try:
        with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"[NERO API] Histórico carregado: {len(data) // 2} trocas anteriores.")
            return data
    except Exception:
        return []


def save_history(hist: list) -> None:
    try:
        with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(hist[-MAX_HISTORY:], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[NERO API] Erro ao salvar histórico: {e}")


history: list[dict] = load_history()

# ── Piper TTS ──────────────────────────────────────────────────────────────
_PIPER_MODEL_PT = os.path.join(_BASE_DIR, "pt_BR-faber-medium.onnx")
_PIPER_MODEL_FR = os.path.join(_BASE_DIR, "fr_FR-siwis-medium.onnx")
_voice_pt       = None  # carregado na primeira chamada a /falar
_voice_fr       = None  # carregado na primeira chamada em modo francês

# ── FastAPI ────────────────────────────────────────────────────────────────
app = FastAPI(title="N.E.R.O API", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_token(request: Request):
    if not API_TOKEN:
        return
    token = request.headers.get("X-API-Token", "")
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")


class Comando(BaseModel):
    texto: str
    modo: str = "default"


@app.get("/")
def root():
    return FileResponse(os.path.join(_BASE_DIR, "static", "index.html"))


@app.get("/status")
def status():
    return {"online": True}


@app.post("/comando")
async def comando(cmd: Comando, _=Depends(require_token)):
    global history
    today = date.today().strftime("%d/%m/%Y")

    # Detecta troca de modo pelo texto (sobrescreve o modo enviado pelo frontend)
    modo = cmd.modo
    if _MODE_FRENCH_RE.search(cmd.texto):
        modo = "french"
    elif _MODE_DEFAULT_RE.search(cmd.texto):
        modo = "default"

    system_base = SYSTEM_PROMPTS.get(modo, SYSTEM_PROMPTS["default"])
    system = system_base + nero_memoria.format_for_prompt() + f" A data de hoje é {today}."
    print(f"[NERO API] Modo: {modo}")

    # Verifica se é um comando de memória — responde direto sem chamar o Groq
    mem_reply = nero_memoria.handle_command(cmd.texto)
    if mem_reply is not None:
        return {"resposta": mem_reply, "modo": modo}

    user_content = cmd.texto
    needs_search, search_query = await classify_and_query(cmd.texto, today)
    if needs_search:
        web_results = await search_web(search_query)
        user_content = (
            f"{cmd.texto}\n\n"
            f"[BUSCA WEB]\n{web_results}\n[FIM DA BUSCA]"
        )

    messages = (
        [{"role": "system", "content": system}]
        + history
        + [{"role": "user", "content": user_content}]
    )

    try:
        response = await groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
        )
        reply = response.choices[0].message.content
        history.append({"role": "user",      "content": cmd.texto})
        history.append({"role": "assistant", "content": reply})
        history = history[-MAX_HISTORY:]
        save_history(history)
        return {"resposta": reply, "modo": modo}
    except Exception as e:
        print(f"[NERO API] Erro Groq: {e}")
        return {"resposta": "Desculpe, tive um problema ao processar sua solicitação. Tente novamente.", "modo": modo}


@app.post("/falar")
async def falar(cmd: Comando, _=Depends(require_token)):
    global _voice_pt, _voice_fr
    try:
        from piper import PiperVoice
        if cmd.modo == "french":
            if not os.path.exists(_PIPER_MODEL_FR):
                raise HTTPException(status_code=503, detail="Modelo de voz francesa não encontrado. Baixe fr_FR-siwis-medium.onnx.")
            if _voice_fr is None:
                _voice_fr = PiperVoice.load(_PIPER_MODEL_FR)
            voice = _voice_fr
        else:
            if _voice_pt is None:
                _voice_pt = PiperVoice.load(_PIPER_MODEL_PT)
            voice = _voice_pt
        buf = io.BytesIO()
        with wave_module.open(buf, "wb") as w:
            voice.synthesize_wav(cmd.texto, w)
        buf.seek(0)
        return StreamingResponse(buf, media_type="audio/wav")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[NERO API] Erro TTS: {e}")
        raise HTTPException(status_code=503, detail="TTS indisponível")


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return socket.gethostbyname(socket.gethostname())


if __name__ == "__main__":
    ip = get_local_ip()
    print("=" * 52)
    print("  N.E.R.O — Interface Web Iniciando...")
    print(f"  Celular (mesmo Wi-Fi): http://{ip}:8000")
    print(f"  Neste PC:              http://localhost:8000")
    print("=" * 52)
    uvicorn.run(app, host="0.0.0.0", port=8000)
