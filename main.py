import discord
from discord.ext import commands
from discord import ui
import datetime
import random
import os
from flask import Flask
from threading import Thread

# --- 1. CONFIGURAÇÃO DO SERVIDOR WEB (KEEP ALIVE) ---
app = Flask('')

@app.route('/')
def home():
    return "PSX Bot está Vivo e Online!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. CONFIGURAÇÃO DO BOT ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# --- 3. SISTEMA DE AVALIAÇÃO (5 ESTRELAS CORRIGIDO) ---
class EvalDropdown(ui.Select):
    def __init__(self, user_name):
        self.user_name = user_name
        options = [
            discord.SelectOption(label="Excelente ⭐⭐⭐⭐⭐", value="5"),
            discord.SelectOption(label="Bom ⭐⭐⭐⭐", value="4"),
            discord.SelectOption(label="Regular ⭐⭐⭐", value="3"),
            discord.SelectOption(label="Ruim ⭐⭐", value="2"),
            discord.SelectOption(label="Péssimo ⭐", value="1")
        ]
        super().__init__(placeholder="Avaliar Atendimento", options=options)

    async def callback(self, interaction: discord.Interaction):
        nota = int(self.values[0])
        
        if nota >= 3:
            msg = f"Muito obrigado pelo feedback positivo, **{self.user_name}**! 🥰"
        else:
            msg = f"Sentimos muito, **{self.user_name}**. 😔 Vamos trabalhar para melhorar!"

        await interaction.response.send_message(msg, ephemeral=True)

        ID_CANAL_LOG = 1471325652991869038  
        canal_logs = bot.get_channel(ID_CANAL_LOG)
        
        if canal_logs:
            cor = discord.Color.green() if nota >= 3 else discord.Color.red()
            embed_log = discord.Embed(
                title="⭐ Nova Avaliação",
                description=f"**Usuário:** {self.user_name}\n**Nota:** {self.values[0]} estrelas",
                color=cor,
                timestamp=datetime.datetime.now()
            )
            await canal_logs.send(embed=embed_log)

# --- 4. BOTÃO DE FECHAR TICKET ---
class CloseTicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_button(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.user
        view_eval = ui.View()
        view_eval.add_item(EvalDropdown(user.name))
        
        try:
            await user.send(content=f"Olá {user.mention}, seu ticket foi encerrado. Poderia nos avaliar?", view=view_eval)
        except:
            pass 
        await interaction.response.send_message("Finalizando ticket...")
        await interaction.channel.delete()

# --- 5. MENU DE TICKETS ---
class TicketModal(ui.Modal, title='Abrir Ticket'):
    def __init__(self, categoria):
        super().__init__()
        self.categoria = categoria
    motivo = ui.TextInput(label='Motivo', style=discord.TextStyle.paragraph, placeholder='Descreva o motivo do ticket...')

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(name=f'ticket-{interaction.user.name}', overwrites=overwrites)
        
        embed = discord.Embed(title="Atendimento PSX", description=f"Olá {interaction.user.mention}, aguarde um suporte.\n**Categoria:** {self.categoria}", color=discord.Color.blue())
        await channel.send(embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"Ticket criado: {channel.mention}", ephemeral=True)

class TicketDropdown(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label='Dúvidas', emoji='❓'),
            discord.SelectOption(label='Vendas', emoji='💰'),
            discord.SelectOption(label='Carrinho', emoji='🛒'),
            discord.SelectOption(label='Outros', emoji='⚠️'),
        ]
        super().__init__(placeholder='Escolha uma categoria...', options=options)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self.values[0]))

# --- 6. COMANDOS ---
@bot.event
async def on_ready():
    print(f'Bot {bot.user} está online e pronto!')

@bot.command()
async def painel(ctx):
    # Banner e Menu em uma única mensagem
    embed = discord.Embed(
        title="CENTRAL DE ATENDIMENTO - PSX",
        description="Clique no menu abaixo para abrir um ticket de suporte.",
        color=discord.Color.blue()
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1470856469179269338/1471317877125808410/1770749281157.png")
    
    view = ui.View(timeout=None)
    view.add_item(TicketDropdown())
    
    await ctx.send(embed=embed, view=view)

# --- FINALIZAÇÃO ---
if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('DISCORD_TOKEN'))
            
