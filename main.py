import discord
from discord.ext import commands
from quart import Quart, render_template, redirect, request
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# --- CONFIGURAÇÕES ---
# O código vai tentar pegar do Render, se não achar, usa o que você colou
TOKEN = os.environ.get('DISCORD_TOKEN', 'COLE_SEU_TOKEN_AQUI')
MONGO_URL = os.environ.get("MONGO_URL", "mongodb+srv://PSX:59585756@cluster0.dbttxsf.mongodb.net/?appName=Cluster0")

# --- INICIALIZAÇÃO ---
app = Quart(__name__)

# Banco de Dados
cluster = AsyncIOMotorClient(MONGO_URL)
db = cluster["psx_bot"]
collection = db["configuracoes"]

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- ROTAS DO SITE ---
@app.route('/')
async def home():
    return await render_template('index.html')

@app.route('/login')
async def login():
    # Link direto para autorizar o bot
    return redirect(f"https://discord.com/api/oauth2/authorize?client_id=1471209311551098931&permissions=8&scope=bot%20applications.commands")

# --- COMANDOS DO BOT ---
@bot.event
async def on_ready():
    print(f'✅ Bot logado como {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos sincronizados!")
    except Exception as e:
        print(e)

@bot.tree.command(name="ping", description="Verifica o status do bot")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latência: {round(bot.latency * 1000)}ms")

# --- INICIALIZADOR ---
async def start_everything():
    # Pega a porta que o Render exige
    port = int(os.environ.get("PORT", 10000))
    
    # Inicia o Site e o Bot juntos da forma correta
    await asyncio.gather(
        bot.start(TOKEN),
        app.run_task(host="0.0.0.0", port=port)
    )

if __name__ == "__main__":
    try:
        @bot.tree.command(name="setup_ticket", description="Configura o painel de tickets no canal atual")
@app_commands.checks.has_permissions(administrator=True)
async def setup_ticket(interaction: discord.Interaction):
    # Definindo as categorias padrão
    categorias = [
        {"nome": "Suporte", "desc": "Dúvidas gerais e ajuda com o bot"},
        {"nome": "Financeiro", "desc": "Problemas com pagamentos ou doações"},
        {"nome": "Denúncia", "desc": "Reportar jogadores ou comportamentos"}
    ]
    
    # Criando o Embed bonitão
    embed = discord.Embed(
        title="🎫 Central de Atendimento - PSX Store",
        description="Clique no menu abaixo para abrir um ticket de suporte.\nNossa equipe responderá o mais rápido possível!",
        color=discord.Color.from_rgb(88, 101, 242) # Azul Discord
    )
    embed.set_footer(text="PSX Bot - Gerenciamento Profissional")
    
    # Enviando a mensagem com o menu (TicketView)
    await interaction.channel.send(embed=embed, view=TicketView(categorias))
    await interaction.response.send_message("✅ Painel de tickets enviado com sucesso!", ephemeral=True)
    asyncio.run(start_everything())
    except KeyboardInterrupt:
        pass
        
