"""
Nero — Assistente pessoal de voz.

Dependências:
    pip install SpeechRecognition PyAudio piper-tts pygame groq
    pip install selenium webdriver-manager python-dotenv
"""

import os
import re
import subprocess
import time
import wave

from dotenv import load_dotenv
load_dotenv()

import pygame
import speech_recognition as sr
from groq import Groq
from piper import PiperVoice
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


# configurações — edite aqui

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

EXIT_PHRASE          = "encerrar conversa"
SHUTDOWN_PHRASE      = "descansar agora paizao"
FRENCH_MODE_PHRASE   = "modo francês"
NORMAL_MODE_PHRASE   = "modo normal"
WHATSAPP_OPEN_PHRASE = "abrir whatsapp"

SHUTDOWN_DELAY = 10  # segundos antes de desligar o PC

# Perfil do Chrome pessoal — já tem WhatsApp Web logado
# IMPORTANTE: feche o Chrome antes de rodar o Nero
_CHROME_PROFILE_DIR  = r"C:\Users\m\AppData\Local\Google\Chrome\User Data"
_CHROME_PROFILE_NAME = "Default"  # mude para "Profile 1", "Profile 2" etc. se necessário


SYSTEM_PROMPTS = {
    "default": (
        "Você é Nero, assistente pessoal inteligente e educado do senhor Ricarte. "
        "Responda sempre em português brasileiro, de forma concisa e natural para ser falado em voz alta. "
        "Nunca use listas, markdown ou formatação especial — apenas texto corrido. "
        "IMPORTANTE: Você JAMAIS deve afirmar que enviou, está enviando ou enviará uma mensagem de WhatsApp. "
        "O envio é feito exclusivamente pelo sistema de automação, não por você. "
        "Se o senhor Ricarte pedir para enviar mensagem e o sistema não confirmar, diga apenas: "
        "'Não consegui processar o comando. Tente dizer: manda mensagem para nome dizendo sua mensagem.'"
    ),
    "french": (
        "Você é Nero no modo professor de francês do senhor Ricarte. "
        "Suas respostas devem misturar português e francês de forma natural e fluida, como uma transição suave entre os dois idiomas. "
        "Quando ele falar em português, responda em português mas inclua a frase equivalente em francês logo em seguida, pronunciada com naturalidade. "
        "Quando ele tentar falar em francês, responda misturando os dois idiomas — corrija gentilmente em português e reforce com o francês correto. "
        "Sempre encoraje, seja leve e natural. Nunca use listas ou formatação — apenas texto corrido para ser falado em voz alta. "
        "Exemplo de estilo: 'Muito bem! Em francês dizemos: bonjour, ça va? Que significa: olá, tudo bem?'"
    ),
}


_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_PIPER_MODEL_PT = os.path.join(_BASE_DIR, "pt_BR-faber-medium.onnx")
_PIPER_MODEL_FR = os.path.join(_BASE_DIR, "fr_FR-siwis-medium.onnx")
_TMP_WAV = os.path.join(_BASE_DIR, "_nero_tmp.wav")

_voice_pt = PiperVoice.load(_PIPER_MODEL_PT)
_voice_fr = PiperVoice.load(_PIPER_MODEL_FR) if os.path.exists(_PIPER_MODEL_FR) else None
_active_voice = _voice_pt

pygame.mixer.init()


def speak(text: str) -> None:
    print(f"[NERO] {text}")
    with wave.open(_TMP_WAV, "wb") as w:
        _active_voice.synthesize_wav(text, w)
    pygame.mixer.music.load(_TMP_WAV)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
    pygame.mixer.music.unload()


def normalize(text: str) -> str:
    return (
        text.lower()
        .strip()
        .replace(",", "")
        .replace(".", "")
        .replace("!", "")
        .replace("'", "")
    )


def listen(recognizer: sr.Recognizer, microphone: sr.Microphone, timeout: int = 5) -> str | None:
    try:
        with microphone as source:
            print("[NERO] Ouvindo...")
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=15)
        recognized = recognizer.recognize_google(audio, language="pt-BR")
        print(f"[NERO] Reconhecido: '{recognized}'")
        return recognized
    except (sr.WaitTimeoutError, sr.UnknownValueError):
        return None
    except sr.RequestError as e:
        print(f"[NERO] Erro no reconhecimento: {e}")
        return None


# padrão principal: com verbo
# ex: "manda uma mensagem para a minha mãe dizendo olá"
WHATSAPP_PATTERN = re.compile(
    r"(mandar?|enviar?|envie|falar?|escrever?)\s+"
    r"(uma\s+)?(mensagem\s+)?"
    r"(para|pro|pra|ao?)\s+"
    r"(a\s+|o\s+|minh[ao]\s+|meu\s+|a\s+minh[ao]\s+|o\s+meu\s+)?"
    r"(?P<contact>.+?)"
    r"(\s+dizendo\s+(?P<message>.+))?$",
    re.IGNORECASE,
)

# padrão secundário: sem verbo, cobre reconhecimento que corta o início da frase
# ex: "para a minha mãe dizendo olá"
WHATSAPP_DIZENDO_PATTERN = re.compile(
    r"^(para|pro|pra)\s+"
    r"(a\s+|o\s+|minh[ao]\s+|meu\s+|a\s+minh[ao]\s+|o\s+meu\s+)?"
    r"(?P<contact>.+?)\s+dizendo\s+(?P<message>.+)$",
    re.IGNORECASE,
)

_driver = None


def _whatsapp_is_ready(driver) -> bool:
    return bool(driver.execute_script("""
        return !!(
            document.querySelector('#pane-side') ||
            document.querySelector('[data-tab="3"]') ||
            document.querySelector('[role="searchbox"]')
        );
    """))


def _whatsapp_needs_qr(driver) -> bool:
    return bool(driver.execute_script("""
        return !!(
            document.querySelector('canvas') ||
            document.querySelector('[data-testid="qrcode"]')
        );
    """))


def get_driver() -> webdriver.Chrome:
    global _driver
    if _driver is None:
        options = Options()
        options.add_argument(f"--user-data-dir={_CHROME_PROFILE_DIR}")
        options.add_argument(f"--profile-directory={_CHROME_PROFILE_NAME}")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        _driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        _driver.get("https://web.whatsapp.com")

        print("[NERO] Verificando estado do WhatsApp Web...")
        try:
            WebDriverWait(_driver, 20).until(
                lambda d: _whatsapp_is_ready(d) or _whatsapp_needs_qr(d)
            )
        except Exception:
            pass

        if _whatsapp_needs_qr(_driver) and not _whatsapp_is_ready(_driver):
            print("[NERO] QR code detectado — aguardando autenticação...")
            speak("WhatsApp está pedindo autenticação. Por favor, escaneie o QR code na tela.")
            try:
                WebDriverWait(_driver, 180).until(_whatsapp_is_ready)
                speak("WhatsApp conectado com sucesso, senhor Ricarte.")
                print("[NERO] WhatsApp autenticado e pronto.")
            except Exception:
                speak("Não recebi confirmação de conexão. Verifique o WhatsApp manualmente.")
                print("[NERO] Timeout aguardando autenticação.")
        elif _whatsapp_is_ready(_driver):
            print("[NERO] WhatsApp Web carregado e pronto.")
        else:
            print("[NERO] Estado indeterminado — aguardando mais 10 segundos...")
            time.sleep(10)

    return _driver


def _js_find(driver, js_snippet: str):
    try:
        return driver.execute_script(js_snippet)
    except Exception:
        return None


def _find_element(driver, selectors: list, timeout: int = 15):
    for selector in selectors:
        try:
            return WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, selector))
            )
        except Exception:
            continue
    return None


def send_whatsapp_message(contact: str, message: str) -> bool:
    try:
        driver = get_driver()

        driver.switch_to.window(driver.current_window_handle)
        driver.maximize_window()
        driver.set_window_position(0, 0)

        if "web.whatsapp.com" not in driver.current_url:
            driver.get("https://web.whatsapp.com")

        if not _whatsapp_is_ready(driver):
            print("[NERO] WhatsApp não está pronto. Aguardando até 30 segundos...")
            try:
                WebDriverWait(driver, 30).until(_whatsapp_is_ready)
            except Exception:
                print("[NERO] Timeout — WhatsApp não carregou.")
                try:
                    driver.save_screenshot(os.path.join(_BASE_DIR, "_nero_debug.png"))
                    print("[NERO] Screenshot salvo para diagnóstico.")
                except Exception:
                    pass
                return False

        time.sleep(1)

        print(f"[NERO] Procurando contato: {contact}")
        search = _js_find(driver, """
            return document.querySelector('[data-tab="3"]') ||
                   document.querySelector('[role="searchbox"]') ||
                   document.querySelector('[title*="Pesquisar"]') ||
                   document.querySelector('[placeholder*="Pesquisar"]');
        """)

        if not search:
            print("[NERO] Caixa de pesquisa não encontrada.")
            return False

        driver.execute_script("arguments[0].click();", search)
        time.sleep(0.8)
        search.send_keys(Keys.CONTROL + "a")
        search.send_keys(Keys.DELETE)
        time.sleep(0.3)
        search.send_keys(contact)
        time.sleep(3)

        print("[NERO] Clicando no contato...")
        first = driver.execute_script("""
            var name = arguments[0].toLowerCase();
            var spans = document.querySelectorAll('span[title]');
            for (var s of spans) {
                if (s.title.toLowerCase().includes(name)) {
                    var el = s;
                    for (var i = 0; i < 10; i++) {
                        if (!el.parentElement) break;
                        el = el.parentElement;
                        if (el.getAttribute('role') === 'listitem') return el;
                    }
                    return s;
                }
            }
            var items = document.querySelectorAll('[role="listitem"]');
            for (var item of items) {
                if (item.offsetParent !== null) return item;
            }
            return null;
        """, contact)

        if not first:
            print("[NERO] Contato não encontrado.")
            return False

        ActionChains(driver).move_to_element(first).click().perform()
        time.sleep(2)

        print("[NERO] Aguardando caixa de mensagem...")
        msg_box = _js_find(driver, """
            return document.querySelector('[data-tab="10"][contenteditable]') ||
                   (() => {
                     for (let e of document.querySelectorAll('[contenteditable]')) {
                       let lbl = (e.getAttribute('aria-label') || '').toLowerCase();
                       if (lbl.includes('ensagem') || lbl.includes('essage')) return e;
                     }
                   })();
        """)

        if not msg_box:
            msg_box = _find_element(driver, [
                '//div[@contenteditable="true"][@data-tab="10"]',
                '//div[@aria-label="Digite uma mensagem"]',
                '//div[contains(@aria-label,"ensagem")][@contenteditable="true"]',
            ])

        if not msg_box:
            print("[NERO] Caixa de mensagem não encontrada.")
            return False

        driver.execute_script("arguments[0].click();", msg_box)
        time.sleep(0.5)
        msg_box.send_keys(message)
        time.sleep(1)
        msg_box.send_keys(Keys.ENTER)
        time.sleep(1)
        print("[NERO] Mensagem enviada!")
        return True

    except Exception as e:
        print(f"[NERO] Erro WhatsApp: {e}")
        return False


def detect_whatsapp_intent(text: str):
    match = WHATSAPP_PATTERN.search(text)
    if match:
        contact = match.group("contact").strip()
        message = match.group("message")
        return contact, (message.strip() if message else None)

    match = WHATSAPP_DIZENDO_PATTERN.match(text)
    if match:
        contact = match.group("contact").strip()
        message = match.group("message").strip()
        print(f"[NERO] Intenção detectada pelo padrão secundário: contato='{contact}', msg='{message}'")
        return contact, message

    return None, None


_groq = Groq(api_key=GROQ_API_KEY)
_MAX_HISTORY = 20  # equivale a 10 trocas


def ask_groq(message: str, mode: str, history: list) -> str:
    messages = (
        [{"role": "system", "content": SYSTEM_PROMPTS[mode]}]
        + history
        + [{"role": "user", "content": message}]
    )
    response = _groq.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
    )
    reply = response.choices[0].message.content
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})
    if len(history) > _MAX_HISTORY:
        del history[:-_MAX_HISTORY]
    return reply


def conversation_loop(recognizer: sr.Recognizer, microphone: sr.Microphone) -> None:
    global _active_voice
    speak("Modo conversa ativado. Como posso ajudá-lo, senhor Ricarte?")
    mode = "default"
    history = []

    while True:
        recognized = listen(recognizer, microphone, timeout=10)
        if recognized is None:
            continue

        normalized = normalize(recognized)

        if normalize(EXIT_PHRASE) in normalized:
            speak("Encerrando modo conversa. Até logo, senhor Ricarte.")
            break

        if normalize(SHUTDOWN_PHRASE) in normalized:
            speak("Claro, senhor. Encerrando todos os sistemas. Até logo.")
            if _driver:
                _driver.quit()
            shutdown_computer()
            break

        if normalize(FRENCH_MODE_PHRASE) in normalized:
            mode = "french"
            history = []
            if _voice_fr:
                _active_voice = _voice_fr
                speak("Modo français ativado! Bonjour monsieur Ricarte! Par où commençons-nous?")
            else:
                speak("Modo professor de francês ativado! Bonjour monsieur Ricarte! Por onde vamos começar?")
            continue

        if normalize(NORMAL_MODE_PHRASE) in normalized:
            mode = "default"
            history = []
            _active_voice = _voice_pt
            speak("De retour en mode normal. Estou pronto, senhor Ricarte.")
            continue

        if normalize(WHATSAPP_OPEN_PHRASE) in normalized:
            speak("Abrindo WhatsApp, senhor Ricarte. Aguarde um momento.")
            get_driver()
            speak("WhatsApp aberto. Pode me pedir para enviar mensagens.")
            continue

        contact, inline_message = detect_whatsapp_intent(recognized)
        if contact:
            if inline_message:
                message_text = inline_message
            else:
                speak(f"O que você quer dizer para {contact}?")
                message_text = None
                for _ in range(3):
                    message_text = listen(recognizer, microphone, timeout=15)
                    if message_text:
                        break
                    speak("Não ouvi a mensagem. Pode repetir?")

            if message_text:
                speak(f"Enviando mensagem para {contact}.")
                ok = send_whatsapp_message(contact, message_text)
                if ok:
                    speak("Mensagem enviada com sucesso, senhor Ricarte.")
                else:
                    speak("Não consegui enviar a mensagem. Verifique se o WhatsApp está aberto e o contato existe.")
            else:
                speak("Não consegui entender a mensagem. Tente novamente mais tarde.")
            continue

        try:
            response = ask_groq(recognized, mode, history)
            speak(response)
        except Exception as e:
            print(f"[NERO] Erro Groq: {e}")
            speak("Desculpe, tive um problema ao processar sua solicitação.")


def shutdown_computer() -> None:
    print(f"[NERO] Desligamento em {SHUTDOWN_DELAY} segundos...")
    subprocess.run(["shutdown", "/s", "/t", str(SHUTDOWN_DELAY)], check=True)


def main() -> None:
    print("=" * 50)
    print("  NERO — Assistente Pessoal")
    print(f"  Encerrar:   \"{EXIT_PHRASE}\"")
    print(f"  Desligar:   \"{SHUTDOWN_PHRASE}\"")
    print("=" * 50)

    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    print("[NERO] Calibrando ruído ambiente (2 segundos)...")
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
    print(f"[NERO] Threshold de energia: {recognizer.energy_threshold:.1f}")
    print("[NERO] Sistema pronto.\n")

    speak("Sistema iniciado. Estou pronto, senhor Ricarte.")
    conversation_loop(recognizer, microphone)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[NERO] Sistema encerrado pelo usuário.")
        if _driver:
            _driver.quit()
        pygame.mixer.quit()
