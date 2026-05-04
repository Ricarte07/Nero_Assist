# N.E.R.O — Documentação do Projeto
**Neural Enhanced Response Operator**
Assistente pessoal inteligente do senhor Ricarte, inspirado no Jarvis do Homem de Ferro.

---

## Índice
1. [Visão Geral do Projeto](#visão-geral)
2. [Estrutura de Arquivos](#estrutura-de-arquivos)
3. [Configuração (.env)](#configuração-env)
4. [nero.py — Assistente de Voz](#neropy)
5. [nero_api.py — Interface Web](#nero_apipy)
6. [nero_memoria.py — Memória Pessoal](#nero_memoriapy)
7. [static/index.html — Frontend](#staticindexhtml)
8. [iniciar_nero.bat — Atalho de Inicialização](#iniciar_nerobat)
9. [Arquivos de Dados](#arquivos-de-dados)
10. [Fluxo Completo de uma Conversa](#fluxo-completo)
11. [Dependências e Instalação](#dependências-e-instalação)
12. [Como Usar o Nero](#como-usar-o-nero)

---

## Visão Geral

O Nero tem **dois modos de uso** que funcionam de forma independente:

| Modo | Arquivo | Como abrir | Uso |
|------|---------|------------|-----|
| **Voz (desktop)** | `nero.py` | `python nero.py` | Fala diretamente com o microfone no PC |
| **Web (celular/navegador)** | `nero_api.py` | `iniciar_nero.bat` | Acessa pelo celular, 4G, ou qualquer navegador |

Ambos compartilham o mesmo módulo de memória (`nero_memoria.py`) e o mesmo arquivo de dados (`nero_memoria.json`).

---

## Estrutura de Arquivos

```
projeto jarvis/
│
├── nero.py                  ← Assistente de voz (roda no PC com microfone)
├── nero_api.py              ← Servidor web FastAPI (acesso pelo celular)
├── nero_memoria.py          ← Módulo de memória pessoal (compartilhado)
│
├── static/
│   └── index.html           ← Interface visual holográfica (frontend)
│
├── iniciar_nero.bat         ← Abre nero_api.py + ngrok com duplo clique
├── ngrok.exe                ← Tunnel para acesso externo (fora de casa)
│
├── .env                     ← Chaves secretas (NUNCA compartilhar)
├── nero_history.json        ← Histórico de conversas (gerado automaticamente)
├── nero_memoria.json        ← Memórias salvas (gerado automaticamente)
│
├── pt_BR-faber-medium.onnx  ← Modelo de voz em português (Piper TTS)
├── fr_FR-siwis-medium.onnx  ← Modelo de voz em francês (Piper TTS)
│
└── DOCUMENTACAO.md          ← Este arquivo
```

---

## Configuração (.env)

Arquivo de texto simples que guarda as chaves secretas. Nunca deve ser compartilhado.

```
GROQ_API_KEY=gsk_...         ← Chave da API Groq (inteligência do Nero)
TAVILY_API_KEY=tvly-...      ← Chave da API Tavily (busca na internet)
API_TOKEN=sua_senha_aqui     ← Senha de acesso à interface web
NGROK_TOKEN=...              ← Token do ngrok (acesso externo)
NGROK_DOMAIN=...             ← Domínio estático ngrok (ex: cartel-dodge.ngrok-free.app)
```

---

## nero.py

**O quê faz:** É o assistente de voz que roda direto no computador. Você fala com o microfone e ele responde em voz alta pelos alto-falantes. Tem integração com WhatsApp Web via automação do navegador.

**Como rodar:** `python nero.py`

---

### Imports do nero.py

#### Biblioteca padrão do Python (já vem instalada, não precisa instalar)

```python
import os
```
Acessa variáveis de ambiente e caminhos de arquivo. Usado para encontrar os arquivos `.onnx` de voz e o `.env`.

```python
import re
```
Expressões regulares. Usado para detectar padrões de fala como "manda mensagem para João dizendo olá" ou "modo francês".

```python
import subprocess
```
Executa comandos do sistema operacional. Usado na função `shutdown_computer()` para desligar o PC com o comando `shutdown /s /t 10`.

```python
import time
```
Controle de tempo. Usado para pausas (`time.sleep()`) enquanto espera o WhatsApp carregar ou o áudio terminar de tocar.

```python
import wave
```
Leitura e escrita de arquivos de áudio `.wav`. Usado para salvar o áudio gerado pelo Piper TTS em um arquivo temporário antes de tocar.

```python
from datetime import date
```
Obtém a data atual. Usado para informar ao modelo de IA qual é o dia de hoje, para ele contextualizar respostas sobre eventos recentes.

#### Dependências externas (precisam ser instaladas com pip)

```python
from duckduckgo_search import DDGS
```
**Pacote:** `duckduckgo-search`
Faz buscas no DuckDuckGo sem precisar de API key. É o mecanismo de busca secundário (fallback), usado quando a Tavily não está disponível ou falha.

```python
from dotenv import load_dotenv
load_dotenv()
```
**Pacote:** `python-dotenv`
Lê o arquivo `.env` e carrega as variáveis de ambiente (GROQ_API_KEY, etc.) para que o Python possa acessá-las com `os.getenv()`.

```python
import nero_memoria
```
Módulo local criado para o projeto. Cuida de salvar, apagar e listar as memórias pessoais do senhor Ricarte. Explicado em detalhes na seção própria.

```python
import pygame
```
**Pacote:** `pygame`
Biblioteca de áudio e jogos. Aqui é usada exclusivamente para tocar o arquivo `.wav` gerado pelo Piper TTS. O `pygame.mixer` consegue tocar áudio e aguardar o fim da reprodução.

```python
import speech_recognition as sr
```
**Pacote:** `SpeechRecognition`
Captura o áudio do microfone e converte em texto usando o Google Speech Recognition (serviço gratuito do Google). Retorna a frase que você falou como uma string Python.

```python
from groq import Groq
```
**Pacote:** `groq`
Cliente da API Groq. No `nero.py` é a versão **síncrona** (bloqueia o código enquanto espera resposta). Envia o histórico da conversa e o system prompt para o modelo de IA e retorna a resposta em texto.

```python
from piper import PiperVoice
```
**Pacote:** `piper-tts`
Motor de síntese de voz (Text-to-Speech) local. Converte texto em áudio `.wav` usando os modelos `.onnx` instalados na pasta. Funciona offline, sem internet.

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
```
**Pacote:** `selenium`
Controla o navegador Chrome automaticamente. É o que faz o Nero enviar mensagens pelo WhatsApp Web. Cada import serve para:
- `webdriver` → abre e controla o Chrome
- `Options` → configura o Chrome (usa o perfil pessoal com WhatsApp já logado)
- `Service` → gerencia o processo do ChromeDriver
- `ActionChains` → simula ações do mouse (mover, clicar em elementos)
- `By` → define como procurar elementos na página (por XPath, CSS, etc.)
- `Keys` → simula teclas especiais como ENTER
- `EC` (expected_conditions) → condições de espera (ex: "aguarde até o elemento ser clicável")
- `WebDriverWait` → aguarda até que uma condição seja verdadeira (evita erros de timing)

```python
from webdriver_manager.chrome import ChromeDriverManager
```
**Pacote:** `webdriver-manager`
Baixa e instala automaticamente a versão correta do ChromeDriver compatível com o Chrome instalado no PC. Elimina a necessidade de baixar o driver manualmente.

---

### Constantes e Configurações

```python
EXIT_PHRASE          = "encerrar conversa"
SHUTDOWN_PHRASE      = "descansar agora paizao"
FRENCH_MODE_PHRASE   = "modo francês"
NORMAL_MODE_PHRASE   = "modo normal"
WHATSAPP_OPEN_PHRASE = "abrir whatsapp"
```
Frases especiais que ativam comandos do sistema. Quando o Nero reconhece qualquer uma dessas falas, ele executa a ação correspondente sem consultar a IA.

```python
SHUTDOWN_DELAY = 10  # segundos antes de desligar o PC
```
Tempo de espera antes do desligamento, dando tempo para cancelar se necessário.

```python
_CHROME_PROFILE_DIR  = r"C:\Users\m\AppData\Local\Google\Chrome\User Data"
_CHROME_PROFILE_NAME = "Default"
```
Caminho para o perfil do Chrome pessoal, onde o WhatsApp Web já está logado. O Selenium usa esse perfil para não precisar escanear o QR code toda vez.

---

### Funções Principais do nero.py

#### `classify_and_query(message, today)` → `(bool, str)`
Envia a mensagem para o modelo rápido `llama-3.1-8b-instant` e recebe em retorno:
- `False, ""` → não precisa de busca, é uma conversa normal
- `True, "query otimizada"` → precisa buscar na internet, retorna a query pronta para pesquisar

Substitui o antigo sistema de palavras-chave (que errava muito) por inteligência real.

#### `search_web(query)` → `str`
Tenta buscar com Tavily primeiro (mais precisa, especialmente para esportes e notícias). Se falhar, cai para DuckDuckGo. Retorna os resultados como texto formatado. Tem timeout de 7 segundos no `nero_api.py` (no `nero.py` a versão é síncrona sem timeout).

#### `speak(text)` → `None`
Converte texto em voz usando o modelo Piper ativo (`_active_voice`). Salva em `_nero_tmp.wav` e toca com pygame. Bloqueia o código até terminar de falar.

#### `listen(recognizer, microphone, timeout)` → `str | None`
Captura áudio do microfone por até `timeout` segundos e converte para texto com Google Speech. Retorna `None` se ninguém falou ou não entendeu.

#### `normalize(text)` → `str`
Deixa o texto em minúsculas e remove pontuação (vírgulas, pontos, exclamações). Usado para comparar frases sem se preocupar com capitalização ou pontuação do reconhecimento de voz.

#### `get_driver()` → `webdriver.Chrome`
Abre o Chrome com o perfil pessoal e navega para o WhatsApp Web. Se o WhatsApp pedir QR code, avisa por voz e aguarda. Mantém o driver na variável `_driver` para reutilizar na sessão.

#### `send_whatsapp_message(contact, message)` → `bool`
Executa toda a automação do WhatsApp: abre o buscador de contatos, digita o nome, clica no contato, digita a mensagem usando `document.execCommand('insertText')` (necessário para acentos funcionarem) e pressiona ENTER. Retorna `True` se enviou com sucesso.

#### `ask_groq(message, mode, history)` → `str`
Monta o conjunto de mensagens (system prompt + memória + histórico + pergunta atual), detecta se precisa de busca, e envia para o `llama-3.3-70b-versatile`. Salva a troca no histórico.

#### `conversation_loop(recognizer, microphone)` → `None`
O laço principal do assistente de voz. Fica em loop infinito: ouve → analisa o que foi dito → executa a ação correspondente (sair, desligar, mudar modo, WhatsApp, memória, ou resposta da IA).

---

## nero_api.py

**O quê faz:** Cria um servidor web usando FastAPI que expõe o Nero como uma API HTTP. O `index.html` (interface visual) faz chamadas para esse servidor. Permite acesso pelo celular, por outros dispositivos na mesma rede Wi-Fi, e via ngrok de qualquer lugar com internet.

**Como rodar:** `python nero_api.py` (ou via `iniciar_nero.bat`)
**Porta padrão:** 8000

---

### Imports do nero_api.py

#### Biblioteca padrão

```python
import asyncio
```
Sistema de programação assíncrona do Python. Permite que o servidor atenda múltiplas requisições ao mesmo tempo sem travar. Usado em `asyncio.to_thread()` para rodar buscas web (que são operações lentas e bloqueantes) em paralelo sem congelar o servidor, e `asyncio.wait_for()` para impor timeout nas buscas.

```python
import io
```
Cria arquivos na memória RAM (sem gravar no disco). Usado para gerar o áudio WAV do Piper TTS diretamente em memória antes de enviar para o navegador.

```python
import json
```
Lê e escreve arquivos no formato JSON. Usado para salvar e carregar o histórico de conversas (`nero_history.json`).

```python
import os
```
Acessa variáveis de ambiente e manipula caminhos de arquivo.

```python
import re
```
Expressões regulares. Usado para detectar comandos de troca de modo ("modo francês", "modo normal") no texto enviado pelo usuário.

```python
import socket
```
Comunicação de rede. Usado pela função `get_local_ip()` para descobrir qual é o IP do computador na rede Wi-Fi local, e exibir no terminal para facilitar o acesso pelo celular.

```python
import wave as wave_module
```
Escrita de arquivos de áudio `.wav`. Usado com o Piper TTS para sintetizar o áudio em memória. Importado com alias `wave_module` para não conflitar com o módulo `wave` que já existe no Python padrão.

```python
from datetime import date
```
Data atual. Injetada no system prompt para que o Nero saiba que dia é hoje.

#### Dependências externas

```python
from duckduckgo_search import DDGS
```
Busca no DuckDuckGo como fallback quando a Tavily falha.

```python
from dotenv import load_dotenv
```
Carrega as variáveis do arquivo `.env`.

```python
import nero_memoria
```
Módulo local de memória pessoal.

```python
from fastapi import Depends, FastAPI, HTTPException, Request
```
**Pacote:** `fastapi`
O framework web que cria o servidor. Cada import:
- `FastAPI` → cria a aplicação principal
- `Request` → representa uma requisição HTTP recebida (usado para ler o cabeçalho com o token)
- `HTTPException` → lança erros HTTP (ex: 401 para token inválido, 503 para TTS indisponível)
- `Depends` → sistema de dependências do FastAPI; usado para aplicar a verificação de token em cada rota protegida

```python
from fastapi.middleware.cors import CORSMiddleware
```
Middleware de CORS (Cross-Origin Resource Sharing). Permite que o `index.html` aberto no navegador do celular faça requisições para o servidor, mesmo estando em origens diferentes. Sem isso, o navegador bloquearia as chamadas por segurança.

```python
from fastapi.responses import FileResponse, StreamingResponse
```
Tipos de resposta HTTP:
- `FileResponse` → envia um arquivo do disco (usado para servir o `index.html`)
- `StreamingResponse` → envia dados em stream (usado para enviar o áudio WAV gerado pelo Piper sem salvar em disco)

```python
from groq import AsyncGroq
```
**Pacote:** `groq`
Cliente **assíncrono** da API Groq (diferente do `nero.py` que usa o `Groq` síncrono). O `AsyncGroq` é obrigatório em aplicações FastAPI para não bloquear o servidor enquanto espera a resposta da IA.

```python
from pydantic import BaseModel
```
**Pacote:** `pydantic`
Define a estrutura dos dados recebidos nas requisições. O `Comando` herda de `BaseModel` e garante que qualquer requisição POST para `/comando` contenha os campos corretos (`texto` e `modo`). Se faltar algo, o FastAPI retorna erro automaticamente.

```python
import uvicorn
```
**Pacote:** `uvicorn`
O servidor ASGI que roda a aplicação FastAPI. É ele quem realmente escuta as conexões na porta 8000 e repassa para o FastAPI processar.

---

### Rotas (Endpoints) do nero_api.py

#### `GET /`
Serve o arquivo `static/index.html` — a interface visual do Nero.

#### `GET /status`
Retorna `{"online": true}`. Usado pelo frontend para verificar se o servidor está rodando e atualizar o ponto verde/vermelho no canto superior esquerdo.

#### `POST /comando`
A rota principal. Recebe `{"texto": "...", "modo": "default"}` e retorna `{"resposta": "...", "modo": "..."}`.

**Fluxo interno:**
1. Detecta se o usuário quer trocar de modo ("modo francês" → muda para `"french"`)
2. Monta o system prompt com o modo correto + memórias pessoais + data de hoje
3. Verifica se é um comando de memória → se sim, responde direto sem chamar a IA
4. Chama `classify_and_query()` com o modelo rápido para decidir se precisa buscar na web
5. Se precisar, busca com Tavily/DuckDuckGo e injeta os resultados na mensagem
6. Envia tudo para o `llama-3.3-70b-versatile` e retorna a resposta
7. Salva a troca no histórico

#### `POST /falar`
Converte texto em áudio. Recebe `{"texto": "...", "modo": "default"}` e retorna um arquivo WAV em streaming.
- `modo == "french"` → carrega e usa `fr_FR-siwis-medium.onnx`
- `modo == "default"` → carrega e usa `pt_BR-faber-medium.onnx`

Os modelos de voz são carregados na primeira chamada (lazy loading) e ficam em memória para as chamadas seguintes.

---

### Segurança

```python
def require_token(request: Request):
    if not API_TOKEN:
        return
    token = request.headers.get("X-API-Token", "")
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")
```
Verifica o cabeçalho `X-API-Token` em cada requisição. Se o `API_TOKEN` não estiver configurado no `.env`, a verificação é pulada (modo sem senha). Se estiver configurado e o token não bater, retorna erro 401.

---

## nero_memoria.py

**O quê faz:** Módulo compartilhado que gerencia a memória pessoal do Nero. É importado tanto pelo `nero.py` quanto pelo `nero_api.py`. Salva tudo em `nero_memoria.json`.

---

### Imports do nero_memoria.py

```python
import json
```
Lê e escreve o arquivo `nero_memoria.json` onde as memórias ficam armazenadas.

```python
import os
```
Monta o caminho absoluto do arquivo de memória, garantindo que ele seja sempre encontrado independentemente de onde o script for executado.

```python
import re
```
Define os padrões de detecção de comandos de memória:
- `_ADD_RE` → detecta "lembra que X", "aprende que X", "anota que X", etc.
- `_DEL_RE` → detecta "esquece X", "apaga da memória X", "remove X"
- `_LIST_RE` → detecta "o que você sabe sobre mim", "lista sua memória", etc.

---

### Funções do nero_memoria.py

#### `load()` → `list[str]`
Lê o `nero_memoria.json` e retorna a lista de memórias. Se o arquivo não existir, retorna lista vazia.

#### `add(texto)` → `str`
Adiciona uma nova memória à lista, evitando duplicatas. Salva no arquivo e retorna mensagem de confirmação para o usuário.

#### `remove(termo)` → `str`
Remove todas as memórias que contenham o termo pesquisado (busca parcial). Retorna quantos itens foram removidos.

#### `list_all()` → `str`
Retorna todas as memórias formatadas como texto legível para o usuário.

#### `format_for_prompt()` → `str`
Retorna um bloco de texto para ser inserido no system prompt do Groq. Exemplo do que é inserido:
```
[MEMÓRIA PESSOAL DO SENHOR RICARTE]
- João é meu sócio e mora em Fortaleza
- quando eu digo bora significa que quero começar logo
[FIM DA MEMÓRIA PESSOAL]
Use essas informações para personalizar suas respostas quando relevante.
```

#### `handle_command(texto)` → `str | None`
Ponto de entrada principal. Analisa o texto e decide se é um comando de memória. Retorna a resposta se for, ou `None` se não for — nesse caso o código que chamou sabe que deve continuar para a IA.

---

## static/index.html

**O quê faz:** A interface visual do Nero no navegador. Arquivo HTML único que contém todo o visual holográfico, a lógica de comunicação com o servidor, e o sistema de áudio. Não depende de frameworks externos (exceto Three.js para o globo 3D).

---

### Bibliotecas JavaScript utilizadas

```html
<link href="https://fonts.googleapis.com/css2?family=Orbitron...">
```
**Google Fonts** — carrega as fontes `Orbitron` (títulos futuristas) e `Share Tech Mono` (texto monospace do terminal).

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js">
```
**Three.js** — biblioteca 3D para o navegador. Cria o globo holográfico animado (esferas, anéis orbitais, partículas, iluminação interna). Usa WebGL por baixo.

---

### Estrutura CSS principal

| Elemento | Função |
|----------|--------|
| `body::before` | Sobreposição de scanlines (linhas horizontais finas que dão efeito de monitor antigo) |
| `body::after` | Barra de scan que desce a tela em loop (efeito holográfico) |
| `.grid-bg` | Grade de linhas ciano finas no fundo |
| `.corner` | Os quatro cantos decorativos da tela |
| `.telemetry` | Painéis laterais com dados falsos (CPU, memória, latência) |
| `#center-block` | Container flexível que centraliza o globo + título + respostas |
| `#globe-wrap` | Container do globo com os anéis de pulso |
| `#sound-wave` | 7 barras animadas que aparecem quando o Nero está falando |
| `#response-box` | Caixa de texto onde as respostas aparecem |
| `#input-area` | Barra de entrada com campo de texto e botões |

---

### Lógica JavaScript — seções principais

#### Globe (Three.js)
Cria e anima o globo holográfico 3D. Componentes:
- Camadas de atmosfera (halos externos semitransparentes)
- Brilho interno volumétrico
- Esfera sólida (núcleo)
- Wireframe esférico (grade)
- 3 anéis orbitais que giram em eixos diferentes
- 280 partículas distribuídas ao redor
- Luz pontual interna que pulsa

A cor de todos os materiais muda suavemente (`lerp`) conforme o estado do Nero.

#### `_setGlobeState(state)`
Controla o visual do globo conforme o estado atual:

| Estado | Cor | Animação | Label |
|--------|-----|----------|-------|
| `idle` | Ciano | Rotação lenta | AGUARDANDO COMANDO |
| `listening` | Laranja | Pulso + anéis | ESCUTANDO... |
| `processing` | Verde | Rotação média | PROCESSANDO... |
| `searching` | Verde | Pulso rápido | BUSCANDO NA WEB... |
| `speaking` | Branco | Rotação média + barras de som | FALANDO... |

#### Token de Acesso
O token é salvo no `localStorage` do navegador na primeira vez que o usuário digita. Nas visitas seguintes, é lido automaticamente. Se o servidor retornar 401 (token inválido), o modal de senha aparece novamente.

#### Modo PT/FR
O botão `PT`/`FR` no canto da barra de entrada alterna entre modo padrão (português) e modo professor de francês. O modo é salvo no `localStorage` para persistir entre sessões. Muda:
- Cor do botão (ciano → dourado)
- Idioma do reconhecimento de voz (pt-BR → fr-FR)
- Placeholder do campo de texto
- O campo `modo` enviado nas requisições

#### `typeWrite(text, totalMs)`
Exibe o texto da resposta **palavra por palavra**, sincronizado com a duração do áudio:
- Com áudio: divide a duração total do arquivo WAV pelo número de tokens (palavras + espaços) para calcular o intervalo entre cada palavra
- Sem áudio (voz desligada): usa 110ms por token como velocidade padrão

#### `sendCommand(texto)`
Função principal do frontend. Fluxo:
1. Muda estado do globo para `processing`
2. Aguarda 2,5 segundos e muda para `searching` se não houver resposta ainda
3. Chama `POST /comando` com o texto e o modo atual
4. Se a resposta tiver `modo` diferente do atual, atualiza o botão PT/FR
5. Se voz estiver habilitada, chama `POST /falar` para obter o áudio
6. Sincroniza o typewriter com a duração do áudio e toca os dois juntos
7. Quando o áudio termina, volta para `idle`

#### Speech Recognition
Usa a Web Speech API nativa do navegador (Chrome):
- `continuous: true` — não para sozinho na primeira pausa
- `interimResults: true` — mostra as palavras em tempo real no campo de texto
- Timer de silêncio de **1,8 segundos** — só envia quando detecta pausa de 1,8s sem novas palavras
- Clique no microfone para parar manualmente (envia imediatamente o que foi captado)

---

## iniciar_nero.bat

**O quê faz:** Script Windows que facilita a inicialização do servidor web + ngrok com um duplo clique.

**Fluxo:**
1. Lê o arquivo `.env` e extrai `NGROK_TOKEN` e `NGROK_DOMAIN`
2. Configura o ngrok com o token de autenticação
3. Abre um terminal com `nero_api.py` rodando
4. Aguarda 3 segundos para o servidor subir
5. Abre outro terminal com o ngrok criando o tunnel para o domínio estático

**Por que lê o `.env` manualmente?**
O `.env` é formato Python (lido pelo `python-dotenv`), não é o mesmo que variáveis de ambiente do Windows. O `.bat` usa um loop `for /f` para parsear o arquivo linha por linha e extrair os valores.

---

## Arquivos de Dados

### nero_history.json
Gerado automaticamente. Armazena as últimas 20 mensagens da conversa (10 trocas) para que o Nero lembre o contexto da conversa atual. Formato:
```json
[
  {"role": "user", "content": "qual o resultado do jogo?"},
  {"role": "assistant", "content": "O Fortaleza venceu por 2 a 1..."}
]
```

### nero_memoria.json
Gerado automaticamente quando você ensina algo ao Nero. Armazena as memórias pessoais permanentes. Formato:
```json
{
  "memorias": [
    "João é meu sócio e mora em Fortaleza",
    "quando eu digo bora significa que quero começar logo"
  ]
}
```

### pt_BR-faber-medium.onnx / fr_FR-siwis-medium.onnx
Modelos de síntese de voz do Piper TTS. Arquivos binários grandes (~60MB cada). Funcionam **offline**, sem internet. O `.onnx` é o formato de rede neural do framework ONNX Runtime, que o Piper usa internamente para gerar o áudio.

---

## Fluxo Completo de uma Conversa

### Via Interface Web (nero_api.py + index.html)

```
Usuário digita ou fala no celular
        ↓
[Frontend] sendCommand() — envia POST /comando
        ↓
[nero_api.py] Verifica token de acesso
        ↓
[nero_api.py] Detecta mudança de modo? (modo francês / modo normal)
        ↓
[nero_api.py] É comando de memória? (lembra que / esquece / lista)
    → Sim: responde direto, sem IA
    → Não: continua ↓
        ↓
[nero_api.py] classify_and_query() — llama-3.1-8b-instant decide:
    → Conversa normal: segue sem busca
    → Precisa de info atual: gera query e busca na web
        ↓
[Tavily / DuckDuckGo] Retorna resultados (se precisou buscar)
        ↓
[nero_api.py] Monta mensagens: system + memórias + histórico + pergunta
        ↓
[Groq API] llama-3.3-70b-versatile gera a resposta
        ↓
[nero_api.py] Salva no histórico, retorna {"resposta": "...", "modo": "..."}
        ↓
[Frontend] Recebe resposta → chama POST /falar
        ↓
[nero_api.py] Piper TTS converte texto em WAV e devolve em streaming
        ↓
[Frontend] Toca o áudio e exibe o texto palavra por palavra sincronizado
        ↓
[Frontend] Globo volta para idle quando o áudio termina
```

### Via Voz Desktop (nero.py)

```
Usuário fala no microfone
        ↓
[nero.py] listen() — Google Speech Recognition → texto
        ↓
[nero.py] normalize() — remove pontuação para comparação
        ↓
[nero.py] Verifica frases especiais (sair, desligar, WhatsApp, modo)
        ↓
[nero_memoria] handle_command() — é comando de memória?
    → Sim: speak(resposta) e continua o loop
    → Não: continua ↓
        ↓
[nero.py] detect_whatsapp_intent() — é pedido de mensagem WhatsApp?
    → Sim: send_whatsapp_message() via Selenium
    → Não: continua ↓
        ↓
[nero.py] ask_groq() — classify_and_query() + busca + Groq
        ↓
[nero.py] speak() — Piper TTS + pygame toca a resposta em voz alta
```

---

## Dependências e Instalação

### Instalação completa
```bash
pip install fastapi uvicorn groq piper-tts pygame
pip install SpeechRecognition PyAudio
pip install selenium webdriver-manager
pip install duckduckgo-search python-dotenv
pip install tavily-python  # opcional mas recomendado
```

### Tabela de dependências

| Pacote | Versão mínima | Usado em | Função |
|--------|--------------|----------|--------|
| `fastapi` | 0.100+ | nero_api.py | Framework web do servidor |
| `uvicorn` | 0.20+ | nero_api.py | Servidor ASGI que roda o FastAPI |
| `groq` | 0.5+ | ambos | Cliente da API Groq (IA) |
| `piper-tts` | 1.2+ | ambos | Síntese de voz offline |
| `pygame` | 2.0+ | nero.py | Reprodução de áudio |
| `SpeechRecognition` | 3.9+ | nero.py | Captura e converte voz em texto |
| `PyAudio` | 0.2+ | nero.py | Acesso ao microfone |
| `selenium` | 4.0+ | nero.py | Automação do WhatsApp Web |
| `webdriver-manager` | 3.8+ | nero.py | Gerencia o ChromeDriver |
| `duckduckgo-search` | 3.0+ | ambos | Busca web (fallback) |
| `python-dotenv` | 1.0+ | ambos | Lê arquivo .env |
| `tavily-python` | 0.3+ | ambos | Busca web principal (opcional) |
| `pydantic` | 2.0+ | nero_api.py | Validação de dados (vem com FastAPI) |

---

## Como Usar o Nero

### Iniciar o assistente web
Duplo clique em `iniciar_nero.bat`
→ Acesse pelo celular: `https://SEU_DOMINIO.ngrok-free.app`
→ Acesse pelo PC: `http://localhost:8000`

### Iniciar o assistente de voz
```
python nero.py
```

### Comandos de voz/texto disponíveis

| Comando | Exemplo | Ação |
|---------|---------|------|
| Conversa | "o que é inteligência artificial?" | Resposta da IA |
| Busca automática | "cotação do dólar agora" | Busca na internet + resposta |
| WhatsApp | "manda mensagem para João dizendo oi" | Envia pelo WhatsApp Web |
| Salvar memória | "lembra que João é meu sócio" | Salva permanentemente |
| Apagar memória | "esquece João" | Remove da memória |
| Ver memória | "o que você sabe sobre mim" | Lista tudo que sabe |
| Modo francês | "modo francês" ou botão FR | Ativa professor de francês |
| Modo normal | "modo normal" ou botão PT | Volta ao português |
| Encerrar (voz) | "encerrar conversa" | Para o nero.py |
| Desligar PC (voz) | "descansar agora paizao" | Desliga o computador |
