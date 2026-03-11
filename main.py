import discord
from discord.ext import commands
from discord import ui, app_commands
import os, asyncio, datetime, io
from motor.motor_asyncio import AsyncIOMotorClient
from quart import Quart

# --- CONFIGURAÇÃO ---
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
        print(f"✅ Sistema PSX v4.0 Ativo")

bot = MyBot()

# --- UTILITÁRIOS ---
async def generate_transcript(channel):
    transcript = f"--- RELATÓRIO DE ATENDIMENTO PSX ---\nCanal: {channel.name}\n\n"
    async for msg in channel.history(limit=None, oldest_first=True):
        time = msg.created_at.strftime('%H:%M')
        content = msg.content if msg.content else "[Anexo/Embed]"
        transcript += f"[{time}] {msg.author}: {content}\n"
    return io.BytesIO(transcript.encode('utf-8'))

# --- SISTEMA DE FEEDBACK ---
class FeedbackModal(ui.Modal):
    def __init__(self, nota, log_id, user_id):
        super().__init__(title="Deixe seu Feedback")
        self.nota, self.log_id, self.user_id = int(nota), log_id, user_id
    coment = ui.TextInput(label="O que podemos melhorar?", style=discord.TextStyle.paragraph, required=False)
    async def on_submit(self, it: discord.Interaction):
        log_ch = bot.get_channel(int(self.log_id))
        if self.nota <= 2:
            msg_cliente, status_log, color = "😔 Lamentamos o ocorrido. Vamos melhorar!", "⚠️ Avaliação Negativa", 0xFF0000
        else:
            msg_cliente, status_log, color = "🥰 Ficamos felizes que gostou!", "⭐ Avaliação Positiva", 0x00FF00
        if log_ch:
            emb = discord.Embed(title=status_log, color=color, timestamp=datetime.datetime.now())
            emb.add_field(name="👤 Cliente", value=f"<@{self.user_id}>", inline=True)
            emb.add_field(name="⭐ Nota", value="★" * self.nota, inline=True)
            emb.add_field(name="💬 Comentário", value=self.coment.value or "Nenhum", inline=False)
            await log_ch.send(embed=emb)
        await it.response.send_message(msg_cliente, ephemeral=True)

class EvalView(ui.View):
    def __init__(self, log_id, user_id):
        super().__init__(timeout=None)
        self.log_id, self.user_id = log_id, user_id
    @ui.select(placeholder="Avalie o suporte (1-5 estrelas)", options=[discord.SelectOption(label="⭐"*i, value=str(i)) for i in range(5, 0, -1)])
    async def callback(self, it, select):
        await it.response.send_modal(FeedbackModal(select.values[0], self.log_id, self.user_id))

# --- BOTÕES DO TICKET ---
class TicketActions(ui.View):
    def __init__(self, log_id, owner_id):
        super().__init__(timeout=None)
        self.log_id, self.owner_id = log_id, owner_id
    @ui.button(label="Reivindicar", style=discord.ButtonStyle.success, emoji="🙋‍♂️")
    async def claim(self, it, button):
        overwrites = {it.guild.default_role: discord.PermissionOverwrite(read_messages=False), it.guild.get_member(self.owner_id): discord.PermissionOverwrite(read_messages=True, send_messages=True), it.user: discord.PermissionOverwrite(read_messages=True, send_messages=True), it.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        await it.channel.edit(overwrites=overwrites)
        button.disabled = True
        button.label = f"Staff: {it.user.name}"
        await it.response.edit_message(view=self)
        await it.channel.send(f"✅ **Ticket reivindicado por {it.user.mention}!**")
    @ui.button(label="Fechar", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, it, button):
        await it.response.send_message("🔒 **Fechando...**")
        log_ch, file = bot.get_channel(int(self.log_id)), await generate_transcript(it.channel)
        if log_ch:
            log_emb = discord.Embed(title="Ticket Encerrado", color=0x2F3136, timestamp=datetime.datetime.now())
            log_emb.add_field(name="👤 Dono", value=f"<@{self.owner_id}>", inline=True)
            await log_ch.send(embed=log_emb, file=discord.File(file, filename=f"log-{it.channel.name}.txt"))
        try:
            owner = it.guild.get_member(self.owner_id)
            if owner: await owner.send(content="Como foi seu atendimento?", view=EvalView(self.log_id, self.owner_id))
        except: pass
        await asyncio.sleep(5); await it.channel.delete()

class TicketView(ui.View):
    def __init__(self, config):
        super().__init__(timeout=None)
        self.config = config
        opts = [discord.SelectOption(label=c['nome'], description=c['desc'], value=f"cat_{i}") for i, c in enumerate(config['categorias'])]
        select = ui.Select(placeholder="Escolha uma categoria...", options=opts)
        async def cb(it: discord.Interaction):
            idx = int(it.data['values'][0].split('_')[1])
            cat_nome = self.config['categorias'][idx]['nome']
            ch = await it.guild.create_text_channel(name=f"🎫-{cat_nome}-{it.user.name}", overwrites={it.guild.default_role: discord.PermissionOverwrite(read_messages=False), it.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)})
            emb = discord.Embed(title=f"Atendimento: {cat_nome}", description=self.config['info_pos'], color=0x5865F2)
            await ch.send(content=f"{it.user.mention}", embed=emb, view=TicketActions(self.config['log_id'], it.user.id))
            await it.response.send_message(f"✅ Criado em {ch.mention}", ephemeral=True)
        select.callback = cb; self.add_item(select)

# --- COMANDOS ---
@bot.command()
@commands.has_permissions(administrator=True)
async def rr(ctx):
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        await ctx.send("⚙️ 1- Descrição:")
        desc = (await bot.wait_for('message', check=check)).content
        await ctx.send("⚙️ 2- Banner (Link ou skip):")
        banner = (await bot.wait_for('message', check=check)).content
        await ctx.send("⚙️ 3- Thumbnail (Link ou skip):")
        thumb = (await bot.wait_for('message', check=check)).content
        await ctx.send("⚙️ 4- Footer:")
        foot = (await bot.wait_for('message', check=check)).content
        await ctx.send("⚙️ 5- Categorias (Nome#Desc | Nome#Desc):")
        raw = (await bot.wait_for('message', check=check)).content
        cats = [{'nome': x.split('#')[0].strip(), 'desc': x.split('#')[1].strip()} for x in raw.split('|') if '#' in x]
        await ctx.send("⚙️ 6- Info Pós-Abertura:")
        info = (await bot.wait_for('message', check=check)).content
        await ctx.send("⚙️ 7- ID Log:")
        log_id = (await bot.wait_for('message', check=check)).content
        await collection.update_one({"_id": ctx.guild.id}, {"$set": {"desc": desc, "banner": banner, "thumb": thumb, "footer": foot, "categorias": cats, "info_pos": info, "log_id": log_id}}, upsert=True)
        await ctx.send("✅ Configurado!")
    except Exception as e: await ctx.send(f"❌ Erro: {e}")

@bot.tree.command(name="setup_painel")
async def setup_painel(it: discord.Interaction):
    await it.response.defer(ephemeral=True)
    dados = await collection.find_one({"_id": it.guild_id})
    if not dados: return await it.followup.send("Rode `!rr` primeiro.")
    emb = discord.Embed(title="Suporte", description=dados['desc'], color=0x5865F2)
    if dados['banner'].lower() != 'skip': emb.set_image(url=dados['banner'])
    if dados['thumb'].lower() != 'skip': emb.set_thumbnail(url=dados['thumb'])
    emb.set_footer(text=dados['footer'])
    await it.channel.send(embed=emb, view=TicketView(dados))
    await it.followup.send("Enviado!")

# --- COMANDO: /BOTDIZER (COM REGRAS DE OBRIGATORIEDADE) ---
@bot.tree.command(name="botdizer", description="Cria um menu personalizado com o bot.")
@app_commands.describe(
    titulo="[Obrigatório] Nome em negrito do topo",
    descricao="[Obrigatório] Texto principal do menu",
    banner="[Opcional] Link da imagem de banner",
    thumbnail="[Opcional] Link da imagem lateral",
    cor="[Obrigatório] Cor em Hex (ex: #ffffff)",
    footer="[Opcional] Texto do rodapé"
)
async def botdizer(
    it: discord.Interaction, 
    titulo: str, 
    descricao: str, 
    cor: str, # Removido o valor padrão para tornar obrigatório
    banner: str = None, 
    thumbnail: str = None, 
    footer: str = None
):
    try:
        color_hex = int(cor.replace("#", ""), 16)
        emb = discord.Embed(title=f"**{titulo}**", description=descricao, color=color_hex)
        
        if banner and banner.lower() != "skip": emb.set_image(url=banner)
        if thumbnail and thumbnail.lower() != "skip": emb.set_thumbnail(url=thumbnail)
        if footer and footer.lower() != "skip": emb.set_footer(text=footer)
        
        await it.channel.send(embed=emb)
        await it.response.send_message("✅ Menu enviado!", ephemeral=True)
    except Exception as e:
        await it.response.send_message(f"❌ Erro: Verifique se a cor está correta (ex: #ff0000).\n`{e}`", ephemeral=True)

@app.route('/')
async def home(): return "Online"

async def main():
    await asyncio.gather(bot.start(TOKEN), app.run_task(host="0.0.0.0", port=10000))

if __name__ == "__main__":
    asyncio.run(main())
    
