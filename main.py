import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button
from discord import app_commands
from flask import Flask
from threading import Thread
from datetime import datetime
import json
import os

TOKEN = os.getenv("TOKEN")

CANAL_APROVADOS = 1482358707529711626
CANAL_REPROVADOS = 1482358743176974519
CANAL_CONTADOR = 1482372644870422579
CANAL_LOGS = 1482569356176261191
CARGO_APROVADO = 1482371950335627304

app = Flask("")

@app.route("/")
def home():
    return "Bot online"

def run():
    app.run(host="0.0.0.0", port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

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

cooldown = {}

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

    msgs=[msg async for msg in canal.history(limit=1)]

    if msgs:
        await msgs[0].edit(embed=embed)
    else:
        await canal.send(embed=embed)

class RegistroModal(Modal, title="Settagem"):

    nome = TextInput(label="Qual é o seu nome?")
    idade = TextInput(label="Qual é sua idade?")
    nick = TextInput(label="Qual é seu Nick?")
    recrutador = TextInput(label="Quem te recrutou?")

    async def on_submit(self, interaction: discord.Interaction):

        agora = datetime.now().timestamp()

        if interaction.user.id in cooldown:
            if agora - cooldown[interaction.user.id] < 60:
                await interaction.response.send_message(
                    "Espere antes de enviar outro registro.",
                    ephemeral=True
                )
                return

        cooldown[interaction.user.id] = agora

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

        embed.set_author(
            name=interaction.guild.name,
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )

        embed.add_field(
            name="",
            value=f"""
**👤 Nome** `{self.nome.value}`
**🆔 Idade** `{self.idade.value}`
**🎮 Nick** `{self.nick.value}`

**📝 Recrutador** `{self.recrutador.value}`
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

        # LOG
        canal_logs=bot.get_channel(CANAL_LOGS)

        log=discord.Embed(
            title="📝 Novo Registro Enviado",
            color=0x3498db
        )

        log.description=f"""
Usuário: {interaction.user.mention}
ID: {interaction.user.id}

Nome: {self.nome.value}
Nick: {self.nick.value}
Idade: {self.idade.value}
Recrutador: {self.recrutador.value}
"""

        await canal_logs.send(embed=log)

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

        self.clear_items()
        await interaction.message.edit(view=self)

        canal=bot.get_channel(CANAL_APROVADOS)

        data=datetime.now().strftime("%d/%m/%Y %H:%M")

        embed=discord.Embed(
            title="✅ Registro Aprovado",
            description=f"**NOVO RESULTADO DE:**\n{self.user.mention}",
            color=0x2ecc71
        )

        embed.set_author(
            name=interaction.guild.name,
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )

        embed.add_field(
            name="",
            value=f"""
**👤 Nome** `{self.nome}`
**🆔 Idade** `{self.idade}`
**🎮 Nick** `{self.nick}`
📂 ID do Discord:`{self.user.id}`

📝 Responsável: {interaction.user.mention}
📅 Data da aprovação: {data}
🆔 ID do responsável: {interaction.user.id}
""",
            inline=False
        )

        await canal.send(embed=embed)

        # LOG
        canal_logs=bot.get_channel(CANAL_LOGS)

        log=discord.Embed(
            title="✅ Registro Aprovado",
            color=0x2ecc71
        )

        log.description=f"""
Usuário: {self.user.mention}
Responsável: {interaction.user.mention}
ID responsável: {interaction.user.id}
Data: {data}
"""

        await canal_logs.send(embed=log)

        await atualizar_contador()

    @discord.ui.button(label="Rejeitar",style=discord.ButtonStyle.danger,emoji="❌")
    async def rejeitar(self,interaction:discord.Interaction,button:Button):

        dados=carregar()
        dados[str(self.user.id)]["status"]="rejeitado"
        salvar(dados)

        await interaction.response.send_message(
            "```registro de set rejeitado, tente novamente mais tarde...```"
        )

        self.clear_items()
        await interaction.message.edit(view=self)

        canal=bot.get_channel(CANAL_REPROVADOS)

        data=datetime.now().strftime("%d/%m/%Y %H:%M")

        embed=discord.Embed(
            title="❌ Registro Rejeitado",
            description=f"**NOVO RESULTADO DE:**\n{self.user.mention}",
            color=0xe74c3c
        )

        embed.set_author(
            name=interaction.guild.name,
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )

        embed.add_field(
            name="",
            value=f"""
**👤 Nome** `{self.nome}`
**🆔 Idade** `{self.idade}`
**🎮 Nick** `{self.nick}`
📂 ID do Discord:`{self.user.id}`

📝 Responsável: {interaction.user.mention}
📅 Data: {data}
🆔 ID do responsável: {interaction.user.id}
""",
            inline=False
        )

        await canal.send(embed=embed)

        canal_logs=bot.get_channel(CANAL_LOGS)

        log=discord.Embed(
            title="❌ Registro Rejeitado",
            color=0xe74c3c
        )

        log.description=f"""
Usuário: {self.user.mention}
Responsável: {interaction.user.mention}
ID responsável: {interaction.user.id}
Data: {data}
"""

        await canal_logs.send(embed=log)

        await atualizar_contador()

@bot.tree.command(name="rgset")
async def rgset(interaction:discord.Interaction):

    modal=RegistroModal()
    await interaction.response.send_modal(modal)

@bot.tree.command(name="historicorgset")
async def historicorgset(interaction:discord.Interaction):

    dados=carregar()

    texto=""

    for user,data in dados.items():

        texto+=f"""
**Usuário:** `<@{user}>`
**Status:** `{data['status']}`
**Nick:** `{data['nick']}`
**Idade:** `{data['idade']}`
**Recrutador:** `{data['recrutador']}`

"""

    embed=discord.Embed(
        title="📜 **HISTÓRICO DE REGISTROS**",
        description=texto[:4000],
        color=0x3498db
    )

    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():

    await bot.tree.sync()
    print("Bot online")

keep_alive()
bot.run(TOKEN)
