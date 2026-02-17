import discord
from discord.ext import commands
from discord import ui, app_commands
import datetime
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from quart import Quart, render_template, redirect, url_for, request
from discord_ext_oauth import DiscordOAuthClient # Nome correto da biblioteca

# --- CONFIGURAÇÕES ---
TOKEN = os.environ.get('DISCORD_TOKEN')
MONGO_URL = os.environ.get("MONGO_URL")
CLIENT_ID = 1471209311551098931
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "YbtZZsBepMgDGjxPLYTtNvrST90RO8NE")
REDIRECT_URI = "https://psx-bot-final.onrender.com/callback"

# --- INICIALIZAÇÃO ---
app = Quart(__name__)
app.secret_key = os.urandom(24)

# Banco de Dados
cluster = AsyncIOMotorClient(MONGO_URL)
db = cluster["psx_bot"]
collection = db["configuracoes"]

# OAuth Client para o Site
oauth = DiscordOAuthClient(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, scopes=("identify", "guilds"))

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, help_command=None)
    
    async def setup_hook(self):
        # Isso sincroniza os comandos de / (slash commands)
        await self.tree.sync()

bot = MyBot()

# --- SISTEMA DE BANCO DE DATOS ---
async def get_config(guild_id):
    return await collection.find_one({"_id": guild_id})

async def save_config(guild_id, data):
    await collection.update_one({"_id": guild_id}, {"$set": data}, upsert=True)

# --- ROTAS DO DASHBOARD (SITE) ---
@app.route('/')
async def home():
    # Renderiza o index.html que está na pasta /templates
    return await render_template('index.html')

@app.route('/login')
async def login():
    return oauth.redirect()

@app.route('/callback')
async def callback():
    code = request.args.get("code")
    if not code:
        return "Erro: Código de autorização não encontrado."
    
    # Aqui o usuário é autenticado via Discord
    user_tokens = await oauth.get_tokens(code)
    user_info = await oauth.get_user(user_tokens.access_token)
    
    return f"<h1>Olá, {user_info.username}!</h1><p>Login na PSX Store realizado com sucesso. Em breve você poderá gerenciar seus tickets por aqui.</p>"

# --- SISTEMA DE TICKETS (BOT) ---
class CloseTicketView(ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
    
    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("O ticket será fechado em breve...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.channel.delete()

class TicketModal(ui.Modal, title='Suporte PSX Store'):
    def __init__(self, categoria):
        super().__init__()
        self.categoria = categoria
    motivo = ui.TextInput(label='Qual o motivo do contato?', style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(name=f'ticket-{interaction.user.name}', overwrites=overwrites)
        
        embed = discord.Embed(title="🎫 Novo Ticket", description=f"Membro: {interaction.user.mention}\nCategoria: {self.categoria}\nMotivo: {self.motivo.value}", color=discord.Color.blue())
        await channel.send(embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Seu ticket foi aberto em {channel.mention}", ephemeral=True)

class TicketView(ui.View):
    def __init__(self, categorias):
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=c['nome'], description=c['desc']) for c in categorias]
        select = ui.Select(placeholder="Escolha como podemos te ajudar...", options=options)
        
        async def callback(interaction: discord.Interaction):
            await interaction.response.send_modal(TicketModal(select.values[0]))
        
        select.callback = callback
        self.add_item(select)

# --- COMANDOS ---
@bot.command()
@commands.has_permissions(administrator=True)
async def rr(ctx):
    # Comando de configuração simplificado para salvar no MongoDB
    await ctx.send("Configuração iniciada! (Lembre-se de configurar via dashboard no futuro para ser mais fácil).")
    # Aqui você pode manter sua lógica de perguntas do !rr que passei antes

@bot.tree.command(name="painel", description="Envia o painel de suporte da loja")
async def painel(interaction: discord.Interaction):
    config = await get_config(interaction.guild_id)
    if not config:
        return await interaction.response.send_message("Configure o bot primeiro usando o comando `!rr`.", ephemeral=True)
    
    embed = discord.Embed(title="Central de Suporte", description=config.get('texto', 'Bem-vindo!'), color=discord.Color.blue())
    if config.get('banner'):
        embed.set_image(url=config['banner'])
        
    await interaction.response.send_message(embed=embed, view=TicketView(config['categorias']))

# --- RODAR BOT E SITE JUNTOS ---
async def main():
    # Inicia o servidor Web na porta correta para o Render
    port = int(os.environ.get("PORT", 10000))
    
    # Rodando o bot e o site simultaneamente
    await asyncio.gather(
        bot.start(TOKEN),
        app.run_task(host="0.0.0.0", port=port)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
        
