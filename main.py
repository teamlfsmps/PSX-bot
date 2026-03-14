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
        print(f"✅ Sistema PSX v10.0 Online")

bot = MyBot()

# --- UTILITÁRIOS TICKETS ---
async def generate_transcript(channel):
    transcript = f"--- HISTÓRICO DE ATENDIMENTO PSX ---\nCanal: {channel.name}\n\n"
    async for msg in channel.history(limit=None, oldest_first=True):
        time = msg.created_at.strftime('%H:%M')
        transcript += f"[{time}] {msg.author}: {msg.content if msg.content else '[Anexo]'}\n"
    return io.BytesIO(transcript.encode('utf-8'))

# --- FEEDBACK TICKETS ---
class FeedbackModal(ui.Modal):
    def __init__(self, nota, log_id, user_id):
        super().__init__(title="Avalie nosso Atendimento")
        self.nota, self.log_id, self.user_id = int(nota), log_id, user_id
    coment = ui.TextInput(label="Comentário:", style=discord.TextStyle.paragraph, required=False)
    async def on_submit(self, it: discord.Interaction):
        log_ch = bot.get_channel(int(self.log_id))
        msg, color = ("🥰 Obrigado!", 0x00FF00) if self.nota > 2 else ("😔 Vamos melhorar.", 0xFF0000)
        if log_ch:
            emb = discord.Embed(title="⭐ Nova Avaliação", color=color, timestamp=datetime.datetime.now())
            emb.add_field(name="👤 Cliente", value=f"<@{self.user_id}>", inline=True)
            emb.add_field(name="⭐ Nota", value="★" * self.nota, inline=True)
            emb.add_field(name="💬 Feedback", value=self.coment.value or "Nenhum", inline=False)
            await log_ch.send(embed=emb)
        await it.response.send_message(msg, ephemeral=True)

class EvalView(ui.View):
    def __init__(self, log_id, user_id):
        super().__init__(timeout=None)
        self.log_id, self.user_id = log_id, user_id
    @ui.select(placeholder="Nota de 1 a 5 estrelas", options=[discord.SelectOption(label=f"{i} Estrelas", value=str(i)) for i in range(5, 0, -1)])
    async def callback(self, it, select):
        await it.response.send_modal(FeedbackModal(select.values[0], self.log_id, self.user_id))

# --- FECHAMENTO TICKET ---
class CloseTicketModal(ui.Modal):
    def __init__(self, log_id, owner_id):
        super().__init__(title="Encerrar Atendimento")
        self.log_id, self.owner_id = log_id, owner_id
    motivo = ui.TextInput(label="Motivo do Fechamento:", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, it: discord.Interaction):
        await it.response.send_message("🔒 **Gerando logs...**")
        log_ch = bot.get_channel(int(self.log_id))
        file_data = await generate_transcript(it.channel)
        if log_ch:
            log_emb = discord.Embed(title="Ticket Fechado", color=0xFF0000, timestamp=datetime.datetime.now())
            log_emb.add_field(name="👤 Autor", value=f"<@{self.owner_id}>", inline=True)
            log_emb.add_field(name="🔒 Fechador", value=f"{it.user.mention}", inline=True)
            log_emb.add_field(name="📝 Motivo", value=self.motivo.value, inline=False)
            await log_ch.send(embed=log_emb, file=discord.File(file_data, filename="log.txt"))
        try:
            owner = it.guild.get_member(self.owner_id)
            if owner:
                pv_emb = discord.Embed(title="Ticket Finalizado", color=0xFF0000)
                pv_emb.add_field(name="Motivo:", value=self.motivo.value)
                await owner.send(embed=pv_emb, view=EvalView(self.log_id, self.owner_id))
        except: pass
        await asyncio.sleep(3); await it.channel.delete()

class TicketActions(ui.View):
    def __init__(self, log_id, owner_id):
        super().__init__(timeout=None)
        self.log_id, self.owner_id = log_id, owner_id
    @ui.button(label="Reivindicar", style=discord.ButtonStyle.success, emoji="🙋‍♂️")
    async def claim(self, it, button):
        overwrites = {it.guild.default_role: discord.PermissionOverwrite(read_messages=False), it.guild.get_member(self.owner_id): discord.PermissionOverwrite(read_messages=True, send_messages=True), it.user: discord.PermissionOverwrite(read_messages=True, send_messages=True), it.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        await it.channel.edit(overwrites=overwrites)
        button.disabled, button.label = True, f"Staff: {it.user.name}"
        await it.response.edit_message(view=self)
        await it.channel.send(f"✅ **Reivindicado por {it.user.mention}!**")
    @ui.button(label="Fechar", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, it, button):
        await it.response.send_modal(CloseTicketModal(self.log_id, self.owner_id))

class OpenTicketModal(ui.Modal):
    def __init__(self, cat_nome, config):
        super().__init__(title=f"Abertura: {cat_nome}")
        self.cat_nome, self.config = cat_nome, config
    motivo = ui.TextInput(label="Motivo da abertura?", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, it: discord.Interaction):
        ch = await it.guild.create_text_channel(name=f"🎫-{self.cat_nome}-{it.user.name}", overwrites={it.guild.default_role: discord.PermissionOverwrite(read_messages=False), it.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)})
        emb = discord.Embed(title=f"**{self.config.get('titulo_ticket', 'Suporte')}**", description=f"{self.config['info_pos']}\n\n**Motivo:** {self.motivo.value}", color=0x5865F2)
        await ch.send(content=f"{it.user.mention}", embed=emb, view=TicketActions(self.config['log_id'], it.user.id))
        await it.response.send_message(f"✅ Aberto em {ch.mention}", ephemeral=True)

class TicketView(ui.View):
    def __init__(self, config):
        super().__init__(timeout=None)
        self.config = config
        opts = [discord.SelectOption(label=c['nome'], description=c['desc'], value=f"cat_{i}") for i, c in enumerate(config['categorias'])]
        select = ui.Select(placeholder="Escolha uma seção...", options=opts)
        async def cb(it: discord.Interaction):
            idx = int(it.data['values'][0].split('_')[1])
            await it.response.send_modal(OpenTicketModal(self.config['categorias'][idx]['nome'], self.config))
        select.callback = cb; self.add_item(select)

# --- SISTEMA RGSET (VERSÃO FINAL) ---
class RGActionView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @ui.button(label="Aprovar", style=discord.ButtonStyle.success, emoji="✅")
    async def approve(self, it, button):
        await it.response.send_message("✅ Settagem aprovada, aguarde a execução.", ephemeral=False)
        self.stop()
    @ui.button(label="Rejeitar", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject(self, it, button):
        await it.response.send_message("❌ Pedido de Settagem rejeitada, tente novamente mais tarde.", ephemeral=False)
        self.stop()

class RGSetModal(ui.Modal):
    def __init__(self):
        super().__init__(title="Formulário de Setagem")
    nome_serv = ui.TextInput(label="Nome no Servidor:", required=True)
    id_serv = ui.TextInput(label="ID no Servidor:", required=True)
    celular = ui.TextInput(label="Número de Celular:", required=True)
    recrutador = ui.TextInput(label="Quem te recrutou?", required=True)

    async def on_submit(self, it: discord.Interaction):
        await it.response.send_message("⏳ Enviando RG, Aguarde.", ephemeral=True)
        # Alteração: Barra Vermelha
        emb = discord.Embed(title="**📋 Novo Registro**", description=f"Novo set de {it.user.mention}", color=0xFF0000)
        emb.set_author(name=it.guild.name, icon_url=it.guild.icon.url if it.guild.icon else None)
        
        # Alteração: Respostas na frente e com crases (caixa preta)
        emb.add_field(name="👤 Nome:", value=f"`{self.nome_serv.value}`", inline=True)
        emb.add_field(name="
        
