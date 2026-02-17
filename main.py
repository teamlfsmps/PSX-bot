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
        print(f"✅ 『PSX』 Comandos sincronizados com descrições detalhadas!")

bot = MyBot()

# --- 2. SITE (DASHBOARD) ---
@app.route('/')
async def home():
    return await render_template('index.html')

# --- 3. COMPONENTES DE TICKET ---
class CloseTicketView(ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
    
    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("『PSX』 Este canal de atendimento será encerrado em instantes...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.channel.delete()

class TicketModal(ui.Modal, title='『PSX』 Formulário de Suporte'):
    motivo = ui.TextInput(label='Motivo do contato', style=discord.TextStyle.paragraph, placeholder="Descreva aqui o que você precisa...")
    
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
        
        embed = discord.Embed(
            title="🎫 Ticket de Atendimento",
            description=f"**Usuário:** {interaction.user.mention}\n**Categoria Escolhida:** {self.categoria}\n**Assunto:** {self.motivo.value}",
            color=0x5865F2,
            timestamp=datetime.datetime.now()
        )
        embed.set_footer(text="『PSX』 Sistema de Suporte Multi-Servidor")
        
        await channel.send(content=f"{interaction.user.mention} suporte solicitado!", embed=embed, view=CloseTicketView())
        await interaction.followup.send(f"✅ 『PSX』 Seu ticket foi gerado com sucesso: {channel.mention}")

class TicketView(ui.View):
    def __init__(self, categorias):
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=c['nome'], description=c['desc']) for c in categorias]
        self.select = ui.Select(placeholder="Selecione uma opção para abrir o ticket...", options=options)
        self.select.callback = self.callback
        self.add_item(self.select)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self.select.values[0]))

# --- 4. COMANDOS SLASH (/) COM DESCRIÇÕES DETALHADAS ---
@bot.tree.command(name="ping", description="『PSX』 Mostra a velocidade de resposta (latência) atual do bot com o servidor.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! 『PSX』 Latência: {round(bot.latency * 1000)}ms")

@bot.tree.command(name="ajuda", description="『PSX』 Exibe o menu principal de auxílio com a lista de todos os comandos e suas funcionalidades.")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 『PSX』 Central de Comandos", color=0x5865F2)
    embed.add_field(name="/ping", value="Verifica a latência do bot.", inline=False)
    embed.add_field(name="/setup_ticket", value="Envia o painel de atendimento para os membros abrirem tickets.", inline=False)
    embed.add_field(name="!rr", value="Inicia a configuração interativa do seu servidor no banco de dados.", inline=False)
    embed.add_field(name="Sensibilidade", value="Dica do dia: a sensibilidade configurada chega a 200!", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setup_ticket", description="『PSX』 Envia o painel interativo de tickets para o canal atual usando as configurações salvas do servidor.")
async def setup_ticket(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    dados = await collection.find_one({"_id": interaction.guild_id})
    
    categorias = dados.get("categorias") if dados and dados.get("categorias") else [
        {"nome": "Suporte Geral", "desc": "Ajuda técnica e dúvidas"},
        {"nome": "Financeiro", "desc": "Assuntos sobre pagamentos e planos"}
    ]
    
    titulo = dados.get("titulo", "Central de Atendimento") if dados else "Atendimento Principal"
    
    embed = discord.Embed(title=f"🎫 {titulo}", description="Clique no menu abaixo para abrir um canal de atendimento privado.", color=0x5865F2)
    if dados and dados.get("banner"):
        embed.set_image(url=dados['banner'])
        
    await interaction.channel.send(embed=embed, view=TicketView(categorias))
    await interaction.followup.send("✅ 『PSX』 Painel de atendimento enviado com sucesso!")

# --- 5. COMANDO CLÁSSICO !RR (PARA CONFIGURAÇÃO MULTI-SERVER) ---
@bot.command()
@commands.has_permissions(administrator=True)
async def rr(ctx):
    await ctx.send("⚙️ **『PSX』 Configuração do Servidor**\nQual o título você deseja para o seu painel de tickets?")
    
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        titulo_msg = await bot.wait_for('message', check=check, timeout=60.0)
        await ctx.send("Excelente! Agora envie o **Link da Imagem (Banner)** ou digite `pular` para não usar imagem:")
        banner_msg = await bot.wait_for('message', check=check, timeout=60.0)
        
        banner_url = banner_msg.content if banner_msg.content.lower() != 'pular' else None
        
        # Salva ou atualiza os dados específicos deste servidor (Guild ID)
        await collection.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"titulo": titulo_msg.content, "banner": banner_url}},
            upsert=True
        )
        await ctx.send(f"✅ 『PSX』 Configuração finalizada para **{ctx.guild.name}**! Use `/setup_ticket` para ver o resultado.")
        
    except asyncio.TimeoutError:
        await ctx.send("⏰ 『PSX』 Tempo esgotado. Tente o comando `!rr` novamente.")

# --- 6. EXECUÇÃO DO SISTEMA ---
async def main():
    port = int(os.environ.get("PORT", 10000))
    if not TOKEN:
        print("❌ 『PSX』 ERRO CRÍTICO: DISCORD_TOKEN não encontrado!")
        return
    
    await asyncio.gather(
        bot.start(TOKEN),
        app.run_task(host="0.0.0.0", port=port)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    
