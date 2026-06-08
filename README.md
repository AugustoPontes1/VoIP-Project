# Projeto VoIP com Asterisk e Python

Projeto acadêmico que demonstra o funcionamento de uma comunicação VoIP utilizando o servidor **Asterisk** em Docker, controlado via **AMI (Asterisk Manager Interface)** com Python.

## Visão Geral

O projeto simula um ciclo completo de chamada VoIP sem necessidade de softphone externo:

1. `sip_client.py` registra um ramal SIP (1001) no Asterisk usando a biblioteca `pyVoIP`
2. `ami.py` conecta à interface de gerenciamento do Asterisk e origina uma chamada para esse ramal
3. O Asterisk executa o dialplan: atende a chamada, aguarda 3 segundos e desliga

## Tecnologias

- **Asterisk 22** — servidor PBX rodando em container Docker
- **PJSIP** — stack SIP moderna usada pelo Asterisk
- **AMI (porta 5038)** — interface de gerenciamento para originar chamadas via Python
- **pyVoIP** — biblioteca Python para registrar o cliente SIP e atender chamadas
- **asterisk-ami** — biblioteca Python para comunicação com a AMI

## Estrutura

```
.
├── docker-compose.yml   # Sobe o container do Asterisk
├── pjsip.conf           # Configuração do ramal 1001 (transporte, endpoint, auth, AOR)
├── extensions.conf      # Dialplan: Answer → Wait(3) → Hangup
├── manager.conf         # Configuração da AMI (usuário "python")
├── ami.py               # Script que origina a chamada via AMI
└── sip_client.py        # Cliente SIP Python que registra o ramal e atende chamadas
```

## Arquivos de Configuração do Asterisk

O Asterisk não funciona sem seus arquivos `.conf` — eles substituem o que seria feito via interface gráfica em outros sistemas e definem todo o comportamento do servidor. Neste projeto, cada arquivo tem uma responsabilidade clara:

### `pjsip.conf`
Define **quem pode se conectar** ao Asterisk. Sem ele, o servidor não conhece nenhum ramal e rejeita qualquer tentativa de registro ou chamada.

Configura três objetos interdependentes para o ramal 1001:
- **transport**: protocolo e porta de escuta (UDP/5060)
- **endpoint**: contexto do dialplan, codecs permitidos (ulaw) e referências para auth e AOR
- **auth**: credenciais que o cliente SIP deve apresentar no REGISTER
- **AOR** *(Address of Record)*: onde armazenar o contato dinâmico após o registro — é o "endereço postal" do ramal

Se este arquivo estiver ausente ou mal configurado, o `sip_client.py` não consegue registrar o ramal e o Asterisk retorna erro `403 Forbidden` ou simplesmente ignora o REGISTER.

### `extensions.conf`
Define **o que acontece com a chamada** depois que ela é atendida — o chamado *dialplan*. Sem ele, o Asterisk atende a chamada e não sabe o que fazer, encerrando imediatamente.

```
[internal]
exten => 1001,1,Answer()   ; atende a chamada (completa o handshake SIP)
 same => n,Wait(3)         ; mantém o canal ativo por 3 segundos
 same => n,Hangup()        ; encerra a chamada e libera o canal
```

O contexto `internal` é o mesmo referenciado no `pjsip.conf` (campo `context`) e no `ami.py` (campo `Context` do Originate) — os três precisam estar alinhados para a chamada funcionar.

### `manager.conf`
Habilita e configura a **AMI (Asterisk Manager Interface)** — a interface TCP que o `ami.py` usa para enviar comandos ao Asterisk em tempo real. Por padrão a AMI vem desabilitada; sem este arquivo, a conexão na porta 5038 é recusada.

Define o usuário `python` com permissão total de leitura e escrita, o que permite executar ações como `Originate` (iniciar chamadas), `Hangup` (derrubar chamadas) e monitorar eventos do servidor.

### Por que esses arquivos ficam fora do container?

No `docker-compose.yml` os três arquivos são montados como volumes:

```yaml
volumes:
  - ./pjsip.conf:/etc/asterisk/pjsip.conf
  - ./extensions.conf:/etc/asterisk/extensions.conf
  - ./manager.conf:/etc/asterisk/manager.conf
```

Isso mantém a configuração **versionada junto ao código** do projeto, separada da imagem Docker. Qualquer alteração no dialplan ou nos ramais é feita nos arquivos locais e aplicada com um simples `docker compose restart`, sem precisar reconstruir a imagem.

## Como Executar

### Pré-requisitos

- Docker e Docker Compose
- Python 3.x com virtualenv

### Instalação

```bash
python -m venv venv
source venv/bin/activate
pip install pyvoip audioop-lts asterisk-ami
```

### Execução

**1. Suba o servidor Asterisk:**
```bash
docker compose up -d
```

**2. Terminal 1 — registre o cliente SIP:**
```bash
python sip_client.py
```
Aguarde a mensagem: `SIP client registered as 1001. Waiting for calls...`

**3. Terminal 2 — origine a chamada:**
```bash
python ami.py
```

### Saída esperada

**`ami.py`:**
```
Response: Success
Message: Originate successfully queued
```

**`sip_client.py`:**
```
Incoming call (ID: ...) — answering...
Call answered. Waiting for Asterisk to hang up...
Call ended.
```

## Fluxo da Chamada

```
ami.py ──► AMI (5038) ──► Asterisk ──► PJSIP/1001 ──► sip_client.py
                                            │
                                     extensions.conf
                                     Answer → Wait(3) → Hangup
```

---

## Arquitetura VoIP: do Analógico ao Digital

A voz humana é um sinal analógico contínuo. Para ser transmitida via rede IP, passa pelas seguintes etapas:

```
Voz (analógico)
      │
      ▼
 Amostragem (8.000 amostras/segundo — padrão G.711)
      │
      ▼
 Quantização (cada amostra vira um valor numérico de 8 bits)
      │
      ▼
 Codificação PCM (Pulse Code Modulation) → stream digital de 64 kbps
      │
      ▼
 Codec (ex: uLaw/G.711) comprime e empacota o áudio
      │
      ▼
 Pacotes RTP enviados pela rede IP
      │
      ▼
 Processo inverso no destino → som analógico
```

---

## Diagrama de Sinalização SIP

O SIP é o protocolo responsável por **estabelecer, modificar e encerrar** chamadas. Abaixo o fluxo de mensagens de uma chamada completa:

```
  Cliente (sip_client.py)          Asterisk (Servidor SIP)
          │                                │
          │──── REGISTER ────────────────►│  registra o ramal 1001
          │◄─── 200 OK ──────────────────│
          │                                │
          │◄─── INVITE ──────────────────│  Asterisk origina a chamada
          │──── 100 Trying ─────────────►│
          │──── 180 Ringing ────────────►│
          │──── 200 OK ─────────────────►│  cliente atende
          │◄─── ACK ─────────────────────│  confirmação
          │                                │
          │◄════ RTP (áudio) ════════════►│  mídia flui (Wait 3s)
          │                                │
          │◄─── BYE ─────────────────────│  Asterisk encerra
          │──── 200 OK ─────────────────►│
          │                                │
```

---

## Diagrama do Fluxo RTP

O RTP (Real-time Transport Protocol) é o protocolo responsável pelo **transporte da mídia** (áudio) durante a chamada. A negociação dos parâmetros de mídia ocorre via **SDP**, embutido nas mensagens SIP.

```
  INVITE (SDP offer)
  ┌─────────────────────────────────┐
  │ m=audio 10000 RTP/AVP 0        │  porta RTP do cliente + codec uLaw
  │ c=IN IP4 172.19.0.1            │  IP do cliente
  └─────────────────────────────────┘
          │
          ▼
  200 OK (SDP answer)
  ┌─────────────────────────────────┐
  │ m=audio 20000 RTP/AVP 0        │  porta RTP do Asterisk + codec aceito
  │ c=IN IP4 172.19.0.2            │  IP do Asterisk
  └─────────────────────────────────┘
          │
          ▼
  Fluxo RTP estabelecido:

  sip_client.py :10000  ◄──────────►  Asterisk :20000
                      pacotes RTP/UDP
                    (áudio em tempo real)
```
