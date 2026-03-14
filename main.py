import discord
from discord.ext import commands
from discord import ui, app_commands
import os, asyncio, datetime

TOKEN = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.all()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ PSX BOT ONLINE")

bot = MyBot()

# =========================
# IDS CONFIG
# =========================

CANAL_LOGS = 1482358707529711626
CANAL_CONTADOR = 1482372644870422579
CARGO_APROVADO = 1482371950335627304

registro_contador = 0

# =========================
# BOTÕES DE REGISTRO
# =========================

class BotoesRegistro(discord.ui.View):

    def __init__(self, nome, idade, nick, user_id):
        super().__init__(timeout=None)
        self.nome = nome
        self.idade = idade
        self.nick = nick
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction):

        if not interaction.user.guild_permissions.manage_roles:

            await interaction.response.send_message(
                "❌ Apenas **staff** pode usar estes botões.",
                ephemeral=True
            )
            return False

        return True

# =========================
# BOTÃO APROVAR
# =========================

    @discord.ui.button(label="Aprovar", emoji="✅", style=discord.ButtonStyle.green)
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):

        global registro_contador

        await interaction.response.edit_message(
            content="```✅ Settagem aprovada, aguarde a execução.```",
            view=None
        )

        membro = interaction.guild.get_member(self.user_id)
        cargo = interaction.guild.get_role(CARGO_APROVADO)

        if membro and cargo:
            await membro.add_roles(cargo)

        registro_contador += 1

        contador_canal = bot.get_channel(CANAL_CONTADOR)

        if contador_canal:
            await contador_canal.send(f"📊 **Registros aprovados:** `{registro_contador}`")

        log_channel = bot.get_channel(CANAL_LOGS)

        if log_channel:

            embed = discord.Embed(
                title="✅ Registro Aprovado",
                color=0x2ecc71,
                timestamp=datetime.datetime.now()
            )

            embed.add_field(name="👤 Usuário", value=f"<@{self.user_id}>", inline=True)
            embed.add_field(name="🆔 ID", value=self.user_id, inline=True)

            embed.add_field(name="Nome", value=f"`{self.nome}`", inline=False)
            embed.add_field(name="Idade", value=f"`{self.idade}`", inline=True)
            embed.add_field(name="Nick", value=f"`{self.nick}`", inline=True)

            embed.add_field(
                name="👮 Staff Responsável",
                value=interaction.user.mention,
                inline=False
            )

            embed.set_footer(text="©Flamengo [BOT]™ | Sistema de Registros")

            await log_channel.send(embed=embed)

# =========================
# BOTÃO REJEITAR
# =========================

    @discord.ui.button(label="Rejeitar", emoji="❌", style=discord.ButtonStyle.red)
    async def rejeitar(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.edit_message(
            content="```❌ Registro rejeitado.```",
            view=None
        )

        log_channel = bot.get_channel(CANAL_LOGS)

        if log_channel:

            embed = discord.Embed(
                title="❌ Registro Rejeitado",
                color=0xe74c3c,
                timestamp=datetime.datetime.now()
            )

            embed.add_field(name="👤 Usuário", value=f"<@{self.user_id}>", inline=True)
            embed.add_field(name="🆔 ID", value=self.user_id, inline=True)

            embed.add_field(name="Nome", value=f"`{self.nome}`", inline=False)
            embed.add_field(name="Idade", value=f"`{self.idade}`", inline=True)
            embed.add_field(name="Nick", value=f"`{self.nick}`", inline=True)

            embed.add_field(
                name="👮 Staff Responsável",
                value=interaction.user.mention,
                inline=False
            )

            embed.set_footer(text="©Flamengo [BOT]™ | Sistema de Registros")

            await log_channel.send(embed=embed)

# =========================
# MODAL DE REGISTRO
# =========================

class RegistroModal(discord.ui.Modal, title="Settagem"):

    nome = discord.ui.TextInput(label="Nick no jogo")
    idade = discord.ui.TextInput(label="Idade")
    nick_serv = discord.ui.TextInput(label="Nick no servidor")
    recrutador = discord.ui.TextInput(label="Recrutador")

    async def on_submit(self, interaction: discord.Interaction):

        await interaction.response.send_message(
            "📨 Registro enviado.",
            ephemeral=True
        )

        embed = discord.Embed(
            title="📋 Novo Registro",
            color=discord.Color.red()
        )

        embed.description = (
            f"**Novo set de** {interaction.user.mention}\n\n"
            f"👤 **Nome:** `{self.nome.value}`\n"
            f"🆔 **Idade:** `{self.idade.value}`\n"
            f"🎮 **Nick:** `{self.nick_serv.value}`\n\n"
            f"📝 **Recrutador:** `{self.recrutador.value}`"
        )

        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        embed.set_footer(text="©Flamengo [BOT]™")

        await interaction.channel.send(
            embed=embed,
            view=BotoesRegistro(
                self.nome.value,
                self.idade.value,
                self.nick_serv.value,
                interaction.user.id
            )
        )

# =========================
# COMANDO RGSET
# =========================

@bot.tree.command(name="rgset", description="Abrir formulário de registro")
async def rgset(interaction: discord.Interaction):

    await interaction.response.send_modal(RegistroModal())

# =========================
# COMANDO BOTDIZER
# =========================

@bot.tree.command(name="botdizer", description="Enviar embed personalizado")
async def botdizer(
    interaction: discord.Interaction,
    titulo: str,
    descricao: str,
    cor_hex: str
):

    try:

        cor = int(cor_hex.replace("#", ""), 16)

        embed = discord.Embed(
            title=titulo,
            description=descricao,
            color=cor
        )

        await interaction.channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Embed enviado.",
            ephemeral=True
        )

    except:
        await interaction.response.send_message(
            "❌ Cor HEX inválida.",
            ephemeral=True
        )

# =========================
# WEB KEEP ALIVE
# =========================

from quart import Quart
app = Quart(__name__)

@app.route("/")
async def home():
    return "Bot Online"

async def main():
    await asyncio.gather(
        bot.start(TOKEN),
        app.run_task(host="0.0.0.0", port=10000)
    )

if __name__ == "__main__":
    asyncio.run(main())
