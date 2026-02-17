import discord
from discord.ext import commands
from discord import ui, app_commands
import datetime
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from quart import Quart, render_template

# --- 1. CONFIGURAÇÕES ---
TOKEN = os.environ.get('DISCORD_TOKEN')
MONGO_URL = "mongodb+srv://PSX:59585756@cluster0.dbttxsf.mongodb.net/?appName=Cluster0"

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

bot = MyBot()

# --- 2. SITE ---
@app.route('/')
async def home():
    return await render_template('index.html')

# --- 3. SISTEMA DE TICKET ---
class CloseTicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Fechando...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.channel.delete()

class TicketModal(ui.Modal, title='Suporte PSX'):
    motivo = ui.TextInput(label='Motivo', style=discord.TextStyle.paragraph)
    def __init__(self, categoria):
        super().__init__()
        self.categoria = categoria
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(name=f'ticket-{interaction.user.name}', overwrites=overwrites)
        embed = discord.Embed(title="Ticket Aberto", description=f"Categoria: {self.categoria}\nMotivo: {self.motivo.value}", color=0x5865F2)
        await channel.send(embed=embed, view=CloseTicketView())
        await interaction.followup.send(f"✅ Ticket criado: {channel.mention}")

class TicketView(ui.View):
    def __init__(self, categorias):
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=c['nome'], description=c['desc']) for c in categorias]
        self.select = ui.Select(placeholder="Escolha uma opção...", options=options)
        self.select.callback = self.callback
        self.add_item(self.select)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self.select.values[0]))

# --- 4. COMANDO DE SETUP ---
@bot.tree.command(name="setup_ticket", description="Envia o painel")
@app_commands.checks.has_permissions(administrator=True)
async def setup_ticket(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    categorias = [
        {"nome": "Suporte", "desc": "Ajuda geral"},
        {"nome": "Financeiro", "desc": "Pagamentos"},
        {"nome": "Denúncia", "desc": "Reportar algo"}
    ]
    embed = discord.Embed(title="🎫 Central de Atendimento PSX", description="Selecione abaixo para abrir um ticket.", color=0x5865F2)
    await interaction.channel.send(embed=embed, view=TicketView(categorias))
    await interaction.followup.send("✅ Painel enviado!")

# --- 5. RODAR TUDO ---
async def main():
    port = int(os.environ.get("PORT", 10000))
    if not TOKEN:
        print("❌ ERRO: DISCORD_TOKEN não encontrado nas variáveis do Render!")
        return
    await asyncio.gather(bot.start(TOKEN), app.run_task(host="0.0.0.0", port=port))

if __name__ == "__main__":
    asyncio.run(main())
        
