import discord
from discord.ext import commands
from discord import ui, app_commands
import datetime
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from quart import Quart, render_template

# --- 1. CONFIGURAÇÕES E BANCO DE DATOS ---
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
        print(f"✅ 『PSX』 Sistema sincronizado para {self.user}")

bot = MyBot()

# --- 2. SISTEMA DE AVALIAÇÃO COM FEEDBACK ---
class FeedbackModal(ui.Modal):
    def __init__(self, nota, user_name, guild_id):
        super().__init__(title="『PSX』 Feedback do Atendimento")
        self.nota = nota
        self.user_name = user_name
        self.guild_id = guild_id
    
    comentario = ui.TextInput(label='O que achou do atendimento?', style=discord.TextStyle.paragraph, placeholder='Escreva aqui seu comentário (opcional)...', required=False)

    async def on_submit(self, interaction: discord.Interaction):
        dados = await collection.find_one({"_id": self.guild_id})
        msg = f"『PSX』 Obrigado pelo feedback de {self.nota} estrelas, {self.user_name}! 🥰" if int(self.nota) >= 3 else f"『PSX』 Sentimos muito, {self.user_name}. Vamos melhorar! 😔"
        await interaction.response.send_message(msg, ephemeral=True)

        log_id = int(dados['log_id']) if dados and dados.get('log_id') else None
        canal = bot.get_channel(log_id)
        if canal:
            cor = discord.Color.green() if int(self.nota) >= 3 else discord.Color.red()
            embed = discord.Embed(title="📥 Nova Avaliação Recebida", color=cor, timestamp=datetime.datetime.now())
            embed.add_field(name="Membro", value=self.user_name, inline=True)
            embed.add_field(name="Nota", value=f"{self.nota} ⭐", inline=True)
            embed.add_field(name="Feedback", value=self.comentario.value or "Sem comentário.", inline=False)
            await canal.send(embed=embed)

class EvalDropdown(ui.Select):
    def __init__(self, user_name, guild_id):
        self.user_name = user_name
        self.guild_id = guild_id
        options = [discord.SelectOption(label=f"{i} Estrelas", value=str(i), emoji="⭐") for i in range(5, 0, -1)]
        super().__init__(placeholder="Selecione sua nota aqui...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(FeedbackModal(self.values[0], self.user_name, self.guild_id))

# --- 3. SISTEMA DE TICKETS ---
class CloseTicketView(ui.View):
    def __init__(self, guild_id): 
        super().__init__(timeout=None)
        self.guild_id = guild_id
    
    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.user
        embed_fin = discord.Embed(title="『PSX』 Ticket Finalizado", description=f"🔒 **Fechado por:** {user.mention}\n\nPor favor, avalie nosso suporte abaixo:", color=discord.Color.red())
        
        view_eval = ui.View(); view_eval.add_item(EvalDropdown(user.name, self.guild_id))
        try: await user.send(embed=embed_fin, view=view_eval)
        except: pass
        await interaction.channel.delete()

class TicketModal(ui.Modal, title='『PSX』 Formulário de Suporte'):
    def __init__(self, categoria, guild_id):
        super().__init__()
        self.categoria = categoria
        self.guild_id = guild_id
    motivo = ui.TextInput(label='Qual o motivo do contato?', style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True), guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        channel = await guild.create_text_channel(name=f'ticket-{interaction.user.name}', overwrites=overwrites)
        
        emb = discord.Embed(title="🎫 Suporte 『PSX』", description=f"Olá {interaction.user.mention}!\n\n**📂 Categoria:** {self.categoria}\n**📝 Motivo:** {self.motivo.value}", color=discord.Color.blue())
        await channel.send(content=interaction.user.mention, embed=emb, view=CloseTicketView(self.guild_id))
        await interaction.response.send_message(f"✅ 『PSX』 Ticket criado em {channel.mention}", ephemeral=True)

class TicketView(ui.View):
    def __init__(self, guild_id, categorias):
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=c['nome'], description=c['desc'][:100]) for c in categorias]
        select = ui.Select(placeholder="Escolha uma categoria...", options=options)
        async def callback(interaction):
            await interaction.response.send_modal(TicketModal(select.values[0], guild_id))
        select.callback = callback
        self.add_item(select)

# --- 4. COMANDO DE CONFIGURAÇÃO !RR ---
@bot.command()
@commands.has_permissions(administrator=True)
async def rr(ctx):
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        await ctx.send("⚙️ 『PSX』 **1° Etapa** - Diga o **ID do canal de logs** de avaliações:")
        msg_log = await bot.wait_for('message', check=check, timeout=60)
        
        await ctx.send("⚙️ 『PSX』 **2° Etapa** - Diga o **Texto do Painel** (Ex: Olá, escolha uma opção...):")
        msg_texto = await bot.wait_for('message', check=check, timeout=120)

        await ctx.send("⚙️ 『PSX』 **3° Etapa** - Diga as **Categorias** (`Nome | Descrição # Nome | Descrição`):")
        msg_cats = await bot.wait_for('message', check=check, timeout=180)
        
        cats = []
        for p in msg_cats.content.split('#'):
            if '|' in p:
                nome, desc = p.split('|')
                cats.append({'nome': nome.strip(), 'desc': desc.strip()})

        await ctx.send("⚙️ 『PSX』 **4° Etapa** - Mande o **Link do Banner** ou digite `skip`:")
        msg_banner = await bot.wait_for('message', check=check, timeout=60)
        banner = None
        if msg_banner.content.lower() != 'skip':
            # Pega o link do texto ou do anexo se houver
            banner = msg_banner.attachments[0].url if msg_banner.attachments else msg_banner.content

        await collection.update_one(
            {"_id": ctx.guild.id},
            {"$set": {'log_id': msg_log.content, 'texto': msg_texto.content, 'categorias': cats, 'banner': banner}},
            upsert=True
        )
        await ctx.send("✅ 『PSX』 **Configuração salva!** Use `/setup_painel` para ativar.")
    except asyncio.TimeoutError:
        await ctx.send("❌ 『PSX』 Tempo esgotado.")

# --- 5. COMANDOS DE BARRA (SLASH COMMANDS) ---
@bot.tree.command(name="setup_painel", description="『PSX』 Envia o painel de atendimento configurado para os membros.")
async def setup_painel(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    dados = await collection.find_one({"_id": interaction.guild_id})
    
    txt = dados['texto'] if dados else "Selecione uma categoria para iniciar o suporte."
    banner = dados['banner'] if dados else None
    cats = dados['categorias'] if dados else [{'nome': 'Suporte', 'desc': 'Geral'}]

    embed = discord.Embed(title="『PSX』 CENTRAL DE ATENDIMENTO", description=txt, color=discord.Color.blue())
    if banner: embed.set_image(url=banner)
    embed.set_footer(text="Atendimento Profissional via PSX")
    
    await interaction.channel.send(embed=embed, view=TicketView(interaction.guild_id, cats))
    await interaction.followup.send("✅ 『PSX』 Painel enviado!", ephemeral=True)

@bot.tree.command(name="ajuda", description="『PSX』 Exibe a lista detalhada de comandos e como configurar o bot.")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(title="✨ Central de Informações 『PSX』", color=discord.Color.gold())
    embed.add_field(name="🎫 **Atendimento**", value="`/setup_painel` - Envia o menu de tickets\n`!rr` - Configura categorias e logs", inline=False)
    embed.add_field(name="⚙️ **Outros**", value="`/ping` - Velocidade do bot\n`/ajuda` - Este menu", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="『PSX』 Verifica a latência de conexão em milissegundos.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 『PSX』 **Pong!** `{round(bot.latency * 1000)}ms`", ephemeral=True)

# --- 6. SERVIDOR WEB E START ---
@app.route('/')
async def home(): return await render_template('index.html')

async def main():
    port = int(os.environ.get("PORT", 10000))
    await asyncio.gather(bot.start(TOKEN), app.run_task(host="0.0.0.0", port=port))

if __name__ == "__main__":
    asyncio.run(main())
        
