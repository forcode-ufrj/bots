import discord
from discord import app_commands #Para criar comandos de barra
from discord.ext import voice_recv #Para gravar o áudio do usuário
from dotenv import load_dotenv #Para carregar o token do bot de forma segura
import wave  #Para manipular arquivos de áudio
import os
import logging #Para manipular logs no terminal e reduzir emissões desnecessárias
import threading #Para criar uma thread (mecanismo de sincronização) para gravar o áudio do usuário
import time #Para manipular o tempo de gravação do áudio do usuário
import array #Para manipular arrays de áudio do usuário

load_dotenv() #Carrega o arquivo .env para pegar o token do bot
TOKEN = os.getenv("Meu_token")

class GravadorPersonalizado(voice_recv.AudioSink): #Para receber separadamente o áudio de cada usuário, e evitar voz robótico quando as vozes se sobrepõem
    def __init__(self):
        super().__init__()
        self.audios = {}
        self.lock = threading.Lock()

    def wants_opus(self):
        return False

    def write(self, user, data): #O write é chamado quando receber o áudio de algum usuário
        if user is None:
            return

        usuario_id = user.id

        with self.lock:
            if usuario_id not in self.audios:
                self.audios[usuario_id] = [] #Gera uma lista para cada usuário assim que falar, armazenando separadamente

            self.audios[usuario_id].append({
                "pcm": data.pcm,
                "timestamp": time.monotonic() #timestamp para guardar o tempo em que cada usuário fala, assim evitando que as vozes se sobreponham e gerando um áudio mais limpo
            })

    #Responsável por realizar montar os áudios em um único arquivo, além de salvar o resultado no arquivo .wav (gravação)
    def cleanup(self):
        with self.lock:
            todos_os_trechos = [
                trecho
                for trechos in self.audios.values()
                for trecho in trechos
            ]

        if not todos_os_trechos:
            print("Nenhum trecho de áudio foi recebido.")
            return

        taxa_amostragem = 48000
        bytes_por_quadro = 4  # 2 canais × 2 bytes por amostra

        primeiro_instante = min(
            trecho["timestamp"] for trecho in todos_os_trechos
        )

        todos_os_trechos.sort(
            key=lambda trecho: trecho["timestamp"]
        )

        # Calcula quantos quadros serão necessários no arquivo final.
        total_quadros = 0

        for trecho in todos_os_trechos:
            inicio = int(
                (trecho["timestamp"] - primeiro_instante)
                * taxa_amostragem
            )

            quantidade_quadros = (
                len(trecho["pcm"]) // bytes_por_quadro
            )

            total_quadros = max(
                total_quadros,
                inicio + quantidade_quadros
            )

        if total_quadros == 0:
            print("Os trechos recebidos não contêm áudio.")
            return

        # Acumulador de 32 bits para permitir a soma das vozes.
        audio_mixado = array.array("i", [0]) * (
            total_quadros * 2
        )

        for trecho in todos_os_trechos: # Loop para captar os tempos em que cada áudio ocorre a partir do primeiro
        #Tentativa de evitar mistura sonora (robotização ou áudio pipocando)
            inicio = int(
                (trecho["timestamp"] - primeiro_instante)
                * taxa_amostragem
            )

            amostras = array.array("h")
            amostras.frombytes(trecho["pcm"])

            posicao_inicial = inicio * 2

            for i, amostra in enumerate(amostras):
                posicao = posicao_inicial + i

                if posicao >= len(audio_mixado):
                    break

                audio_mixado[posicao] += amostra

        # Limita as amostras ao intervalo de áudio PCM de 16 bits.
        audio_pcm = array.array(
            "h",
            (
                max(-32768, min(32767, amostra))
                for amostra in audio_mixado
            )
        )

        duracao_aproximada = (
            total_quadros / taxa_amostragem
        )

        #Sequência para confirmar que a compilação está contendo todos os usuários e áudios referentes
        print("Preparando o arquivo de áudio final...")

        with wave.open("gravacao.wav", "wb") as arquivo:
            arquivo.setnchannels(2)
            arquivo.setsampwidth(2)
            arquivo.setframerate(taxa_amostragem)
            arquivo.writeframes(audio_pcm.tobytes())

        print(f"Participantes gravados: {len(self.audios)}")
        print(f"Trechos recebidos: {len(todos_os_trechos)}")
        print(
            f"Duração aproximada: " #Garantir que comportou a duração de todos os áudios
            f"{duracao_aproximada:.2f} segundos"
        )
        print("Arquivo gravacao.wav criado.")

logging.getLogger("discord.ext.voice_recv.reader").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO) #Para reduzir a quantidade de logs desnecessários no terminal, deixando apenas os importantes

opus_path = os.path.join(os.path.dirname(discord.__file__), "bin", "libopus-0.x64.dll")
discord.opus.load_opus(opus_path) #Para carregar o Opus, necessário para gravar o áudio do usuário


intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot) #cria uma árvore de comandos para o bot
gravacao = None #Acrescenta uma variável para armazenar o áudio gravado
arquivo_audio = "gravacao.wav" #Nome do arquivo de áudio que será gravado
sink = None #Variável para armazenar o sink do áudio



@bot.event #evento para o bot reconhecer que está conectado
async def on_ready():
    await tree.sync() #O bot aguarda até que os comandos sejam sincronizados
    print(f"For Record conectado como: {bot.user}") #Mensagem de teste para saber se o bot se conectou corretamente
    print("O bot está pronto para gravar tudo!")

@tree.command(name="gravar", description="Inicia a gravação da reunião") #Cria o comando /gravar, que inicia a gravação da reunião
async def gravar(interaction: discord.Interaction):
    if not interaction.user.voice: #Teste para verificar se o usuário esta em um canal de voz
        await interaction.response.send_message( 
            "Se não estiver ninguém em canais de voz eu não trabalho!",
            ephemeral=True
        )
        return

    canal = interaction.user.voice.channel

    try:
        vc = await canal.connect(cls=voice_recv.VoiceRecvClient) #Conecta o bot ao canal de voz do usuário que digitou o comando
        sink = GravadorPersonalizado()
        vc.listen(sink) #Inicia a gravação do áudio
        await interaction.response.send_message( #Confirma que se conectou enviando uma mensagem
            "Pode deixar com o record! Vou gravar tudo que for dito aqui",
            ephemeral=True
        )
    except Exception as e: #Caso haja erro na conexão
        await interaction.response.send_message(
            f"Não consegui conectar: {e}",
            ephemeral=True
        )


@tree.command(name="parar", description="Encerra a gravação") #Criação do comando /parar para interromper a gravação
async def parar(interaction: discord.Interaction):
    if interaction.guild.voice_client is None: #Condicional para reconhecer se está na chamada
        await interaction.response.send_message(
            "Não estou conectado a um canal de voz.",
            ephemeral=True
        )
        return

    await interaction.guild.voice_client.disconnect() #Com essa linha, se estiver desconecta

    await interaction.response.send_message( #Mensagem de resposta para a saída
        "Record parando a fita, já já estará pronta para ser ouvida!",
        ephemeral=True
    )




bot.run(TOKEN) #Lerá o token e iniciará o bot