import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
import asyncio

TOKEN = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.all()

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        await self.tree.sync()
        print("BOT ONLINE")

bot = Bot()

# IDS

CANAL_LOGS = 1482358707529711626
CANAL_CONTADOR = 1482372644870422579
CARGO_APROVADO = 1482371950335627304

contador_registros = 0

# =============================
# BOTÕES
# =============================

class RegistroBotoes(discord.ui.View):

    def __init__(self, nome, idade, nick, autor):
        super().__init__(timeout=None)

        self.nome = nome
        self.idade = idade
        self.nick = nick
        self.autor = autor

    async def interaction_check(self, interaction: discord.Interaction):

        if not interaction.user.guild_permissions.manage_roles:

            await interaction.response.send_message(
                "❌ Apenas **STAFF** pode usar este botão.",
                ephemeral=True
            )

            return False

        return True

# =============================
# BOTÃO APROVAR
# =============================

    @discord.ui.button(label="Aprovar", style=discord.ButtonStyle.green, emoji="✅")
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):

        global contador_registros

        membro = interaction.guild.get_member(self.autor)

        cargo = interaction.guild.get_role(CARGO_APROVADO)

        if membro and cargo:
            await membro.add_roles(cargo)

        contador_registros += 1

        contador_channel = bot.get_channel(CANAL_CONTADOR)

        if contador_channel:
            await contador_channel.send(
                f"📊 **Registros aprovados:** `{contador_registros}`"
            )

        log_channel = bot.get_channel(CANAL_LOGS)

        if log_channel:

            data = datetime.datetime.now().strftime("%A, %d de %B de %Y às %H:%M")

            embed = discord.Embed(
                description=f"""
**✅ Registro Aprovado**

**Novo resultado de:** <@{self.autor}> aprovado

👤 **Nome:** `{self.nome}`
🆔 **Idade:** `{self.idade}`
🎮 **Nick:** `{self.nick}`
📂 **ID do Discord:** `{self.autor}`

📝 **Responsável:** {interaction.user.mention}
📅 **Data da aprovação:** {data}
""",
                color=0x2ecc71
            )

            embed.set_author(
                name=interaction.guild.name,
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )

            embed.set_footer(
                text="©Flamengo [BOT]™ | Todos os Direitos reservados."
            )

            await log_channel.send(embed=embed)

        await interaction.response.edit_message(
            content="✅ Settagem aprovada, aguarde a execução.",
            view=None
        )

# =============================
# BOTÃO REJEITAR
# =============================

    @discord.ui.button(label="Rejeitar", style=discord.ButtonStyle.red, emoji="❌")
    async def rejeitar(self, interaction: discord.Interaction, button: discord.ui.Button):

        log_channel = bot.get_channel(CANAL_LOGS)

        if log_channel:

            data = datetime.datetime.now().strftime("%A, %d de %B de %Y às %H:%M")

            embed = discord.Embed(
                description=f"""
**❌ Registro Rejeitado**

**Resultado de:** <@{self.autor}> rejeitado

👤 **Nome:** `{self.nome}`
🆔 **Idade:** `{self.idade}`
🎮 **Nick:** `{self.nick}`
📂 **ID do Discord:** `{self.autor}`

📝 **Responsável:** {interaction.user.mention}
📅 **Data:** {data}
""",
                color=0xe74c3c
            )

            embed.set_author(
                name=interaction.guild.name,
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )

            embed.set_footer(
                text="©Flamengo [BOT]™ | Todos os Direitos reservados."
            )

            await log_channel.send(embed=embed)

        await interaction.response.edit_message(
            content="❌ Registro rejeitado.",
            view=None
        )

# =============================
# MODAL
# =============================

class RegistroModal(discord.ui.Modal, title="Novo Registro"):

    nome = discord.ui.TextInput(label="Nome")
    idade = discord.ui.TextInput(label="Idade")
    nick = discord.ui.TextInput(label="Nick")

    async def on_submit(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="📋 Novo Registro",
            description=f"Novo set de {interaction.user.mention}",
            color=discord.Color.red()
        )

        embed.add_field(name="Nome", value=self.nome.value, inline=False)
        embed.add_field(name="Idade", value=self.idade.value, inline=True)
        embed.add_field(name="Nick", value=self.nick.value, inline=True)

        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        await interaction.response.send_message(
            "Registro enviado.",
            ephemeral=True
        )

        await interaction.channel.send(
            embed=embed,
            view=RegistroBotoes(
                self.nome.value,
                self.idade.value,
                self.nick.value,
                interaction.user.id
            )
        )

# =============================
# COMANDO RGSET
# =============================

@bot.tree.command(name="rgset")
async def rgset(interaction: discord.Interaction):

    await interaction.response.send_modal(RegistroModal())

# =============================
# COMANDO BOTDIZER
# =============================

@bot.tree.command(name="botdizer")
async def botdizer(
    interaction: discord.Interaction,
    titulo: str,
    descricao: str,
    cor_hex: str
):

    try:

        cor = int(cor_hex.replace("#",""),16)

        embed = discord.Embed(
            title=titulo,
            description=descricao,
            color=cor
        )

        await interaction.channel.send(embed=embed)

        await interaction.response.send_message(
            "Mensagem enviada.",
            ephemeral=True
        )

    except:

        await interaction.response.send_message(
            "Cor inválida.",
            ephemeral=True
        )

# =============================
# KEEP ALIVE (RENDER)
# =============================

from quart import Quart

app = Quart(__name__)

@app.route("/")
async def home():
    return "Bot online"

async def main():
    await asyncio.gather(
        bot.start(TOKEN),
        app.run_task(host="0.0.0.0", port=10000)
    )

asyncio.run(main())
