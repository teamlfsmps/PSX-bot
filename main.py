import discord
from discord.ext import commands
from discord import ui, app_commands
import os
import asyncio
import datetime
import io
from motor.motor_asyncio import AsyncIOMotorClient
from quart import Quart

# --- CONFIGURAÇÃO ---
TOKEN = os.environ.get('DISCORD_TOKEN')
MONGO_URL = "SUA_URL_DO_MONGODB_AQUI" # Substitua pela sua URL

app = Quart(__name__)
cluster = AsyncIOMotorClient(MONGO_URL)
db = cluster["psx_bot"]
collection = db["config_tickets"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, help_command=None)
    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ 『PSX』 Comandos e Transcrições Sincronizados.")

bot = MyBot()

# --- FUNÇÃO DE TRANSCRIÇÃO ---
async def generate_transcript(channel):
    transcript = f"--- Transcrição do Ticket: {channel.name} ---\n"
    transcript += f"Data de Fechamento: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
    
    messages = []
    async for message in channel.history(limit=None, oldest_first=True):
        time = message.created_at.strftime('%H:%M:%S')
        content = message.content if message.content else "[Imagem/Anexo]"
        messages.append(f"[{time}] {message.author}: {content}")
    
    transcript += "\n".join(messages)
    return io.BytesIO(transcript.encode('utf-8'))

# --- AVALIAÇÃO E FEEDBACK ---
class FeedbackModal(ui.Modal):
    def __init__(self, nota, log_id):
        super().__init__(title="『PSX』 Feedback do Atendimento")
        self.nota = int(nota)
        self.log_id = log_id
    
    comentario = ui.TextInput(label='O que achou do nosso suporte?', style=discord.TextStyle.paragraph, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        msg = "『PSX』 Sentimos muito. Vamos melhorar! 😔" if self.nota <= 2 else "『PSX』 Obrigado pelo feedback positivo! 🥰"
        await interaction.response.send_message(msg, ephemeral=True)
        
        canal_log = bot.get_channel(int(self.log_id))
        if canal_log:
            embed = discord.Embed(title="📥 Nova Avaliação Recebida", color=0x00FF00 if self.nota > 2 else 0xFF0000)
            embed.add_field(name="👤 Membro", value=f"{interaction.user.mention}", inline=True)
            embed.add_field(name="⭐ Nota", value=f"{'⭐' * self.nota}", inline=True)
            embed.add_field(name="💬 Feedback", value=self.comentario.value or "Sem comentário.", inline=False)
            await canal_log.send(embed=embed)

class EvalView(ui.View):
    def __init__(self, log_id):
        super().__init__(timeout=None)
        self.log_id = log_id

    @ui.select(placeholder="⭐ Avalie nosso suporte...", options=[
        discord.SelectOption(label="5 Estrelas", value="5", emoji="⭐"),
        discord.SelectOption(label="4 Estrelas", value="4", emoji="⭐"),
        discord.SelectOption(label="3 Estrelas", value="3", emoji="⭐"),
        discord.SelectOption(label="2 Estrelas", value="2", emoji="⭐"),
        discord.SelectOption(label="1 Estrela", value="1", emoji="⭐"),
    ])
    async def select_callback(self, interaction: discord.Interaction, select: ui.Select):
        await interaction.response.send_modal(FeedbackModal(select.values[0], self.log_id))

# --- AÇÕES DO TICKET (CLAIM, CLOSE & TRANSCRIPT) ---
class TicketActions(ui.View):
    def __init__(self, log_id, info_pos):
        super().__init__(timeout=None)
        self.log_id = log_id
        self.info_pos = info_pos

    @ui.button(label="Reivindicar", style=discord.ButtonStyle.success, emoji="🙋‍♂️")
    async def claim(self, interaction: discord.Interaction, button: ui.Button):
        button.disabled = True
        button.label = "Reivindicado"
        embed = interaction.message.embeds[0]
        embed.add_field(name="⚙️ Staff Responsável", value=interaction.user.mention, inline=False)
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(f"『PSX』 O staff {interaction.user.mention} assumiu este ticket!")

    @ui.button(label="Fechar", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("『PSX』 Gerando transcrição e fechando canal...")
        
        # Gera e envia transcrição para os logs
        canal_log = bot.get_channel(int(self.log_id))
        if canal_log:
            file_data = await generate_transcript(interaction.channel)
            file = discord.File(file_data, filename=f"transcript-{interaction.channel.name}.txt")
            embed_log = discord.Embed(title="🔒 Ticket Encerrado", color=0x2F3136)
            embed_log.add_field(name="Canal", value=interaction.channel.name)
            embed_log.add_field(name="Fechado por", value=interaction.user.mention)
            await canal_log.send(embed=embed_log, file=file)
        
        try:
            eval_embed = discord.Embed(title="Ticket Encerrado", description="Sua opinião é importante! Avalie abaixo:", color=0x5865F2)
            await interaction.user.send(embed=eval_embed, view=EvalView(self.log_id))
        except: pass
        
        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- TICKET CORE ---
class TicketView(ui.View):
    def __init__(self, config):
        super().__init__(timeout=None)
        self.config = config
        options = [discord.SelectOption(label=c['nome'], description=c['desc']) for c in config['categorias']]
        select = ui.Select(placeholder="Escolha uma categoria abaixo...", options=options)
        async def callback(interaction):
            guild = interaction.guild
            cat_name = select.values[0]
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            channel = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", overwrites=overwrites)
            emb = discord.Embed(title="『PSX』 Suporte", description=self.config['info_pos'], color=0x5865F2)
            emb.add_field(name="🎫 Categoria", value=cat_name, inline=True)
            emb.add_field(name="👤 Autor", value=interaction.user.mention, inline=True)
            if self.config['thumb'].lower() != 'skip': emb.set_thumbnail(url=self.config['thumb'])
            await channel.send(content=f"||{interaction.user.mention}||", embed=emb, view=TicketActions(self.config['log_id'], self.config['info_pos']))
            await interaction.response.send_message(f"✅ Aberto em {channel.mention}", ephemeral=True)
        select.callback = callback
        self.add_item(select)

# --- COMANDO CONFIG !RR ---
@bot.command()
@commands.has_permissions(administrator=True)
async def rr(ctx):
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        await ctx.send("『PSX』 **1-** Descrição do painel:")
        desc = (await bot.wait_for('message', check=check)).content
        await ctx.send("『PSX』 **2-** Link do Banner (ou `skip`):")
        banner = (await bot.wait_for('message', check=check)).content
        await ctx.send("『PSX』 **2.1-** Thumbnail canto superior (ou `skip`):")
        thumb = (await bot.wait_for('message', check=check)).content
        await ctx.send("『PSX』 **3-** Texto do rodapé (footer):")
        footer = (await bot.wait_for('message', check=check)).content
        await ctx.send("『PSX』 **4-** Categorias (`Nome#Descrição | Nome#Descrição`):")
        raw = (await bot.wait_for('message', check=check)).content
        cats = [{'nome': x.split('#')[0].strip(), 'desc': x.split('#')[1].strip()} for x in raw.split('|') if '#' in x]
        await ctx.send("『PSX』 **5-** Info pós-abertura (ex: mencionar cargo):")
        info = (await bot.wait_for('message', check=check)).content
        await ctx.send("『PSX』 **6-** ID do canal de logs (Avaliações e Transcrições):")
        log_id = (await bot.wait_for('message', check=check)).content

        await collection.update_one({"_id": ctx.guild.id}, {"$set": {"desc": desc, "banner": banner, "thumb": thumb, "footer": footer, "categorias": cats, "info_pos": info, "log_id": log_id}}, upsert=True)
        await ctx.send("✅ Configuração finalizada! Use `/setup_painel`.")
    except Exception as e: await ctx.send(f"❌ Erro: {e}")

@bot.tree.command(name="setup_painel", description="Envia o painel de tickets 『PSX』")
async def setup_painel(interaction: discord.Interaction):
    dados = await collection.find_one({"_id": interaction.guild_id})
    if not dados: return await interaction.response.send_message("Rode `!rr` primeiro!", ephemeral=True)
    embed = discord.Embed(title="Central de Atendimento", description=dados['desc'], color=0x5865F2)
    if dados['banner'].lower() != 'skip': embed.set_image(url=dados['banner'])
    if dados['thumb'].lower() != 'skip': embed.set_thumbnail(url=dados['thumb'])
    embed.set_footer(text=dados['footer'])
    await interaction.channel.send(embed=embed, view=TicketView(dados))
    await interaction.response.send_message("Painel Enviado!", ephemeral=True)

@app.route('/')
async def home(): return "PSX Bot Online"

async def main():
    await asyncio.gather(bot.start(TOKEN), app.run_task(host="0.0.0.0", port=10000))

if __name__ == "__main__":
    asyncio.run(main())
        
