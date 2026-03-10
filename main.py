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
        print(f"✅ Sistema PSX v3.0 Ativo")

bot = MyBot()

# --- UTILITÁRIOS ---
async def generate_transcript(channel):
    transcript = f"--- RELATÓRIO DE ATENDIMENTO PSX ---\nCanal: {channel.name}\nData: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
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
    
    coment = ui.TextInput(label="O que podemos melhorar?", style=discord.TextStyle.paragraph, required=False, placeholder="Opcional...")

    async def on_submit(self, it: discord.Interaction):
        log_ch = bot.get_channel(int(self.log_id))
        
        # Lógica de texto baseada na nota
        if self.nota <= 2:
            msg_cliente = "😔 **Lamentamos que sua experiência não tenha sido das melhores.** Vamos utilizar seu feedback para melhorar nosso atendimento!"
            status_log = "⚠️ Avaliação Negativa"
            color = 0xFF0000
        else:
            msg_cliente = "🥰 **Ficamos muito felizes que você gostou!** Sua satisfação é nossa prioridade."
            status_log = "⭐ Avaliação Positiva"
            color = 0x00FF00

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

    @ui.select(placeholder="Avalie o suporte (1-5 estrelas)", options=[
        discord.SelectOption(label="⭐⭐⭐⭐⭐", value="5"),
        discord.SelectOption(label="⭐⭐⭐⭐", value="4"),
        discord.SelectOption(label="⭐⭐⭐", value="3"),
        discord.SelectOption(label="⭐⭐", value="2"),
        discord.SelectOption(label="⭐", value="1"),
    ])
    async def callback(self, it, select):
        await it.response.send_modal(FeedbackModal(select.values[0], self.log_id, self.user_id))

# --- BOTÕES DO TICKET ---
class TicketActions(ui.View):
    def __init__(self, log_id, owner_id):
        super().__init__(timeout=None)
        self.log_id = log_id
        self.owner_id = owner_id

    @ui.button(label="Reivindicar", style=discord.ButtonStyle.success, emoji="🙋‍♂️", custom_id="claim_btn")
    async def claim(self, it, button):
        # Bloqueia o canal apenas para o dono do ticket e o staff que reivindicou
        overwrites = {
            it.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            it.guild.get_member(self.owner_id): discord.PermissionOverwrite(read_messages=True, send_messages=True),
            it.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            it.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        await it.channel.edit(overwrites=overwrites)
        button.disabled = True
        button.label = f"Staff: {it.user.name}"
        await it.response.edit_message(view=self)
        await it.channel.send(f"✅ **Ticket reivindicado por {it.user.mention}!** Agora apenas você e o cliente podem ler este canal.")

    @ui.button(label="Fechar", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_btn")
    async def close(self, it, button):
        await it.response.send_message("🔒 **Este ticket será fechado em breve. Gerando logs...**")
        
        log_ch = bot.get_channel(int(self.log_id))
        transcript_file = await generate_transcript(it.channel)
        
        if log_ch:
            log_emb = discord.Embed(title="Ticket Encerrado", color=0x2F3136, timestamp=datetime.datetime.now())
            log_emb.add_field(name="🆔 Ticket", value=it.channel.name, inline=True)
            log_emb.add_field(name="👤 Aberto por", value=f"<@{self.owner_id}>", inline=True)
            log_emb.add_field(name="🔒 Fechado por", value=it.user.mention, inline=True)
            await log_ch.send(embed=log_emb, file=discord.File(transcript_file, filename=f"transcript-{it.channel.name}.txt"))

        try:
            owner = it.guild.get_member(self.owner_id)
            if owner: await owner.send(content="**Obrigado pelo contato! Como foi seu atendimento?**", view=EvalView(self.log_id, self.owner_id))
        except: pass

        await asyncio.sleep(5)
        await it.channel.delete()

# --- PAINEL PRINCIPAL ---
class TicketView(ui.View):
    def __init__(self, config):
        super().__init__(timeout=None)
        self.config = config
        opts = [discord.SelectOption(label=c['nome'], description=c['desc'], value=f"cat_{i}") for i, c in enumerate(config['categorias'])]
        select = ui.Select(placeholder="Escolha como podemos ajudar...", options=opts)
        
        async def cb(it: discord.Interaction):
            idx = int(it.data['values'][0].split('_')[1])
            cat_nome = self.config['categorias'][idx]['nome']
            
            ch = await it.guild.create_text_channel(name=f"🎫-{cat_nome}-{it.user.name}", overwrites={
                it.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                it.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                it.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            })
            
            emb = discord.Embed(title=f"Atendimento: {cat_nome}", description=self.config['info_pos'], color=0x5865F2)
            emb.set_footer(text="Aguarde um staff reivindicar seu atendimento.")
            
            await ch.send(content=f"{it.user.mention} | Boas-vindas!", embed=emb, view=TicketActions(self.config['log_id'], it.user.id))
            await it.response.send_message(f"✅ Ticket criado com sucesso em {ch.mention}", ephemeral=True)
        
        select.callback = cb
        self.add_item(select)

# --- COMANDOS ---
@bot.command()
@commands.has_permissions(administrator=True)
async def rr(ctx):
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        await ctx.send("⚙️ **1- Descrição do Painel:**")
        desc = (await bot.wait_for('message', check=check)).content
        await ctx.send("⚙️ **2- Link do Banner (ou skip):**")
        banner = (await bot.wait_for('message', check=check)).content
        if ctx.message.attachments: banner = ctx.message.attachments[0].url
        await ctx.send("⚙️ **3- Thumbnail (ou skip):**")
        thumb = (await bot.wait_for('message', check=check)).content
        await ctx.send("⚙️ **4- Rodapé (Footer):**")
        foot = (await bot.wait_for('message', check=check)).content
        await ctx.send("⚙️ **5- Categorias (Ex: Suporte#Dúvidas | VIP#Comprar):**")
        raw = (await bot.wait_for('message', check=check)).content
        cats = [{'nome': x.split('#')[0].strip(), 'desc': x.split('#')[1].strip()} for x in raw.split('|') if '#' in x]
        await ctx.send("⚙️ **6- Mensagem ao abrir ticket (ex: mencione @suporte):**")
        info = (await bot.wait_for('message', check=check)).content
        await ctx.send("⚙️ **7- ID do Canal de Logs:**")
        log_id = (await bot.wait_for('message', check=check)).content

        await collection.update_one({"_id": ctx.guild.id}, {"$set": {"desc": desc, "banner": banner, "thumb": thumb, "footer": foot, "categorias": cats, "info_pos": info, "log_id": log_id}}, upsert=True)
        await ctx.send("✅ **Configuração salva com sucesso no banco de dados!**")
    except Exception as e: await ctx.send(f"❌ Erro: {e}")

@bot.tree.command(name="setup_painel")
async def setup_painel(it: discord.Interaction):
    await it.response.defer(ephemeral=True)
    dados = await collection.find_one({"_id": it.guild_id})
    if not dados: return await it.followup.send("Rode `!rr` primeiro.")
    
    emb = discord.Embed(title="Central de Suporte PSX", description=dados['desc'], color=0x5865F2)
    if dados['banner'].lower() != 'skip': emb.set_image(url=dados['banner'])
    if dados['thumb'].lower() != 'skip': emb.set_thumbnail(url=dados['thumb'])
    emb.set_footer(text=dados['footer'])
    
    await it.channel.send(embed=emb, view=TicketView(dados))
    await it.followup.send("Painel enviado!")

@app.route('/')
async def home(): return "Online"

async def main():
    await asyncio.gather(bot.start(TOKEN), app.run_task(host="0.0.0.0", port=10000))

if __name__ == "__main__":
    asyncio.run(main())
                             
