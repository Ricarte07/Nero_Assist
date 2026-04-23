# Plano — App Mobile do Nero 

O celular vira uma interface para o Nero. O assistente continua rodando no PC
(com WhatsApp, Selenium, Piper, tudo funcionando como hoje). O app só envia
comandos e recebe as respostas por rede local.

## Como vai funcionar

```
[Celular] ──── Wi-Fi local ────► [PC com Nero rodando]
   app envia texto/voz               FastAPI recebe, processa,
   recebe resposta em texto           devolve resposta do Groq
```

## O que precisa ser criado

### No PC (backend)
- Adicionar FastAPI ao `jarvis_wakeup.py` (ou arquivo separado `nero_api.py`)
- Expor dois endpoints:
  - `POST /comando` — recebe texto, retorna resposta do Nero
  - `GET /status` — verifica se o Nero está online
- Rodar junto com o Nero quando o app estiver ativo

### No celular (frontend)
- App simples em React Native (ou PWA se quiser evitar Play Store)
- Tela com campo de texto ou botão de microfone
- Conecta no IP local do PC (ex: 192.168.x.x:8000)
- Exibe a resposta do Nero em texto
- Opcional: TTS nativo do celular para falar a resposta

## Dependências novas
```
pip install fastapi uvicorn
```

## Limitações desta abordagem
- Celular e PC precisam estar na mesma rede Wi-Fi
- O PC precisa estar ligado e com o Nero rodando
- WhatsApp continua funcionando normalmente (roda no PC)
