import discord
from discord.ext import commands
from discord import ui, app_commands
import datetime
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from quart import Quart, render_template, redirect, url_for, request

# --- 1. CONFIGURAÇÕES ---
TOKEN = os.environ.get('DISCORD_TOKEN', 'COLE_SEU_TOKEN_AQUI')
MONGO_URL = os.environ.get("MONGO_URL", "mongodb+srv://PSX:59585756@cluster0.dbttxsf.mongodb.net/?appName=Cluster0")

# --- 2. INICIALIZAÇÃO (BOT + SITE) ---
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
        print("✅ Comandos Slash sincronizados!")

bot = MyBot()

# --- 3. ROTAS DO SITE (DASHBOARD) ---
@app.route('/')
async def home():
    return await render_template('index.html')

@app.route('/login')
async def login():
    # Link de autorização (Bot + Comandos Slash)
    return redirect("https://discord.com/api/oauth2/authorize?client_id=1471209311551098931&permissions=8&scope=bot%20applications.commands")

# --- 4. COMPONENTES DO TICKET (BOT) ---
class CloseTicketView(ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
    
    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Este ticket será fechado em 5 segundos...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketModal(ui.Modal, title='Formulário de Suporte - PSX'):
    def __init__(self, categoria):
        super().__init__()
        self.categoria = categoria
    
    motivo = ui.TextInput(label='Motivo do contato', style=discord.TextStyle.paragraph, placeholder="Como podemos te ajudar?")

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        channel = await guild.create_text_channel(name=f'ticket-{interaction.user.name}', overwrites=overwrites)
        
        embed = discord.Embed(
            title="🎫 Central de Atendimento", 
            description=f"**Membro:** {interaction.user.mention}\n**Categoria:** {self.categoria}\n**Motivo:** {self.motivo.value}", 
            color=discord.Color.from_rgb(88, 101, 242)
        )
        embed.set_footer(text="Para fechar o ticket, clique no botão abaixo.")
        
        await channel.send(content=f"{interaction.user.mention} suporte solicitado!", embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Ticket criado em {channel.mention}", ephemeral=True)

class TicketView(ui.View):
    def __init__(self, categorias):
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=c['nome'], description=c['desc']) for c in categorias]
        select = ui.Select(placeholder="Selecione uma categoria...", options=options)
        
        async def callback(interaction: discord.Interaction):
            await interaction.response.send_modal(TicketModal(select.values[0]))
        
        select.callback = callback
        self.add_item(select)

# --- 5. COMANDOS ---
@bot.tree.command(name="ping", description="Verifica o status do bot")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latência: {round(bot.latency * 1000)}ms")

@bot.tree.command(name="setup_ticket", description="Configura o painel de tickets no canal atual")
@app_commands.checks.has_permissions(administrator=True)
async def setup_ticket(interaction: discord.Interaction):
    # Categorias do painel
    categorias = [
        {"nome": "Suporte", "desc": "Dúvidas gerais e ajuda com o bot"},
        {"nome": "Financeiro", "desc": "Problemas com pagamentos ou doações"},
        {"nome": "Denúncia", "desc": "Reportar jogadores ou comportamentos"}
    ]
    
    # Embed Principal
    embed = discord.Embed(
        title="🎫 Central de Atendimento - PSX Store",
        description="Clique no menu abaixo para abrir um ticket de suporte.\nNossa equipe responderá o mais rápido possível!",
        color=discord.Color.from_rgb(88, 101, 242)
    )
    embed.set_footer(text="PSX Bot - Gerenciamento Profissional")
    
    # Adicionando o Banner se existir no Banco de Dados
    config = await collection.find_one({"_id": interaction.guild_id})
    if config and config.get('banner'):
        embed.set_image(url=config['banner'])
    
    await interaction.channel.send(embed=embed, view=TicketView(categorias))
    await interaction.response.send_message("✅ Painel de tickets enviado com sucesso!", ephemeral=True)

# --- 6. INICIALIZAÇÃO DUPLA ---
async def main():
    port = int(os.environ.get("PORT", 10000))
    await asyncio.gather(
        bot.start(TOKEN),
        app.run_task(host="0.0.0.0", port=port)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
        
