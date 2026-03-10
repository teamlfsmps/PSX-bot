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
MONGO_URL = "SUA_URL_DO_MONGODB_AQUI" 

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
        print(f"✅ 『PSX』 Sistema Sincronizado.")

bot = MyBot()

# --- TRANSCRIÇÃO ---
async def generate_transcript(channel):
    transcript = f"--- Transcrição do Ticket: {channel.name} ---\n"
    async for message in channel.history(limit=None, oldest_first=True):
        time = message.created_at.strftime('%H:%M:%S')
        transcript += f"[{time}] {message.author}: {message.content}\n"
    return io.BytesIO(transcript.encode('utf-8'))

# --- AVALIAÇÃO ---
class FeedbackModal(ui.Modal):
    def __init__(self, nota, log_id):
        super().__init__(title="『PSX』 Avaliação")
        self.nota = int(nota)
        self.log_id = log_id
    comentario = ui.TextInput(label='Feedback:', style=discord.TextStyle.paragraph, required=False)
    async def on_submit(self, interaction: discord.Interaction):
        canal = bot.get_channel(int(self.log_id))
        if canal:
            embed = discord.Embed(title="📥 Nova Avaliação", color=0x00FF00 if self.nota > 2 else 0xFF0000)
            embed.add_field(name="Membro", value=interaction.user.mention)
            embed.add_field(name="Nota", value="⭐" * self.nota)
            embed.add_field(name="Comentário", value=self.comentario.value or "Nenhum")
            await canal.send(embed=embed)
        await interaction.response.send_message("Obrigado!", ephemeral=True)

class EvalView(ui.View):
    def __init__(self, log_id):
        super().__init__(timeout=None)
        self.log_id = log_id
    @ui.select(placeholder="Avalie de 1 a 5 estrelas", options=[discord.SelectOption(label=f"{i} Estrelas", value=str(i), emoji="⭐") for i in range(5, 0, -1)])
    async def callback(self, interaction: discord.Interaction, select: ui.Select):
        await interaction.response.send_modal(FeedbackModal(select.values[0], self.log_id))

# --- TICKET CORE ---
class TicketActions(ui.View):
    def __init__(self, log_id):
        super().__init__(timeout=None)
        self.log_id = log_id
    @ui.button(label="Reivindicar", style=discord.ButtonStyle.success)
    async def claim(self, interaction: discord.Interaction, button: ui.Button):
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"O staff {interaction.user.mention} assumiu o ticket!")
    @ui.button(label="Fechar", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Fechando...")
        log_ch = bot.get_channel(int(self.log_id))
        if log_ch:
            file_data = await generate_transcript(interaction.channel)
            await log_ch.send(file=discord.File(file_data, filename=f"log-{interaction.channel.name}.txt"))
        try: await interaction.user.send(view=EvalView(self.log_id))
        except: pass
        await asyncio.sleep(3); await interaction.channel.delete()

class TicketView(ui.View):
    def __init__(self, config):
        super().__init__(timeout=None)
        self.config = config
        opts = [discord.SelectOption(label=c['nome'], description=c['desc']) for c in config['categorias']]
        select = ui.Select(options=opts)
        async def cb(interaction):
            ch = await interaction.guild.create_text_channel(name=f"ticket-{interaction.user.name}", overwrites={interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False), interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)})
            emb = discord.Embed(title="Suporte", description=self.config['info_pos'], color=0x5865F2)
            await ch.send(content=interaction.user.mention, embed=emb, view=TicketActions(self.config['log_id']))
            await interaction.response.send_message(f"Aberto em {ch.mention}", ephemeral=True)
        select.callback = cb; self.add_item(select)

# --- CONFIGURAÇÃO !RR ---
@bot.command()
@commands.has_permissions(administrator=True)
async def rr(ctx):
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        await ctx.send("『PSX』 **1- Descrição:**")
        desc = (await bot.wait_for('message', check=check, timeout=60)).content
        await ctx.send("『PSX』 **2- Banner (Link ou skip):**")
        banner = (await bot.wait_for('message', check=check)).content
        await ctx.send("『PSX』 **3- Thumbnail (Link ou skip):**")
        thumb = (await bot.wait_for('message', check=check)).content
        await ctx.send("『PSX』 **4- Footer:**")
        foot = (await bot.wait_for('message', check=check)).content
        await ctx.send("『PSX』 **5- Categorias (Nome#Desc | Nome#Desc):**")
        raw = (await bot.wait_for('message', check=check)).content
        cats = [{'nome': x.split('#')[0].strip(), 'desc': x.split('#')[1].strip()} for x in raw.split('|') if '#' in x]
        await ctx.send("『PSX』 **6- Info Pós-Abertura:**")
        info = (await bot.wait_for('message', check=check)).content
        await ctx.send("『PSX』 **7- ID do Canal de Log:**")
        log_id = (await bot.wait_for('message', check=check)).content

        # SALVAMENTO
        data = {"desc": desc, "banner": banner, "thumb": thumb, "footer": foot, "categorias": cats, "info_pos": info, "log_id": log_id}
        await collection.update_one({"_id": ctx.guild.id}, {"$set": data}, upsert=True)
        
        # MENSAGEM FINAL QUE ESTAVA FALTANDO
        await ctx.send("✅ **『PSX』 Você terminou as configurações!** Agora use `/setup_painel` para enviar o painel.")
    except Exception as e: await ctx.send(f"❌ Erro: {e}")

@bot.tree.command(name="setup_painel")
async def setup_painel(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True) # Evita o erro de "aplicativo não respondeu"
    dados = await collection.find_one({"_id": interaction.guild_id})
    if not dados: return await interaction.followup.send("Rode !rr primeiro!")
    
    embed = discord.Embed(title="Atendimento", description=dados['desc'], color=0x5865F2)
    if dados['banner'].lower() != 'skip': embed.set_image(url=dados['banner'])
    if dados['thumb'].lower() != 'skip': embed.set_thumbnail(url=dados['thumb'])
    embed.set_footer(text=dados['footer'])
    
    await interaction.channel.send(embed=embed, view=TicketView(dados))
    await interaction.followup.send("Painel enviado!")

@app.route('/')
async def home(): return "Online"

async def main():
    await asyncio.gather(bot.start(TOKEN), app.run_task(host="0.0.0.0", port=10000))

if __name__ == "__main__":
    asyncio.run(main())
        
