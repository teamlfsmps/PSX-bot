import discord
from discord.ext import commands
from discord import ui, app_commands
import datetime
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from quart import Quart, render_template

# --- CONFIGURAÇÕES ---
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
        super().__init__(command_prefix='!', intents=intents, help_command=None)
    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

# --- SISTEMA DE AVALIAÇÃO (ESTRELAS) ---
class FeedbackView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.select(placeholder="⭐ Avalie nosso atendimento...", options=[
        discord.SelectOption(label="5 Estrelas", value="5", emoji="⭐⭐⭐⭐⭐"),
        discord.SelectOption(label="4 Estrelas", value="4", emoji="⭐⭐⭐⭐"),
        discord.SelectOption(label="3 Estrelas", value="3", emoji="⭐⭐⭐"),
        discord.SelectOption(label="Péssimo", value="1", emoji="⭐")
    ])
    async def select_callback(self, interaction: discord.Interaction, select: ui.Select):
        await interaction.response.send_message(f"『PSX』 Obrigado pela nota {select.values[0]}! Sua avaliação nos ajuda muito.", ephemeral=True)

# --- SISTEMA DE TICKET ---
class CloseTicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("『PSX』 Encerrando... Avalie-nos abaixo!", view=FeedbackView(), ephemeral=False)
        await asyncio.sleep(10)
        await interaction.channel.delete()

class TicketModal(ui.Modal, title='『PSX』 Abrir Chamado'):
    motivo = ui.TextInput(label='Assunto', style=discord.TextStyle.paragraph)
    def __init__(self, categoria):
        super().__init__()
        self.categoria = categoria
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        ch = await interaction.guild.create_text_channel(name=f'ticket-{interaction.user.name}', overwrites=overwrites)
        embed = discord.Embed(title="『PSX』 Atendimento", description=f"**Membro:** {interaction.user.mention}\n**Categoria:** {self.categoria}\n**Motivo:** {self.motivo.value}", color=0x5865F2)
        await ch.send(embed=embed, view=CloseTicketView())
        await interaction.followup.send(f"✅ 『PSX』 Criado: {ch.mention}")

class TicketView(ui.View):
    def __init__(self, categorias):
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=c['nome'], description=c['desc']) for c in categorias]
        self.select = ui.Select(placeholder="Escolha uma categoria...", options=options)
        self.select.callback = self.callback
        self.add_item(self.select)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self.select.values[0]))

# --- COMANDOS SLASH ---
@bot.tree.command(name="ping", description="『PSX』 Mostra a latência do bot.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! 『PSX』 {round(bot.latency * 1000)}ms")

@bot.tree.command(name="ajuda", description="『PSX』 Mostra os comandos disponíveis.")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 『PSX』 Central de Ajuda", color=0x5865F2)
    embed.add_field(name="/ping", value="Latência do bot.", inline=True)
    embed.add_field(name="/setup_painel", value="Envia o painel de tickets.", inline=True)
    embed.add_field(name="!rr", value="Configura título e imagem do servidor.", inline=False)
    embed.set_footer(text="A sensi chega a 200!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setup_painel", description="『PSX』 Inicia o painel de atendimento no servidor.")
async def setup_painel(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    dados = await collection.find_one({"_id": interaction.guild_id})
    categorias = dados.get("categorias") if dados and dados.get("categorias") else [
        {"nome": "Suporte", "desc": "Dúvidas gerais"},
        {"nome": "Financeiro", "desc": "Compras"}
    ]
    t = dados.get("titulo", "Central de Atendimento") if dados else "Painel PSX"
    embed = discord.Embed(title=f"『PSX』 {t}", description="Abra um ticket selecionando abaixo.", color=0x5865F2)
    if dados and dados.get("banner"): embed.set_image(url=dados['banner'])
    await interaction.channel.send(embed=embed, view=TicketView(categorias))
    await interaction.followup.send("✅ 『PSX』 Painel enviado!")

# --- COMANDO !RR ---
@bot.command()
@commands.has_permissions(administrator=True)
async def rr(ctx):
    await ctx.send("⚙️ 『PSX』 Qual o título para o painel?")
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        t = await bot.wait_for('message', check=check, timeout=60.0)
        await ctx.send("Envie o link do **Banner** ou `pular`:")
        b = await bot.wait_for('message', check=check, timeout=60.0)
        url = b.content if b.content.lower() != 'pular' else None
        await collection.update_one({"_id": ctx.guild.id}, {"$set": {"titulo": t.content, "banner": url}}, upsert=True)
        await ctx.send(f"✅ 『PSX』 Configurado! Use `/setup_painel`.")
    except asyncio.TimeoutError:
        await ctx.send("⏰ 『PSX』 Tempo esgotado.")

# --- SITE E START ---
@app.route('/')
async def home(): return await render_template('index.html')

async def main():
    port = int(os.environ.get("PORT", 10000))
    await asyncio.gather(bot.start(TOKEN), app.run_task(host="0.0.0.0", port=port))

if __name__ == "__main__":
    asyncio.run(main())
        
