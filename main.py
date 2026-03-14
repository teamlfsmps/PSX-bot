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
        print("✅ Sistema PSX v12.0 Online")

bot = MyBot()

# ===============================
# UTILITÁRIO TRANSCRIPT
# ===============================

async def generate_transcript(channel):

    transcript = f"--- HISTÓRICO DE ATENDIMENTO PSX ---\nCanal: {channel.name}\n\n"

    async for msg in channel.history(limit=None, oldest_first=True):

        time = msg.created_at.strftime('%H:%M')

        transcript += f"[{time}] {msg.author}: {msg.content if msg.content else '[Anexo]'}\n"

    return io.BytesIO(transcript.encode('utf-8'))

# ===============================
# SISTEMA DE REGISTRO
# ===============================

class BotoesRegistro(discord.ui.View):

    def __init__(self, nome, idade, nick, user_id):
        super().__init__(timeout=None)
        self.nome = nome
        self.idade = idade
        self.nick = nick
        self.user_id = user_id

    @discord.ui.button(label="Aprovar", emoji="✅", style=discord.ButtonStyle.green)
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.edit_message(
            content="```✅ Settagem aprovada, aguarde a execução.```",
            view=None
        )

        log_channel = interaction.guild.get_channel(1482358707529711626)

        if log_channel:

            embed = discord.Embed(
                description=(
                    f"**Novo resultado de: <@{self.user_id}> aprovado**\n\n"
                    f"**👤 Nome:** `{self.nome}`\n"
                    f"**🆔 Idade:** `{self.idade}`\n"
                    f"**🎮 Nick:** `{self.nick}`\n"
                    f"**📂ID do Discord:** `{self.user_id}`\n\n"
                    f"**📝 Responsável:** {interaction.user.mention}\n"
                    f"**📅 Data da aprovação:** <t:{int(datetime.datetime.now().timestamp())}:F>\n\n"
                    f"©Flamengo [BOT]™ | Todos os Direitos reservados."
                ),
                color=0x2ecc71
            )

            await log_channel.send(embed=embed)

    @discord.ui.button(label="Rejeitar", emoji="❌", style=discord.ButtonStyle.red)
    async def rejeitar(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.edit_message(
            content="```❌ Pedido de Settagem rejeitada, tente novamente mais tarde.```",
            view=None
        )

        log_channel = interaction.guild.get_channel(1482358707529711626)

        if log_channel:

            embed = discord.Embed(
                description=(
                    f"**Novo resultado de: <@{self.user_id}> rejeitado**\n\n"
                    f"**👤 Nome:** `{self.nome}`\n"
                    f"**🆔 Idade:** `{self.idade}`\n"
                    f"**🎮 Nick:** `{self.nick}`\n"
                    f"**📂ID do Discord:** `{self.user_id}`\n\n"
                    f"**📝 Responsável:** {interaction.user.mention}\n"
                    f"**📅 Data da rejeição:** <t:{int(datetime.datetime.now().timestamp())}:F>\n\n"
                    f"©Flamengo [BOT]™ | Todos os Direitos reservados."
                ),
                color=0xe74c3c
            )

            await log_channel.send(embed=embed)

# ===============================
# MODAL REGISTRO
# ===============================

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
            view=BotoesRegistro(
                self.nome.value,
                self.idade.value,
                self.nick_serv.value,
                interaction.user.id
            )
        )

# ===============================
# COMANDOS
# ===============================

@bot.tree.command(name="rgset", description="Abrir formulário de registro")
async def rgset(interaction: discord.Interaction):
    await interaction.response.send_modal(RegistroModal())

# ===============================
# BOTDIZER
# ===============================

@bot.tree.command(name="botdizer")
async def botdizer(it: discord.Interaction, titulo: str, descricao: str, cor_hex: str):

    try:

        color = int(cor_hex.replace("#", ""), 16)

        emb = discord.Embed(
            title=titulo,
            description=descricao,
            color=color
        )

        await it.channel.send(embed=emb)

        await it.response.send_message("✅ Enviado!", ephemeral=True)

    except:

        await it.response.send_message("❌ Erro no Hex.", ephemeral=True)

# ===============================
# WEB SERVER
# ===============================

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
