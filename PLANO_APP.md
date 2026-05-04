# Plano — App Mobile do Nero

> **STATUS: IMPLEMENTADO** — O Nero foi disponibilizado como servidor web via `nero_api.py`
> (FastAPI + Uvicorn). A interface roda no PC e é acessível pelo celular via Wi-Fi local
> ou pela internet via ngrok. Não foi necessário criar um app nativo — uma PWA em
> `static/index.html` cobre todos os requisitos planejados.

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
- [x] Arquivo separado `nero_api.py` com FastAPI
- [x] `POST /comando` — recebe texto, retorna resposta do Nero
- [x] `GET /status` — verifica se o Nero está online
- [x] `POST /falar` — síntese de voz em PT e FR com Piper TTS
- [x] Autenticação por token (`X-API-Token`)
- [x] Busca web automática via `classify_and_query`
- [x] Memória pessoal via `nero_memoria.py`

### No celular (frontend)
- [x] PWA em `static/index.html` (sem Play Store)
- [x] Campo de texto e botão de microfone com reconhecimento de voz
- [x] Globo Three.js com estados visuais (idle/ouvindo/processando/buscando/falando)
- [x] TTS sincronizado com typewriter palavra a palavra
- [x] Toggle de modo PT/FR
- [x] Acesso via IP local ou ngrok (internet)

## Dependências novas
```
pip install fastapi uvicorn
```

## Limitações desta abordagem
- Celular e PC precisam estar na mesma rede Wi-Fi (ou usar ngrok para acesso externo)
- O PC precisa estar ligado e com o Nero rodando
- WhatsApp continua funcionando normalmente (roda no PC)
