import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread
import os
import json

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==============================
# FLASK (ANTI TIMEOUT RENDER)
# ==============================

app = Flask(__name__)

@app.route("/")
def home():
    return "PSX Bot Online"

def run():
    app.run(host="0.0.0.0", port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==============================
# BANCO DE REGISTROS
# ==============================

ARQUIVO = "registros.json"

if not os.path.exists(ARQUIVO):
    with open(ARQUIVO, "w") as f:
        json.dump({}, f)

def carregar():
    with open(ARQUIVO) as f:
        return json.load(f)

def salvar(data):
    with open(ARQUIVO, "w") as f:
        json.dump(data, f, indent=4)

# ==============================
# EVENTO
# ==============================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot conectado como {bot.user}")

# ==============================
# /REGISTRO
# ==============================

@bot.tree.command(name="registro", description="Registrar usuário")
@app_commands.describe(
    nome="Seu nome",
    idade="Sua idade"
)
async def registro(interaction: discord.Interaction, nome: str, idade: int):

    registros = carregar()
    user_id = str(interaction.user.id)

    # ANTI MULTI REGISTRO
    if user_id in registros:
        await interaction.response.send_message(
            "❌ Você já está registrado!",
            ephemeral=True
        )
        return

    registros[user_id] = {
        "nome": nome,
        "idade": idade
    }

    salvar(registros)

    await interaction.response.send_message(
        "✅ Registro realizado com sucesso!",
        ephemeral=True
    )

# ==============================
# /BOTDIZER
# ==============================

@bot.tree.command(name="botdizer", description="Enviar embed")
@app_commands.describe(
    titulo="Título",
    descricao="Descrição",
    cor="Cor HEX (#176387)",
    footer="Texto do footer",
    thumbnail="Link da thumbnail",
    banner="Link do banner"
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
        cor = int(cor.replace("#", ""), 16)
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

    await interaction.response.send_message("✅ Mensagem enviada!", ephemeral=True)
    await interaction.channel.send(embed=embed)

# ==============================
# /BOTDIZER2
# ==============================

@bot.tree.command(name="botdizer2", description="Bot envia mensagem simples")
@app_commands.describe(
    mensagem="Mensagem"
)

async def botdizer2(interaction: discord.Interaction, mensagem: str):

    await interaction.response.send_message("✅ Mensagem enviada!", ephemeral=True)
    await interaction.channel.send(mensagem)

# ==============================
# INICIAR
# ==============================

keep_alive()
bot.run(TOKEN)
