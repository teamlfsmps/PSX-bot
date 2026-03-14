import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==============================
# SERVIDOR FLASK (ANTI TIMEOUT)
# ==============================

app = Flask(__name__)

@app.route('/')
def home():
    return "PSX Bot Online"

def run():
    app.run(host="0.0.0.0", port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==============================
# EVENTOS
# ==============================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot conectado como {bot.user}")

# ==============================
# /BOTDIZER
# ==============================

@bot.tree.command(name="botdizer", description="Fazer o bot enviar um embed")
@app_commands.describe(
    titulo="Título da embed",
    descricao="Descrição da mensagem",
    cor="Cor da embed (ex: #176387)",
    footer="Texto do footer",
    thumbnail="Link da thumbnail",
    banner="Link da imagem/banner"
)

async def botdizer(
    interaction: discord.Interaction,
    titulo: str,
    descricao: str,
    cor: str = None,
    footer: str = None,
    thumbnail: str = None,
    banner: str = None
):

    if cor:
        cor = int(cor.replace("#",""),16)
    else:
        cor = 0x176387

    embed = discord.Embed(
        title=f"**{titulo}**",
        description=descricao,
        color=cor
    )

    if footer:
        embed.set_footer(text=footer)

    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    if banner:
        embed.set_image(url=banner)

    await interaction.response.send_message("Mensagem enviada!", ephemeral=True)
    await interaction.channel.send(embed=embed)

# ==============================
# /BOTDIZER2
# ==============================

@bot.tree.command(name="botdizer2", description="Bot envia mensagem simples")
@app_commands.describe(
    mensagem="Mensagem que o bot vai enviar"
)

async def botdizer2(interaction: discord.Interaction, mensagem: str):
    await interaction.response.send_message("Mensagem enviada!", ephemeral=True)
    await interaction.channel.send(mensagem)

# ==============================
# INICIAR BOT
# ==============================

keep_alive()
bot.run(TOKEN)
