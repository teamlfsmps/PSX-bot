import discord
from discord.ext import commands
from discord import ui
import datetime
import os
from flask import Flask
from threading import Thread

# --- SERVIDOR WEB ---
app = Flask('')
@app.route('/')
def home(): return "Bot Vivo!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- BOT CONFIG ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# --- SISTEMA DE AVALIAÇÃO (TODAS AS 5 ESTRELAS) ---
class EvalDropdown(ui.Select):
    def __init__(self, user_name):
        self.user_name = user_name
        # Lista explícita com as 5 opções
        options = [
            discord.SelectOption(label="⭐⭐⭐⭐⭐ Excelente", value="5"),
            discord.SelectOption(label="⭐⭐⭐⭐ Bom", value="4"),
            discord.SelectOption(label="⭐⭐⭐ Regular", value="3"),
            discord.SelectOption(label="⭐⭐ Ruim", value="2"),
            discord.SelectOption(label="⭐ Péssimo", value="1")
        ]
        super().__init__(placeholder="Selecione sua nota aqui", options=options)

    async def callback(self, interaction: discord.Interaction):
        nota = int(self.values[0])
        msg = "Obrigado pela sua avaliação! 🥰" if nota >= 3 else "Sentimos muito. Vamos melhorar! 😔"
        await interaction.response.send_message(msg, ephemeral=True)

        # LOG DE AVALIAÇÃO
        ID_CANAL_LOG = 1471325652991869038
        canal = bot.get_channel(ID_CANAL_LOG)
        if canal:
            embed = discord.Embed(
                title="📥 Nova Avaliação",
                description=f"**Usuário:** {self.user_name}\n**Nota:** {self.values[0]} estrelas",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            await canal.send(embed=embed)

# --- TICKET E PAINEL ---
class CloseTicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.user
        view = ui.View(); view.add_item(EvalDropdown(user.name))
        try: await user.send(content="Avalie nosso atendimento:", view=view)
        except: pass
        await interaction.response.send_message("Limpando canal...")
        await interaction.channel.delete()

class TicketModal(ui.Modal, title='Abrir Ticket'):
    def __init__(self, categoria):
        super().__init__()
        self.categoria = categoria
    motivo = ui.TextInput(label='Motivo', style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await interaction.guild.create_text_channel(name=f'ticket-{interaction.user.name}', overwrites=overwrites)
        emb = discord.Embed(title="Suporte solicitado", description=f"Categoria: {self.categoria}\nAguarde o retorno.", color=discord.Color.green())
        await channel.send(embed=emb, view=CloseTicketView())
        await interaction.response.send_message(f"Canal criado: {channel.mention}", ephemeral=True)

class TicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        options = [
            discord.SelectOption(label='Dúvidas', emoji='❓'),
            discord.SelectOption(label='Vendas', emoji='💰'),
            discord.SelectOption(label='Outros', emoji='⚠️')
        ]
        select = ui.Select(placeholder="Escolha uma categoria...", options=options)
        async def select_callback(interaction):
            await interaction.response.send_modal(TicketModal(select.values[0]))
        select.callback = select_callback
        self.add_item(select)

@bot.command()
async def painel(ctx):
    # AQUI ESTÁ O PAINEL ÚNICO (SEM TEXTO FORA E SEM BANNER)
    embed = discord.Embed(
        title="CENTRAL DE SUPORTE",
        description="Clique no menu abaixo para abrir um atendimento exclusivo.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=TicketView())

@bot.event
async def on_ready():
    print("Bot rodando!")

# --- BOOT ---
if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('DISCORD_TOKEN'))
