import discord
from discord.ext import commands
from discord import ui, app_commands
import datetime
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from quart import Quart, render_template, redirect, url_for, request
from threading import Thread

# --- CONFIGURAÇÕES DE CONEXÃO ---
# Pegando os dados que configuramos no Render e no Discord
MONGO_URL = os.environ.get("MONGO_URL", "mongodb+srv://PSX:59585756@cluster0.dbttxsf.mongodb.net/?appName=Cluster0")
CLIENT_ID = 1471209311551098931
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "YbtZZsBepMgDGjxPLYTtNvrST90RO8NE")
REDIRECT_URI = "https://psx-bot-final.onrender.com/callback"

# --- INICIALIZAÇÃO ---
app = Quart(__name__)
cluster = AsyncIOMotorClient(MONGO_URL)
db = cluster["psx_bot"]
collection = db["configuracoes"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, help_command=None)
    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

# --- FUNÇÕES DO BANCO DE DATOS ---
async def get_config(guild_id):
    return await collection.find_one({"_id": guild_id})

async def save_config(guild_id, data):
    await collection.update_one({"_id": guild_id}, {"$set": data}, upsert=True)

# --- ROTAS DO SITE (DASHBOARD) ---
@app.route('/')
async def home():
    # Isso vai procurar a pasta 'templates/index.html' que você criou
    try:
        return await render_template('index.html')
    except:
        return "<h1>Painel PSX Online</h1><p>Crie a pasta 'templates' com o index.html para ver o site completo!</p>"

@app.route('/login')
async def login():
    # Link de login que você gera no Discord Developer Portal
    discord_login_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds"
    return redirect(discord_login_url)

@app.route('/callback')
async def callback():
    # Aqui é onde o usuário cai depois de logar (O 'sucesso' do dashboard)
    return "<h1>Login realizado com sucesso!</h1><p>Em breve você poderá configurar seus servidores por aqui.</p>"

# --- SISTEMA DE TICKETS E AVALIAÇÃO ---
class FeedbackModal(ui.Modal):
    def __init__(self, nota, user_name, guild_id):
        super().__init__(title="Feedback do Atendimento")
        self.nota, self.user_name, self.guild_id = nota, user_name, guild_id
    
    comentario = ui.TextInput(label='O que achou?', style=discord.TextStyle.paragraph, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        config = await get_config(self.guild_id)
        msg = "Obrigado pela sua avaliação!" if int(self.nota) >= 3 else "Sentimos muito. Vamos melhorar!"
        await interaction.response.send_message(msg, ephemeral=True)

        log_id = int(config['log_id']) if config and config.get('log_id') else None
        canal = bot.get_channel(log_id)
        if canal:
            cor = discord.Color.green() if int(self.nota) >= 3 else discord.Color.red()
            embed = discord.Embed(title="📥 Nova Avaliação", color=cor, timestamp=datetime.datetime.now())
            embed.add_field(name="Membro", value=self.user_name)
            embed.add_field(name="Nota", value=f"{self.nota} ⭐")
            embed.add_field(name="Feedback", value=self.comentario.value or "Sem comentário.")
            await canal.send(embed=embed)

class EvalDropdown(ui.Select):
    def __init__(self, user_name, guild_id):
        super().__init__(placeholder="Avalie o atendimento", options=[discord.SelectOption(label=f"{i} Estrelas", value=str(i), emoji="⭐") for i in range(5, 0, -1)])
        self.user_name, self.guild_id = user_name, guild_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(FeedbackModal(self.values[0], self.user_name, self.guild_id))

class CloseTicketView(ui.View):
    def __init__(self, guild_id): 
        super().__init__(timeout=None)
        self.guild_id = guild_id
    
    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        view = ui.View()
        view.add_item(EvalDropdown(interaction.user.name, self.guild_id))
        try:
            await interaction.user.send(content="Seu ticket foi fechado. Como foi seu atendimento?", view=view)
        except:
            pass
        await interaction.channel.delete()

class TicketModal(ui.Modal, title='Formulário de Suporte'):
    def __init__(self, categoria, guild_id):
        super().__init__()
        self.categoria, self.guild_id = categoria, guild_id
    motivo = ui.TextInput(label='Motivo do contato', style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(name=f'ticket-{interaction.user.name}', overwrites=overwrites)
        emb = discord.Embed(title="🎫 Suporte PSX", description=f"**Categoria:** {self.categoria}\n**Motivo:** {self.motivo.value}", color=discord.Color.blue())
        await channel.send(content=interaction.user.mention, embed=emb, view=CloseTicketView(self.guild_id))
        await interaction.response.send_message(f"✅ Ticket criado em {channel.mention}", ephemeral=True)

class TicketView(ui.View):
    def __init__(self, config, guild_id):
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=c['nome'], description=c['desc']) for c in config['categorias']]
        select = ui.Select(placeholder="Escolha uma categoria...", options=options)
        async def cb(interaction):
            await interaction.response.send_modal(TicketModal(select.values[0], guild_id))
        select.callback = cb
        self.add_item(select)

# --- COMANDOS ---
@bot.command()
@commands.has_permissions(administrator=True)
async def rr(ctx):
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        await ctx.send("⚙️ **Configuração PSX**\n1. Envie o **ID do Canal de Logs**:")
        log = await bot.wait_for('message', check=check, timeout=60)
        await ctx.send("2. Envie o **Texto do Painel**:")
        txt = await bot.wait_for('message', check=check, timeout=60)
        await ctx.send("3. Envie as **Categorias** (Ex: `Vendas | Comprar produtos # Dúvidas | Tirar dúvidas`):")
        cats_msg = await bot.wait_for('message', check=check, timeout=120)
        cats = [{'nome': p.split('|')[0].strip(), 'desc': p.split('|')[1].strip()} for p in cats_msg.content.split('#') if '|' in p]
        await ctx.send("4. Envie o link do **Banner** ou digite `skip`:")
        banner = await bot.wait_for('message', check=check, timeout=60)
        banner_url = None if banner.content.lower() == 'skip' else banner.content

        await save_config(ctx.guild.id, {'log_id': log.content, 'texto': txt.content, 'categorias': cats, 'banner': banner_url})
        await ctx.send("✅ Configuração salva com sucesso no banco de dados!")
    except Exception as e:
        await ctx.send(f"❌ Erro na configuração: {e}")

@bot.tree.command(name="painel", description="Envia o painel de atendimento")
async def painel(interaction: discord.Interaction):
    config = await get_config(interaction.guild_id)
    if not config:
        return await interaction.response.send_message("Este servidor ainda não foi configurado. Use `!rr`.", ephemeral=True)
    
    embed = discord.Embed(title="CENTRAL DE ATENDIMENTO", description=config['texto'], color=discord.Color.blue())
    if config.get('banner'):
        embed.set_image(url=config['banner'])
    await interaction.response.send_message(embed=embed, view=TicketView(config, interaction.guild_id))

# --- INICIALIZAÇÃO DUPLA (BOT + SITE) ---
def run_http():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # Roda o servidor Web em uma thread separada
    Thread(target=run_http).start()
    # Roda o Bot
    bot.run(os.environ.get('DISCORD_TOKEN', 'COLE_SEU_TOKEN_AQUI_SE_NAO_USAR_VARIAVEL'))
        
