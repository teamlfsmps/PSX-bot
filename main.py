import discord
from discord.ext import commands
from discord import ui, app_commands
import datetime
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from quart import Quart, render_template, redirect

# --- 1. CONFIGURAÇÕES ---
# O bot vai ler o Token e o Banco de Dados das variáveis do Render
TOKEN = os.environ.get('DISCORD_TOKEN')
MONGO_URL = os.environ.get("MONGO_URL", "mongodb+srv://PSX:59585756@cluster0.dbttxsf.mongodb.net/?appName=Cluster0")

# --- 2. INICIALIZAÇÃO ---
app = Quart(__name__)
cluster = AsyncIOMotorClient(MONGO_URL)
db = cluster["psx_bot"]
collection = db["configuracoes"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Comandos Slash (/) sincronizados com sucesso!")

bot = MyBot()

# --- 3. SITE (DASHBOARD) ---
@app.route('/')
async def home():
    return await render_template('index.html')

# --- 4. SISTEMA DE TICKET ---
class CloseTicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("🔒 Este canal será deletado em 5 segundos...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketModal(ui.Modal, title='Suporte PSX Store'):
    motivo = ui.TextInput(label='Qual o motivo do contato?', style=discord.TextStyle.paragraph, placeholder="Descreva brevemente sua dúvida...")
    
    def __init__(self, categoria):
        super().__init__()
        self.categoria = categoria

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        # Configura permissões: Apenas o staff e o dono do ticket veem
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages
    
