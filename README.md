# Nero — Assistente Pessoal de Voz

Assistente pessoal controlado por voz, com respostas em áudio, integração com WhatsApp Web e suporte a modo professor de francês.

## O que faz

- Escuta comandos pelo microfone em tempo real
- Responde em voz alta usando síntese de voz offline (Piper TTS)
- Conversa com inteligência artificial via Groq (LLaMA 70B)
- Envia mensagens pelo WhatsApp Web via automação com Selenium
- Alterna entre modo padrão (português) e modo professor de francês
- Desliga o computador por comando de voz

## Comandos disponíveis

| Frase | Ação |
|---|---|
| `encerrar conversa` | Sai do modo conversa |
| `descansar agora paizao` | Encerra o Nero e desliga o PC |
| `modo francês` | Ativa o modo professor de francês |
| `modo normal` | Volta ao modo padrão em português |
| `abrir whatsapp` | Abre o WhatsApp Web no Chrome |
| `manda mensagem para [contato] dizendo [mensagem]` | Envia mensagem pelo WhatsApp |

## Requisitos

- Python 3.10 ou superior
- Google Chrome instalado
- Microfone funcionando
- Conta no [Groq](https://console.groq.com) para obter a API key

## Instalação

```bash
pip install SpeechRecognition PyAudio piper-tts pygame groq
pip install selenium webdriver-manager python-dotenv
```

Configure a chave da API:

```bash
cp .env.example .env
```

Abra o `.env` e preencha com sua chave do Groq:

```
GROQ_API_KEY=sua_chave_aqui
```

## Modelos de voz (Piper TTS)

Os modelos não estão incluídos no repositório por serem arquivos grandes. Baixe manualmente e coloque na pasta do projeto:

- **Português:** `pt_BR-faber-medium.onnx` + `pt_BR-faber-medium.onnx.json`
- **Francês (opcional):** `fr_FR-siwis-medium.onnx` + `fr_FR-siwis-medium.onnx.json`

Disponíveis em: [github.com/rhasspy/piper/blob/master/VOICES.md](https://github.com/rhasspy/piper/blob/master/VOICES.md)

## Como rodar

```bash
python nero.py
```

Na primeira vez que usar o WhatsApp, o Chrome vai abrir e pedir para escanear o QR code. Depois disso o perfil fica salvo.

> **Importante:** feche o Google Chrome antes de rodar o Nero, pois ele abre o Chrome com seu perfil pessoal.

## Estrutura do projeto

```
projeto jarvis/
├── nero.py          # código principal
├── .env             # sua chave da API (não sobe ao GitHub)
├── .env.example     # modelo de configuração
├── PLANO_APP.md     # plano para versão mobile
└── .gitignore
```
