import time
# VoIPPhone: representa o cliente SIP (equivale a um softphone)
# CallState: enum com os estados possíveis de uma chamada (RINGING, ANSWERED, ENDED, etc.)
from pyVoIP.VoIP import VoIPPhone, CallState


# Wrapper para print com flush imediato, garantindo que logs apareçam em tempo real
def log(msg):
    print(msg, flush=True)


# Callback executado pelo pyVoIP toda vez que uma chamada recebida é detectada
def call_handler(call):
    log(f"Incoming call (ID: {call.call_id}) — answering...")

    # Envia "200 OK" ao Asterisk via SIP, completando o handshake de sinalização
    # A partir daqui o canal RTP é aberto e o áudio começa a fluir
    call.answer()
    log("Call answered. Waiting for Asterisk to hang up...")

    # Mantém o processo aguardando enquanto a chamada estiver ativa
    # O Asterisk executa o dialplan (Wait 3s) e depois envia BYE para encerrar
    while call.state == CallState.ANSWERED:
        time.sleep(0.1)

    log("Call ended.")


# Instancia o cliente SIP com as credenciais do ramal configurado no pjsip.conf
# server/port: endereço do Asterisk (Docker com porta 5060 mapeada)
# myIP: IP do host visível pelo container Docker (gateway da rede Docker)
# sipPort: porta local onde este cliente SIP escuta mensagens SIP recebidas
phone = VoIPPhone(
    server="127.0.0.1",
    port=5060,
    username="1001",
    password="1234",
    myIP="172.19.0.1",
    sipPort=5080,
    callCallback=call_handler,
)

# Envia o REGISTER ao Asterisk para registrar o ramal 1001
# Após isso, o Asterisk sabe que pode alcançar este cliente em 172.19.0.1:5080
phone.start()
log("SIP client registered as 1001. Waiting for calls...")
log("Run ami.py in another terminal to trigger a call.")
log("Press Ctrl+C to stop.")

# Mantém o processo vivo aguardando chamadas
# Sem esse loop o script encerraria e o ramal seria desregistrado imediatamente
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    # Envia REGISTER com Expires: 0, removendo o ramal do Asterisk antes de sair
    phone.stop()
    log("SIP client stopped.")
