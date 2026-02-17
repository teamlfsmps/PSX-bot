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
        super().__init__(command_prefix='!', intents=intents, help_command=None)
    
    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ 『PSX』 Comandos sincronizados dentro do limite de caracteres!")

bot = MyBot()

# --- 2. SITE ---
@app.route('/')
async def home():
    return await render_template('index.html')

# --- 3. COMPONENTES DE TICKET ---
class CloseTicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("『PSX』 Encerrando o atendimento em instantes...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.channel.delete()

class TicketModal(ui.Modal, title='『PSX』 Suporte'):
    motivo = ui.TextInput(label='Motivo', style=discord.TextStyle.paragraph, placeholder="Descreva sua dúvida...")
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
        embed = discord.Embed(title="🎫 Novo Ticket", description=f"**Membro:** {interaction.user.mention}\n**Categoria:** {self.categoria}\n**Motivo:** {self.motivo.value}", color=0x5865F2)
        embed.set_footer(text="『PSX』 Sistema Multi-Servidor")
        await channel.send(content=f"{interaction.user.mention} suporte solicitado!", embed=embed, view=CloseTicketView())
        await interaction.followup.send(f"✅ 『PSX』 Ticket criado: {channel.mention}")

class TicketView(ui.View):
    def __init__(self, categorias):
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=c['nome'], description=c['desc']) for c in categorias]
        self.select = ui.Select(placeholder="Selecione uma categoria...", options=options)
        self.select.callback = self.callback
        self.add_item(self.select)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self.select.values[0]))

# --- 4. COMANDOS SLASH (/) - TEXTOS CURTOS PARA EVITAR ERRO ---
@bot.tree.command(name="ping", description="『PSX』 Mostra a latência e velocidade de resposta atual do bot.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! 『PSX』 Latência: {round(bot.latency * 1000)}ms")

@bot.tree.command(name="ajuda", description="『PSX』 Menu de auxílio com a lista de todos os comandos e funções.")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 『PSX』 Central de Ajuda", color=0x5865F2)
    embed.add_field(name="/ping", value="Verifica latência.", inline=True)
    embed.add_field(name="/setup_ticket", value="Envia o painel de suporte.", inline=True)
    embed.add_field(name="!rr", value="Configura título e banner.", inline=False)
    embed.set_footer(text="Dica: A sensibilidade chega até 200!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setup_ticket", description="『PSX』 Envia o painel de atendimento usando as configurações salvas.")
async def setup_ticket(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    dados = await collection.find_one({"_id": interaction.guild_id})
    categorias = dados.get("categorias") if dados and dados.get("categorias") else [
        {"nome": "Suporte Geral", "desc": "Ajuda técnica"},
        {"nome": "Financeiro", "desc": "Pagamentos"}
    ]
    titulo = dados.get("titulo", "Central de Atendimento") if dados else "Atendimento"
    embed = discord.Embed(title=f"🎫 {titulo}", description="Selecione abaixo para abrir um ticket.", color=0x5865F2)
    if dados and dados.get("banner"): embed.set_image(url=dados['banner'])
    await interaction.channel.send(embed=embed, view=TicketView(categorias))
    await interaction.followup.send("✅ 『PSX』 Painel enviado!")

# --- 5. COMANDO !RR ---
@bot.command()
@commands.has_permissions(administrator=True)
async def rr(ctx):
    await ctx.send("⚙️ **『PSX』** Qual o título para o painel de tickets?")
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        t = await bot.wait_for('message', check=check, timeout=60.0)
        await ctx.send("Envie o **Link do Banner** ou digite `pular`:")
        b = await bot.wait_for('message', check=check, timeout=60.0)
        url = b.content if b.content.lower() != 'pular' else None
        await collection.update_one({"_id": ctx.guild.id}, {"$set": {"titulo": t.content, "banner": url}}, upsert=True)
        await ctx.send(f"✅ 『PSX』 Salvo para **{ctx.guild.name}**! Use `/setup_ticket`.")
    except asyncio.TimeoutError:
        await ctx.send("⏰ 『PSX』 Tempo esgotado.")

# --- 6. EXECUÇÃO ---
async def main():
    port = int(os.environ.get("PORT", 10000))
    if not TOKEN: return print("❌ 『PSX』 Token faltando!")
    await asyncio.gather(bot.start(TOKEN), app.run_task(host="0.0.0.0", port=port))

if __name__ == "__main__":
    asyncio.run(main())
        
