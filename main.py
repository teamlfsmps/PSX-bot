import discord
from discord.ext import commands
from discord import ui
import datetime
import os
from flask import Flask
from threading import Thread

# --- SERVIDOR WEB (KEEP ALIVE) ---
app = Flask('')
@app.route('/')
def home(): return "Bot Vivo!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURAÇÃO DO BOT ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# --- SISTEMA DE AVALIAÇÃO ---
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
        super().__init__(placeholder="Avalie nosso atendimento aqui", options=options)

    async def callback(self, interaction: discord.Interaction):
        nota = self.values[0]
        await interaction.response.send_message(f"Obrigado pelo feedback de {nota} estrelas! 🥰", ephemeral=True)

        ID_CANAL_LOG = 1471325652991869038
        canal = bot.get_channel(ID_CANAL_LOG)
        if canal:
            embed = discord.Embed(
                title="📥 Nova Avaliação",
                description=f"**Usuário:** {self.user_name}\n**Nota:** {nota} estrelas",
                color=discord.Color.green() if int(nota) >= 3 else discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            await canal.send(embed=embed)

# --- TICKET E ENCERRAMENTO ---
class CloseTicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.user
        embed_dm = discord.Embed(
            title="Ticket Finalizado",
            description=f"Seu atendimento foi encerrado.\nPor favor, deixe sua avaliação abaixo.",
            color=discord.Color.red()
        )
        view_eval = ui.View()
        view_eval.add_item(EvalDropdown(user.name))
        
        try: await user.send(embed=embed_dm, view=view_eval)
        except: pass
        
        await interaction.response.send_message("O canal será excluído...")
        await interaction.channel.delete()

# --- MODAL DE ABERTURA ---
class TicketModal(ui.Modal, title='Formulário de Suporte'):
    def __init__(self, categoria):
        super().__init__()
        self.categoria = categoria
    
    motivo = ui.TextInput(label='Motivo do contato', style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(name=f'ticket-{interaction.user.name}', overwrites=overwrites)
        
        embed_info = discord.Embed(
            title="👋 Suporte Iniciado",
            description=f"**Categoria:** {self.categoria}\n**Motivo:** {self.motivo.value}\n\nAguarde um instante.",
            color=discord.Color.blue()
        )
        await channel.send(content=f"{interaction.user.mention}", embed=embed_info, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Ticket criado: {channel.mention}", ephemeral=True)

# --- MENU PRINCIPAL (COM BANNER) ---
class TicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.select(
        placeholder="Escolha uma categoria...",
        options=[
            discord.SelectOption(label='Dúvidas', description='Tire suas dúvidas gerais', emoji='❓'),
            discord.SelectOption(label='Vendas', description='Questões sobre compras', emoji='💰'),
            discord.SelectOption(label='Carrinho', description='Produtos no carrinho', emoji='🛒'),
            discord.SelectOption(label='Outros', description='Outros assuntos', emoji='⚠️'),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: ui.Select):
        await interaction.response.send_modal(TicketModal(select.values[0]))

@bot.command()
async def painel(ctx):
    embed = discord.Embed(
        title="CENTRAL DE ATENDIMENTO - PSX",
        description="Selecione a categoria abaixo para iniciar o suporte.",
        color=discord.Color.blue()
    )
    # LINHA DO BANNER ADICIONADA NOVAMENTE:
    embed.set_image(url="https://cdn.discordapp.com/attachments/1470856469179269338/1471317877125808410/1770749281157.png")
    
    await ctx.send(embed=embed, view=TicketView())

@bot.event
async def on_ready():
    print(f"Bot {bot.user} pronto!")

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('DISCORD_TOKEN'))
        
