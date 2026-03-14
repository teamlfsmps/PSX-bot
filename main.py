import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
import asyncio
import json

TOKEN = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.all()

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("BOT ONLINE")

bot = Bot()

# ================= IDS =================

CANAL_LOGS_APROVADOS = 1482358707529711626
CANAL_LOGS_REJEITADOS = 1482358743176974519
CANAL_CONTADOR = 1482372644870422579
CARGO_APROVADO = 1482371950335627304

ARQUIVO_DB = "registros.json"

contador_aprovados = 0
contador_rejeitados = 0
mensagem_contador = None

# ================= BANCO JSON =================

def carregar_db():

    global contador_aprovados, contador_rejeitados

    if not os.path.exists(ARQUIVO_DB):

        data = {
            "aprovados":0,
            "rejeitados":0,
            "historico":[]
        }

        with open(ARQUIVO_DB,"w") as f:
            json.dump(data,f)

    with open(ARQUIVO_DB,"r") as f:
        data = json.load(f)

    contador_aprovados = data["aprovados"]
    contador_rejeitados = data["rejeitados"]

    return data

def salvar_db(data):

    with open(ARQUIVO_DB,"w") as f:
        json.dump(data,f,indent=4)

db = carregar_db()

# ================= DATA PT =================

def data_pt():

    meses = [
        "janeiro","fevereiro","março","abril","maio","junho",
        "julho","agosto","setembro","outubro","novembro","dezembro"
    ]

    dias = [
        "Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira",
        "Sexta-feira","Sábado","Domingo"
    ]

    agora = datetime.datetime.now()

    return f"{dias[agora.weekday()]}, {agora.day} de {meses[agora.month-1]} de {agora.year} às {agora.strftime('%H:%M')}"

# ================= CONTADOR =================

async def atualizar_contador():

    global mensagem_contador

    canal = bot.get_channel(CANAL_CONTADOR)

    embed = discord.Embed(
        title="📊 Sistema de Registros",
        description=f"""
**Aprovado✅:** `{contador_aprovados}`
**Rejeitado❌:** `{contador_rejeitados}`
""",
        color=0xf1c40f
    )

    if mensagem_contador is None:

        mensagem_contador = await canal.send(embed=embed)

    else:

        await mensagem_contador.edit(embed=embed)

# ================= BOTÕES =================

class RegistroBotoes(discord.ui.View):

    def __init__(self, nome, idade, nick, recrutador, autor):
        super().__init__(timeout=None)

        self.nome = nome
        self.idade = idade
        self.nick = nick
        self.recrutador = recrutador
        self.autor = autor

    async def interaction_check(self, interaction: discord.Interaction):

        if not interaction.user.guild_permissions.manage_roles:

            await interaction.response.send_message(
                "❌ Apenas STAFF pode usar este botão.",
                ephemeral=True
            )

            return False

        return True

# ================= APROVAR =================

    @discord.ui.button(label="Aprovar", style=discord.ButtonStyle.green, emoji="✅")
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):

        global contador_aprovados

        membro = interaction.guild.get_member(self.autor)
        cargo = interaction.guild.get_role(CARGO_APROVADO)

        if membro and cargo:
            await membro.add_roles(cargo)

        contador_aprovados += 1
        db["aprovados"] = contador_aprovados

        registro = {
            "usuario": self.autor,
            "nome": self.nome,
            "idade": self.idade,
            "nick": self.nick,
            "recrutador": self.recrutador,
            "staff": interaction.user.id,
            "resultado":"aprovado",
            "data": data_pt()
        }

        db["historico"].append(registro)
        salvar_db(db)

        await atualizar_contador()

        canal_logs = bot.get_channel(CANAL_LOGS_APROVADOS)

        embed = discord.Embed(
            description=f"""
**Aprovado✅**

**Novo resultado de:** <@{self.autor}> aprovado

👤 **Nome:** `{self.nome}`
🆔 **Idade:** `{self.idade}`
🎮 **Nick:** `{self.nick}`
📂 **ID do Discord:** `{self.autor}`

📝 **Responsável:** {interaction.user.mention}
📅 **Data da aprovação:** {data_pt()}
""",
            color=0x2ecc71
        )

        embed.set_footer(text="©Flamengo [BOT]™ | Todos os Direitos reservados.")

        await canal_logs.send(embed=embed)

        await interaction.response.edit_message(
            content="✅ Settagem aprovada, aguarde a execução.",
            view=None
        )

# ================= REJEITAR =================

    @discord.ui.button(label="Rejeitar", style=discord.ButtonStyle.red, emoji="❌")
    async def rejeitar(self, interaction: discord.Interaction, button: discord.ui.Button):

        global contador_rejeitados

        contador_rejeitados += 1
        db["rejeitados"] = contador_rejeitados

        registro = {
            "usuario": self.autor,
            "nome": self.nome,
            "idade": self.idade,
            "nick": self.nick,
            "recrutador": self.recrutador,
            "staff": interaction.user.id,
            "resultado":"rejeitado",
            "data": data_pt()
        }

        db["historico"].append(registro)
        salvar_db(db)

        await atualizar_contador()

        canal_logs = bot.get_channel(CANAL_LOGS_REJEITADOS)

        embed = discord.Embed(
            description=f"""
**Rejeitado❌**

**Novo resultado de:** <@{self.autor}> rejeitado

👤 **Nome:** `{self.nome}`
🆔 **Idade:** `{self.idade}`
🎮 **Nick:** `{self.nick}`
📂 **ID do Discord:** `{self.autor}`

📝 **Responsável:** {interaction.user.mention}
📅 **Data:** {data_pt()}
""",
            color=0xe74c3c
        )

        embed.set_footer(text="©Flamengo [BOT]™ | Todos os Direitos reservados.")

        await canal_logs.send(embed=embed)

        await interaction.response.edit_message(
            content="❌ Registro rejeitado.",
            view=None
        )

# ================= MODAL =================

class RegistroModal(discord.ui.Modal, title="Registro / Settagem"):

    nome = discord.ui.TextInput(label="Nome")
    idade = discord.ui.TextInput(label="Idade")
    nick = discord.ui.TextInput(label="Nick")
    recrutador = discord.ui.TextInput(label="Recrutador")

    async def on_submit(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="📋 Novo Registro",
            description=f"Novo set de {interaction.user.mention}",
            color=discord.Color.red()
        )

        embed.add_field(name="👤 Nome", value=self.nome.value, inline=False)
        embed.add_field(name="🆔 Idade", value=self.idade.value, inline=True)
        embed.add_field(name="🎮 Nick", value=self.nick.value, inline=True)
        embed.add_field(name="📝 Recrutador", value=self.recrutador.value, inline=False)

        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        embed.set_footer(text="©Flamengo [BOT]™ | Todos os Direitos reservados.")

        await interaction.response.send_message("Registro enviado.", ephemeral=True)

        await interaction.channel.send(
            embed=embed,
            view=RegistroBotoes(
                self.nome.value,
                self.idade.value,
                self.nick.value,
                self.recrutador.value,
                interaction.user.id
            )
        )

# ================= COMANDO RGSET =================

@bot.tree.command(name="rgset")
async def rgset(interaction: discord.Interaction):

    await interaction.response.send_modal(RegistroModal())

# ================= HISTÓRICO =================

@bot.tree.command(name="historicorgset")
async def historicorgset(interaction: discord.Interaction, usuario: discord.Member):

    registros_usuario = [
        r for r in db["historico"] if r["usuario"] == usuario.id
    ]

    if not registros_usuario:

        await interaction.response.send_message(
            "❌ Nenhum registro encontrado para este usuário.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="📂 Histórico de Registro",
        description=f"Histórico de {usuario.mention}",
        color=0xf1c40f
    )

    for registro in registros_usuario[-10:]:

        resultado = "Aprovado✅" if registro["resultado"] == "aprovado" else "Rejeitado❌"

        embed.add_field(
            name=resultado,
            value=f"""
👤 Nome: `{registro['nome']}`
🆔 Idade: `{registro['idade']}`
🎮 Nick: `{registro['nick']}`
📝 Recrutador: `{registro['recrutador']}`
📅 Data: `{registro['data']}`
""",
            inline=False
        )

    embed.set_thumbnail(url=usuario.display_avatar.url)

    embed.set_footer(text="©Flamengo [BOT]™ | Sistema de Histórico")

    await interaction.response.send_message(embed=embed)

# ================= KEEP ALIVE =================

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
