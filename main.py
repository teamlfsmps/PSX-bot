import discord
from discord.ext import commands
from discord import ui, app_commands
import os, asyncio, datetime, io
from motor.motor_asyncio import AsyncIOMotorClient
from quart import Quart

TOKEN = os.environ.get('DISCORD_TOKEN')
MONGO_URL = "mongodb+srv://PSX:psx2026@cluster0.dbttxsf.mongodb.net/?retryWrites=true&w=majority"

app = Quart(__name__)
cluster = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=10000)
db = cluster["psx_bot"]
collection = db["config_tickets"]

intents = discord.Intents.all() 

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, help_command=None)
    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ Sistema PSX Sincronizado.")

bot = MyBot()

def get_url(message):
    if message.attachments: return message.attachments[0].url
    return message.content

async def generate_transcript(channel):
    transcript = f"--- Transcrição PSX: {channel.name} ---\n"
    async for msg in channel.history(limit=None, oldest_first=True):
        transcript += f"[{msg.created_at.strftime('%H:%M')}] {msg.author}: {msg.content}\n"
    return io.BytesIO(transcript.encode('utf-8'))

class FeedbackModal(ui.Modal):
    def __init__(self, nota, log_id):
        super().__init__(title="『PSX』 Avaliação")
        self.nota, self.log_id = int(nota), log_id
    coment = ui.TextInput(label='O que achou?', style=discord.TextStyle.paragraph, required=False)
    async def on_submit(self, it: discord.Interaction):
        canal = bot.get_channel(int(self.log_id))
        if canal:
            emb = discord.Embed(title="⭐ Nova Avaliação", color=0x00FF00 if self.nota > 2 else 0xFF0000)
            emb.add_field(name="Nota", value="⭐" * self.nota)
            emb.add_field(name="💬 Feedback", value=self.coment.value or "Vazio")
            await canal.send(embed=emb)
        await it.response.send_message("Obrigado!", ephemeral=True)

class EvalView(ui.View):
    def __init__(self, log_id):
        super().__init__(timeout=None)
        self.log_id = log_id
    @ui.select(placeholder="Avalie de 1 a 5 estrelas", options=[discord.SelectOption(label=f"{i} Estrelas", value=str(i), emoji="⭐") for i in range(5, 0, -1)])
    async def callback(self, it, select):
        await it.response.send_modal(FeedbackModal(select.values[0], self.log_id))

class TicketActions(ui.View):
    def __init__(self, log_id):
        super().__init__(timeout=None)
        self.log_id = log_id
    @ui.button(label="Reivindicar", style=discord.ButtonStyle.success, emoji="🙋‍♂️")
    async def claim(self, it, button):
        button.disabled = True
        button.label = f"Por: {it.user.name}"
        await it.response.edit_message(view=self)
    @ui.button(label="Fechar", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, it, button):
        await it.response.send_message("🔒 Fechando canal...", ephemeral=True)
        log_ch = bot.get_channel(int(self.log_id))
        if log_ch:
            file = await generate_transcript(it.channel)
            await log_ch.send(content=f"Log: {it.channel.name}", file=discord.File(file, filename="log.txt"))
        try: await it.user.send(view=EvalView(self.log_id))
        except: pass
        await asyncio.sleep(2); await it.channel.delete()

class TicketView(ui.View):
    def __init__(self, config):
        super().__init__(timeout=None)
        self.config = config
        # Adicionando um índice (i) para garantir que cada valor seja único no Discord
        opts = [discord.SelectOption(label=c['nome'], description=c['desc'], value=f"cat_{i}") for i, c in enumerate(config['categorias'])]
        select = ui.Select(placeholder="Selecione uma categoria...", options=opts)
        
        async def cb(it: discord.Interaction):
            # Descobrir qual categoria foi clicada usando o ID
            idx = int(it.data['values'][0].split('_')[1])
            categoria_nome = self.config['categorias'][idx]['nome']
            
            ch = await it.guild.create_text_channel(name=f"{categoria_nome}-{it.user.name}", overwrites={
                it.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                it.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                it.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            })
            emb = discord.Embed(title="Suporte Solicitado", description=self.config['info_pos'], color=0x5865F2)
            await ch.send(content=f"{it.user.mention} | Suporte para: **{categoria_nome}**", embed=emb, view=TicketActions(self.config['log_id']))
            await it.response.send_message(f"✅ Ticket criado: {ch.mention}", ephemeral=True)
        
        select.callback = cb
        self.add_item(select)

@bot.command()
@commands.has_permissions(administrator=True)
async def rr(ctx):
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        await ctx.send("1- Descrição do Painel:")
        desc = (await bot.wait_for('message', check=check)).content
        await ctx.send("2- Banner (Link ou Skip):")
        banner = get_url(await bot.wait_for('message', check=check))
        await ctx.send("3- Thumbnail (Link ou Skip):")
        thumb = get_url(await bot.wait_for('message', check=check))
        await ctx.send("4- Rodapé:")
        foot = (await bot.wait_for('message', check=check)).content
        await ctx.send("5- Categorias (Nome#Descrição | Nome#Descrição):")
        raw = (await bot.wait_for('message', check=check)).content
        cats = [{'nome': x.split('#')[0].strip(), 'desc': x.split('#')[1].strip()} for x in raw.split('|') if '#' in x]
        await ctx.send("6- Texto após abrir ticket:")
        info = (await bot.wait_for('message', check=check)).content
        await ctx.send("7- ID do canal de Log/Avaliações:")
        log_id = (await bot.wait_for('message', check=check)).content

        await collection.update_one({"_id": ctx.guild.id}, {"$set": {"desc": desc, "banner": banner, "thumb": thumb, "footer": foot, "categorias": cats, "info_pos": info, "log_id": log_id}}, upsert=True)
        await ctx.send("✅ Configurações salvas! Use `/setup_painel`.")
    except Exception as e: await ctx.send(f"❌ Erro ao salvar: {e}")

@bot.tree.command(name="setup_painel", description="Envia o painel de tickets.")
async def setup_painel(it: discord.Interaction):
    await it.response.defer(ephemeral=True) 
    try:
        dados = await collection.find_one({"_id": it.guild_id})
        if not dados: return await it.followup.send("Rode !rr primeiro!")
        
        emb = discord.Embed(title="Central de Atendimento", description=dados['desc'], color=0x5865F2)
        if dados['banner'].lower() != 'skip': emb.set_image(url=dados['banner'])
        if dados['thumb'].lower() != 'skip': emb.set_thumbnail(url=dados['thumb'])
        emb.set_footer(text=dados['footer'])
        
        await it.channel.send(embed=emb, view=TicketView(dados))
        await it.followup.send("✅ Painel enviado!")
    except Exception as e:
        await it.followup.send(f"❌ Erro no painel: {e}")

@app.route('/')
async def home(): return "PSX Ticket Online"

async def main():
    await asyncio.gather(bot.start(TOKEN), app.run_task(host="0.0.0.0", port=10000))

if __name__ == "__main__":
    asyncio.run(main())
        
