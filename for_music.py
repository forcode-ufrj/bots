import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()  # carrega as variáveis de ambiente do arquivo .env

# configuração das intents (pra ele conseguir ler mensagens e comandos)
intents = discord.Intents.all()

# inicializar o bot
bot = commands.Bot(command_prefix='!', intents=intents)

# o que é o yt-dlp?
# ferramenta de linha de comando pra baixar áudios e vídeos de sites como o Youtube
# busca a mídia

# o que é FFmpeg?
# ferramenta de linha de comando pra converter arquivos de áudio e vídeo entre diferentes formatos
# processa a mídia

# yt-dlp (baixa)  →  FFmpeg (processa)  →  Discord (toca)  

# configurações do yt-dlp e do ffmpeg
YTDL_OPTIONS = {
    'format' : 'bestaudio/best', # melhor arquivo de áudio ou melhor arquivo único que tiver áudio
    'noplaylist' : True, # se a url apontar pra uma playlist, vai baixar só aquele vídeo e ignorar o resto
    'quiet' : True, # silencia a saída, não imprime mensagens de download nem status
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', # tenta reconectar caso caia a conexão
    'options': '-vn' # diz pra ignorar o vídeo, foca só no áudio
}

@bot.event # bot event é um evento que o bot vai escutar, por ex quando ele está pronto ou quandoa lguém manda mensagem!
async def on_ready():
    print(f'Bot {bot.user.name} está pronto para tocar músicas para você! :)')
# async def é uma função que pode pausar e retomar, bom pra ele não travar tudo enquanto espera a resposta

@bot.command() # bot command é um comando que o bot vai escutar, por ex quando alguém digita !play
async def tocar(ctx, url: str): # ele recebe o contexto e a url do usuário
    # tem que conectar ao canal que o usuário está e tocar a música do link do youtube

    # verifica se usuário está em um canal de voz:
    if not ctx.author.voice: # ctx.author.voice é o estado de voz do usuário. "not" é se o usuário não estiver em canal algum
        return await ctx.send("Você precisa estar em um canal de voz para conseguir escutar músicas!")
        # ctx = contexto do comando! (quem enviou, onde, o que etc)
    
    canal_de_voz = ctx.author.voice.channel # pega o canal de voz em que o usuário está

    # conecta ao canal de voz
    if not ctx.voice_client: # "voice_client" representa a conexão do bot em um canal de voz, ou seja, se ele não estiver conectado a nenhum canal ainda
        voice_client = await canal_de_voz.connect() # await é para esperar a conexão ser feita antes de continuar
    else:
        voice_client = ctx.voice_client # se ja estiver conectado a algum canal, é só pegar a conexão atual!

    await ctx.send("Procurando sua música....")

    # extrair infos da música com o yt-dlp
    with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
        info = ydl.extract_info(url, download=False)
        url_musica = info['url']
        titulo_musica = info['title']

    # preparar o áudio com FFmpeg
    fonte_audio = discord.FFmpegPCMAudio(url_musica, **FFMPEG_OPTIONS) # "**" é para passar o dicionário como argumentos nomeados, ou seja, cada chave do dicionário vira um argumento da função

    # toca a música uhu amo
    if not voice_client.is_playing(): # se não estiver tocando nada, toca a música
        voice_client.play(fonte_audio)
        await ctx.send(f"🎶Tocando agora: **{titulo_musica}**! aproveite!")
    else: # se já estiver tocando algo, avisa que não pode tocar outra música
        await ctx.send("Já estou tocando uma música! Espere terminar ou use o comando !stop para parar a música atual.")
        # TODO: implementar filas pras músicas

@bot.command()
async def pausa(ctx):
    voice_client = ctx.voice_client #"ctx.voice_client" declara se o bot está conectado a algum canal de voz do servidor (=ctx.guild.voice_client")
    if voice_client and voice_client.is_playing(): # tem que verificar se tem conexão em algum canal && se está tocando algo
        voice_client.pause()
        await ctx.send("⏸️ Música pausada!")
    else:
        await ctx.send("Não estou tocando nenhuma música no momento.")

@bot.command()
async def volta(ctx):
    voice_client = ctx.voice_client
    if voice_client and voice_client.is_paused(): # verifica se o bot está pausado
        voice_client.resume()
        await ctx.send("▶️ Voltando com sua música!")

@bot.command()
async def para(ctx):
    voice_client = ctx.voice_client
    if voice_client:
        voice_client.stop()
        await voice_client.disconnect()
        await ctx.send("⏹️ Música parada e vou desconectar! Tchauuuu 👋")


bot.run(os.getenv('TOKEN_DO_BOT'))