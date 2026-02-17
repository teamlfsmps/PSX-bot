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
        print(f"✅ 『PSX』 Comandos sincronizados.")

bot = MyBot()

# --- 2. SISTEMA DE AVALIAÇÃO ---
class FeedbackModal(ui.Modal):
    def __init__(self, nota, user_name, guild_id):
        super().__init__(title="『PSX』 Feedback")
        self.nota = nota
        self.user_name = user_name
        self.guild_id = guild_id
    
    comentario = ui.TextInput(label='O que achou?', style=discord.TextStyle.paragraph, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        dados = await collection.find_one({"_id": self.guild_id})
        await interaction.response.send_message(f"『PSX』 Obrigado pela avaliação!", ephemeral=True)
        
        log_id = dados.get('log_id') if dados else None
        if log_id:
            canal = bot.get_channel(int(log_id))
            if canal:
                embed = discord.Embed(title="📥 Nova Avaliação", color=discord.Color.green())
                embed.add_field(name="Membro", value=self.user_name)
                embed.add_field(name="Nota", value=f"{self.nota} ⭐")
                embed.add_field(name="Comentário", value=self.comentario.value or "Nenhum")
                await canal.send(embed=embed)

class EvalDropdown(ui.Select):
    def __init__(self, user_name, guild_id):
        self.user_name = user_name
        self.guild_id = guild_id
        options = [discord.SelectOption(label=f"{i} Estrelas", value=str(i)) for i in range(5, 0, -1)]
        super().__init__(placeholder="Avalie o atendimento aqui", options=options)

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
        view_eval = ui.View(); view_eval.add_item(EvalDropdown(user.name, self.guild_id))
        try: await user.send(content="『PSX』 Seu ticket foi fechado. Avalie-nos:", view=view_eval)
        except: pass
        await interaction.channel.delete()

class TicketModal(ui.Modal, title='『PSX』 Abrir Suporte'):
    def __init__(self, categoria, guild_id):
        super().__init__()
        self.categoria = categoria
        self.guild_id = guild_id
    motivo = ui.TextInput(label='Motivo do contato', style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True), guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        channel = await guild.create_text_channel(name=f'ticket-{interaction.user.name}', overwrites=overwrites)
        emb = discord.Embed(title="🎫 Suporte 『PSX』", description=f"**Categoria:** {self.categoria}\n**Motivo:** {self.motivo.value}", color=discord.Color.blue())
        await channel.send(content=interaction.user.mention, embed=emb, view=CloseTicketView(self.guild_id))
        await interaction.response.send_message(f"✅ Criado: {channel.mention}", ephemeral=True)

class TicketView(ui.View):
    def __init__(self, guild_id, categorias):
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=c['nome'], description=c['desc'][:100]) for c in categorias]
        select = ui.Select(placeholder="Escolha uma categoria...", options=options)
        async def callback(interaction):
            await interaction.response.send_modal(TicketModal(select.values[0], guild_id))
        select.callback = callback
        self.add_item(select)

# --- 4. COMANDO !RR (FIX BUG BANNER) ---
@bot.command()
@commands.has_permissions(administrator=True)
async def rr(ctx):
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        await ctx.send("⚙️ 『PSX』 **1° Etapa** - ID do canal de logs:")
        msg_log = await bot.wait_for('message', check=check, timeout=60)
        
        await ctx.send("⚙️ 『PSX』 **2° Etapa** - Texto do Painel:")
        msg_texto = await bot.wait_for('message', check=check, timeout=120)

        await ctx.send("⚙️ 『PSX』 **3° Etapa** - Categorias (`Nome|Desc#Nome|Desc`):")
        msg_cats = await bot.wait_for('message', check=check, timeout=180)
        
        cats = []
        for p in msg_cats.content.split('#'):
            if '|' in p:
                n, d = p.split('|')
                cats.append({'nome': n.strip(), 'desc': d.strip()})

        await ctx.send("⚙️ 『PSX』 **4° Etapa** - Link do Banner ou `skip`:")
        msg_banner = await bot.wait_for('message', check=check, timeout=60)
        
        banner = None
        if msg_banner.content.lower() not in ['skip', 'pular']:
            banner = msg_banner.attachments[0].url if msg_banner.attachments else msg_banner.content

        # SALVAMENTO GARANTIDO NO MONGO
        await collection.update_one(
            {"_id": ctx.guild.id},
            {"$set": {'log_id': msg_log.content, 'texto': msg_texto.content, 'categorias': cats, 'banner': banner}},
            upsert=True
        )
        await ctx.send("✅ 『PSX』 **Configuração salva com sucesso!** Use `/setup_painel`.")
    except Exception as e:
        await ctx.send(f"❌ Erro na configuração: {e}")

# --- 5. COMANDOS SLASH ---
@bot.tree.command(name="setup_painel", description="『PSX』 Envia o painel de atendimento.")
async def setup_painel(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
        dados = await collection.find_one({"_id": interaction.guild_id})
        
        if not dados:
            return await interaction.followup.send("❌ Use `!rr` primeiro para configurar o servidor!")

        txt = dados.get('texto', "Suporte")
        banner = dados.get('banner')
        cats = dados.get('categorias', [{'nome': 'Geral', 'desc': 'Suporte'}])

        embed = discord.Embed(title="『PSX』 ATENDIMENTO", description=txt, color=discord.Color.blue())
        if banner and banner.startswith("http"): embed.set_image(url=banner)
        
        await interaction.channel.send(embed=embed, view=TicketView(interaction.guild_id, cats))
        await interaction.followup.send("✅ Painel enviado!")
    except Exception as e:
        print(f"Erro no setup: {e}")

@bot.tree.command(name="ajuda", description="『PSX』 Comandos do bot.")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(title="✨ Central 『PSX』", color=discord.Color.gold())
    embed.add_field(name="Comandos", value="`/setup_painel`\n`!rr` (Config)\n`/ping`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="『PSX』 Latência.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 `{round(bot.latency * 1000)}ms`", ephemeral=True)

# --- 6. START ---
@app.route('/')
async def home(): return await render_template('index.html')

async def main():
    port = int(os.environ.get("PORT", 10000))
    await asyncio.gather(bot.start(TOKEN), app.run_task(host="0.0.0.0", port=port))

if __name__ == "__main__":
    asyncio.run(main())
                                      
