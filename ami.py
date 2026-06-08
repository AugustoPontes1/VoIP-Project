# Biblioteca para comunicação com a AMI (Asterisk Manager Interface)
from asterisk.ami import AMIClient, SimpleAction

# Conecta à AMI do Asterisk via TCP na porta 5038
# O Asterisk está rodando em Docker com essa porta mapeada para o host
client = AMIClient(address='127.0.0.1', port=5038)

# Autentica com o usuário configurado em manager.conf
client.login(
    username='python',
    secret='senha123'
)

# Define a ação "Originate": instrui o Asterisk a iniciar uma chamada
# Channel: ramal de destino via PJSIP (protocolo SIP moderno do Asterisk)
# Context/Exten/Priority: ponto de entrada no dialplan (extensions.conf)
# CallerID: identificador exibido como originador da chamada
action = SimpleAction(
    'Originate',
    Channel='PJSIP/1001',
    Context='internal',
    Exten='1001',
    Priority=1,
    CallerID='Python'
)

# Envia a ação ao Asterisk e aguarda a resposta
# O Asterisk enfileira a chamada e retorna imediatamente com Success ou Error
future = client.send_action(action)

# Exibe a resposta da AMI (Success = chamada enfileirada com sucesso)
print(future.response)

# Encerra a sessão com a AMI
client.logoff()
