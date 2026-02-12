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
    return "PSX Bot está Vivo!"

def run():
    # O Render exige a porta 10000 ou usar a variável de ambiente PORT
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

# --- 3. SISTEMA DE AVALIAÇÃO ---
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
        msg = f"Feedback recebido, **{self.user_name}**! 🥰" if nota >= 3 else f"Sentimos muito, **{self.user_name}**. 😔"
        await interaction.response.send_message(msg, ephemeral=True)

        ID_CANAL_LOG = 1471325652991869038  
        canal_logs = bot.get_channel(ID_CANAL_LOG)
        if canal_logs:
            embed = discord.Embed(title="⭐ Nova Avaliação", description=f"**Usuário:** {self.user_name}\n**Nota:** {self.values[0]}", color=discord.Color.green())
            await canal_logs.send(embed=embed)

# --- 4. COMANDOS ---
@bot.event
async def on_ready():
    print(f'Bot {bot.user} está online!')

@bot.command()
async def painel(ctx):
    embed = discord.Embed(title="Central de Atendimento", description="Selecione uma opção.", color=discord.Color.blue())
    # Link do seu banner abaixo
    embed.set_image(url="https://cdn.discordapp.com/attachments/1470856469179269338/1471317877125808410/1770749281157.png")
    await ctx.send(embed=embed)

# --- 5. INICIALIZAÇÃO (ORDEM CRITÍCA) ---
if __name__ == "__main__":
    keep_alive() # Liga o servidor primeiro
    token = os.environ.get('DISCORD_TOKEN')
    if token:
        bot.run(token) # Liga o bot por último
    else:
        print("ERRO: Token não encontrado nas variáveis do Render!")
        
