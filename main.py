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
        print(f"✅ Sistema PSX v12.0 Online")

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

    @ui.select(
        placeholder="Nota de 1 a 5 estrelas",
        options=[discord.SelectOption(label=f"{i} Estrelas", value=str(i)) for i in range(5, 0, -1)]
    )
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

            await log_ch.send(
                embed=log_emb,
                file=discord.File(file_data, filename="log.txt")
            )

        try:
            owner = it.guild.get_member(self.owner_id)

            if owner:
                pv_emb = discord.Embed(title="Ticket Finalizado", color=0xFF0000)
                pv_emb.add_field(name="Motivo:", value=self.motivo.value)

                await owner.send(
                    embed=pv_emb,
                    view=EvalView(self.log_id, self.owner_id)
                )

        except:
            pass

        await asyncio.sleep(3)
        await it.channel.delete()

class TicketActions(ui.View):
    def __init__(self, log_id, owner_id):
        super().__init__(timeout=None)
        self.log_id, self.owner_id = log_id, owner_id

    @ui.button(label="Reivindicar", style=discord.ButtonStyle.success, emoji="🙋‍♂️")
    async def claim(self, it, button):

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
        await it.channel.send(f"✅ **Reivindicado por {it.user.mention}!**")

    @ui.button(label="Fechar", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, it, button):
        await it.response.send_modal(CloseTicketModal(self.log_id, self.owner_id))

# --- SISTEMA DE REGISTRO ---
class BotoesRegistro(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Aprovar", emoji="✅", style=discord.ButtonStyle.green)
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=f"```✅ Settagem aprovada, aguarde a execução.```", view=None)

    @discord.ui.button(label="Rejeitar", emoji="❌", style=discord.ButtonStyle.red)
    async def rejeitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=f"```❌ Pedido de Settagem rejeitada, tente novamente mais tarde.```", view=None)

class RegistroModal(discord.ui.Modal, title="Settagem"):

    nome = discord.ui.TextInput(label="Qual é o seu Nick no jogo?")
    idade = discord.ui.TextInput(label="Quantos anos você tem?")
    nick_serv = discord.ui.TextInput(label="Qual é seu Nick no servidor?")
    recrutador = discord.ui.TextInput(label="Quem te recrutou?")

    async def on_submit(self, interaction: discord.Interaction):

        await interaction.response.send_message("📨 Enviando RG, aguarde.", ephemeral=True)

        embed = discord.Embed(title="📋 **Novo Registro**", color=discord.Color.red())

        embed.set_author(
            name=interaction.guild.name,
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )

        embed.description = (
            f"**Novo set de** {interaction.user.mention}\n\n"
            f"**👤 Nome:** `{self.nome.value}`\n"
            f"**🆔 Idade:** `{self.idade.value}`\n"
            f"**🎮 Nick:** `{self.nick_serv.value}`\n\n"
            f"**📝 Recrutador:** `{self.recrutador.value}`\n\n"
            f"©Flamengo [BOT]™ | Todos os Direitos reservados."
        )

        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        await interaction.channel.send(
            content="@everyone",
            embed=embed,
            view=BotoesRegistro()
        )

# --- COMANDOS ---

@bot.tree.command(name="rgset", description="Abrir formulário de registro")
async def rgset(interaction: discord.Interaction):
    await interaction.response.send_modal(RegistroModal())

# -------- NOVO BOTDIZER --------
@bot.tree.command(name="botdizer", description="Criar um painel personalizado")
@app_commands.describe(
    titulo="Título do painel",
    descricao="Descrição do painel",
    cor="Cor em HEX (#ffffff)",
    banner="Link da imagem (opcional)",
    thumbnail="Link da thumbnail (opcional)",
    rooter="Texto do rodapé (opcional)"
)

async def botdizer(
    interaction: discord.Interaction,
    titulo: str,
    descricao: str,
    cor: str,
    banner: str = None,
    thumbnail: str = None,
    rooter: str = None
):

    try:
        cor_embed = int(cor.replace("#", ""), 16)
    except:
        await interaction.response.send_message("❌ Cor HEX inválida.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"**{titulo}**",
        description=descricao,
        color=cor_embed
    )

    if banner:
        embed.set_image(url=banner)

    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    if rooter:
        embed.set_footer(text=rooter)

    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Painel enviado!", ephemeral=True)

# --- WEB SERVER ---

@app.route('/')
async def home():
    return "Online"

async def main():
    await asyncio.gather(
        bot.start(TOKEN),
        app.run_task(host="0.0.0.0", port=10000)
    )

if __name__ == "__main__":
    asyncio.run(main())
