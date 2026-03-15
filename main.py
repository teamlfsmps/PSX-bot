import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button
from flask import Flask
from threading import Thread
from datetime import datetime
import json
import os

TOKEN = os.getenv("TOKEN")

# =========================
# IDs
# =========================

CANAL_APROVADOS = 1482358707529711626
CANAL_REPROVADOS = 1482358743176974519
CANAL_CONTADOR = 1482372644870422579
CARGO_APROVADO = 1482371950335627304

# =========================
# FLASK (Render)
# =========================

app = Flask("")

@app.route("/")
def home():
    return "Bot online"

def run():
    app.run(host="0.0.0.0", port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# =========================
# BOT
# =========================

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# BANCO DE DADOS
# =========================

ARQUIVO = "registros.json"

if not os.path.exists(ARQUIVO):
    with open(ARQUIVO,"w") as f:
        json.dump({},f)

def carregar():
    with open(ARQUIVO) as f:
        return json.load(f)

def salvar(dados):
    with open(ARQUIVO,"w") as f:
        json.dump(dados,f,indent=4)

# =========================
# CONTADOR
# =========================

async def atualizar_contador():

    dados = carregar()

    aprovados = sum(1 for x in dados.values() if x["status"]=="aprovado")
    rejeitados = sum(1 for x in dados.values() if x["status"]=="rejeitado")

    canal = bot.get_channel(CANAL_CONTADOR)

    embed = discord.Embed(
        title="📊 Sistema de Registros",
        description=f"Aprovado✅: {aprovados}\nRejeitado❌: {rejeitados}",
        color=0xf1c40f
    )

    mensagens = [msg async for msg in canal.history(limit=1)]

    if mensagens:
        await mensagens[0].edit(embed=embed)
    else:
        await canal.send(embed=embed)

# =========================
# FORMULÁRIO RGSET
# =========================

class RegistroModal(Modal, title="Settagem"):

    nome = TextInput(
        label="Qual é o seu nome?",
        required=True
    )

    nick = TextInput(
        label="Qual é o seu Nick no jogo?",
        required=True
    )

    idade = TextInput(
        label="Quantos anos você tem?",
        required=True
    )

    recrutador = TextInput(
        label="Quem te recrutou?",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):

        dados = carregar()

        if str(interaction.user.id) in dados:
            await interaction.response.send_message(
                "Você já enviou um registro.",
                ephemeral=True
            )
            return

        dados[str(interaction.user.id)] = {
            "nome": self.nome.value,
            "nick": self.nick.value,
            "idade": self.idade.value,
            "recrutador": self.recrutador.value,
            "status": "pendente"
        }

        salvar(dados)

        await interaction.response.send_message(
            "Enviando RG, Aguarde.",
            ephemeral=True
        )

        embed = discord.Embed(
            title="📋 **Novo Registro**",
            description=f"Novo set de {interaction.user.mention}",
            color=0xe74c3c
        )

        embed.add_field(
            name="",
            value=f"""
👤 Nome:`{self.nome.value}`
🆔 Idade:`{self.idade.value}`
🎮 Nick:`{self.nick.value}`

📝 Recrutador:`{self.recrutador.value}`
""",
            inline=False
        )

        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        embed.set_footer(
            text="©Flamengo [BOT]™ | Todos os Direitos reservados."
        )

        view = RegistroBotoes(
            interaction.user,
            self.nome.value,
            self.nick.value,
            self.idade.value,
            self.recrutador.value
        )

        await interaction.channel.send(embed=embed, view=view)

# =========================
# BOTÕES
# =========================

class RegistroBotoes(View):

    def __init__(self,user,nome,nick,idade,recrutador):
        super().__init__(timeout=None)
        self.user=user
        self.nome=nome
        self.nick=nick
        self.idade=idade
        self.recrutador=recrutador

    @discord.ui.button(label="Aprovar",style=discord.ButtonStyle.success,emoji="✅")
    async def aprovar(self,interaction:discord.Interaction,button:Button):

        dados=carregar()

        dados[str(self.user.id)]["status"]="aprovado"
        salvar(dados)

        await interaction.response.send_message(
            "```Registro de set aprovado, aguarde a execução...```"
        )

        canal=bot.get_channel(CANAL_APROVADOS)

        data=datetime.now().strftime("%d/%m/%Y %H:%M")

        embed=discord.Embed(
            title="✅ Registro Aprovado",
            description=f"Novo resultado de: {self.user.mention} aprovado",
            color=0x2ecc71
        )

        embed.add_field(
            name="",
            value=f"""
👤 Nome:`{self.nome}`
🆔 Idade:`{self.idade}`
🎮 Nick:`{self.nick}`
📂 ID do Discord:`{self.user.id}`

📝 Responsável:`{interaction.user}`
📅 Data da aprovação: {data}
""",
            inline=False
        )

        embed.set_footer(
            text="©Flamengo [BOT]™ | Todos os Direitos reservados."
        )

        await canal.send(embed=embed)

        membro=interaction.guild.get_member(self.user.id)
        cargo=interaction.guild.get_role(CARGO_APROVADO)

        if membro and cargo:
            await membro.add_roles(cargo)

        await atualizar_contador()

    @discord.ui.button(label="Rejeitar",style=discord.ButtonStyle.danger,emoji="❌")
    async def rejeitar(self,interaction:discord.Interaction,button:Button):

        dados=carregar()

        dados[str(self.user.id)]["status"]="rejeitado"
        salvar(dados)

        await interaction.response.send_message(
            "```registro de set rejeitado, tente novamente mais tarde...```"
        )

        canal=bot.get_channel(CANAL_REPROVADOS)

        data=datetime.now().strftime("%d/%m/%Y %H:%M")

        embed=discord.Embed(
            title="❌ Registro Rejeitado",
            description=f"Novo resultado de: {self.user.mention} rejeitado",
            color=0xe74c3c
        )

        embed.add_field(
            name="",
            value=f"""
👤 Nome:`{self.nome}`
🆔 Idade:`{self.idade}`
🎮 Nick:`{self.nick}`
📂 ID do Discord:`{self.user.id}`

📝 Responsável:`{interaction.user}`
📅 Data: {data}
""",
            inline=False
        )

        embed.set_footer(
            text="©Flamengo [BOT]™ | Todos os Direitos reservados."
        )

        await canal.send(embed=embed)

        await atualizar_contador()

# =========================
# COMANDO RGSET
# =========================

@bot.tree.command(name="rgset",description="Formulário de registro")
async def rgset(interaction:discord.Interaction):

    modal=RegistroModal()
    await interaction.response.send_modal(modal)

# =========================
# HISTÓRICO
# =========================

@bot.tree.command(name="historicorgset",description="Histórico de registros")
async def historicorgset(interaction:discord.Interaction):

    dados=carregar()

    texto=""

    for user,data in dados.items():

        texto+=f"""
Usuário:<@{user}>
Status:`{data['status']}`
Nick:`{data['nick']}`
Idade:`{data['idade']}`
Recrutador:`{data['recrutador']}`

"""

    embed=discord.Embed(
        title="📜 Histórico de Registros",
        description=texto[:4000],
        color=0x3498db
    )

    await interaction.response.send_message(embed=embed)

# =========================
# BOTDIZER
# =========================

@bot.tree.command(name="botdizer",description="Bot envia embed")
@app_commands.describe(
titulo="Título",
descricao="Descrição",
cor="Cor HEX ex: #176387"
)
async def botdizer(interaction:discord.Interaction,titulo:str,descricao:str,cor:str=None):

    if cor:
        cor=int(cor.replace("#",""),16)
    else:
        cor=0x176387

    embed=discord.Embed(
        title=f"**{titulo}**",
        description=descricao,
        color=cor
    )

    await interaction.response.send_message("Mensagem enviada.",ephemeral=True)
    await interaction.channel.send(embed=embed)

# =========================
# BOTDIZER2
# =========================

@bot.tree.command(name="botdizer2",description="Bot envia mensagem simples")
@app_commands.describe(mensagem="Mensagem")
async def botdizer2(interaction:discord.Interaction,mensagem:str):

    await interaction.response.send_message("Mensagem enviada.",ephemeral=True)
    await interaction.channel.send(mensagem)

# =========================

@bot.event
async def on_ready():

    await bot.tree.sync()
    print("Bot online")

keep_alive()
bot.run(TOKEN)
