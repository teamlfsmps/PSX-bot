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

# --- SISTEMA DE AVALIAÇÃO (5 ESTRELAS) ---
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
        nota = int(self.values[0])
        msg = "Obrigado pelo feedback! 🥰" if nota >= 3 else "Sentimos muito. Vamos melhorar! 😔"
        await interaction.response.send_message(msg, ephemeral=True)

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

# --- BOTÃO E INFOS DE FECHAR TICKET ---
class CloseTicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.user
        
        # Embed de encerramento enviado na DM
        embed_dm = discord.Embed(
            title="Ticket Finalizado",
            description=f"Seu atendimento foi encerrado por: {user.mention}\n\nPor favor, deixe sua avaliação abaixo para nos ajudar.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        
        view_eval = ui.View()
        view_eval.add_item(EvalDropdown(user.name))
        
        try: await user.send(embed=embed_dm, view=view_eval)
        except: pass
        
        await interaction.response.send_message("O canal será excluído em segundos...")
        await interaction.channel.delete()

# --- MODAL E INFOS DE ABERTURA ---
class TicketModal(ui.Modal, title='Formulário de Suporte'):
    def __init__(self, categoria):
        super().__init__()
        self.categoria = categoria
    
    motivo = ui.TextInput(label='Descreva o motivo do contato', style=discord.TextStyle.paragraph, placeholder='Escreva aqui...')

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        channel = await guild.create_text_channel(name=f'ticket-{user.name}', overwrites=overwrites)
        
        # Embed informativa dentro do ticket aberto
        embed_info = discord.Embed(
            title="👋 Olá! Bem-vindo ao seu Ticket",
            description=f"Seu atendimento foi iniciado.\n\n**📂 Categoria:** {self.categoria}\n**📝 Motivo:** {self.motivo.value}\n\nUm membro da equipe logo entrará em contato. Para encerrar, clique no botão abaixo.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        embed_info.set_footer(text="Sistema de Suporte PSX")
        
        await channel.send(content=f"{user.mention}", embed=embed_info, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Seu ticket foi criado com sucesso: {channel.mention}", ephemeral=True)

# --- MENU PRINCIPAL (PAINEL ÚNICO COM DESCRIÇÕES) ---
class TicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.select(
        placeholder="Escolha uma categoria para atendimento...",
        options=[
            discord.SelectOption(label='Dúvidas', description='Tire suas dúvidas sobre nossos serviços', emoji='❓'),
            discord.SelectOption(label='Vendas', description='Problemas ou questões sobre compras', emoji='💰'),
            discord.SelectOption(label='Carrinho', description='Dúvidas sobre produtos no carrinho', emoji='🛒'),
            discord.SelectOption(label='Outros', description='Assuntos que não se encaixam acima', emoji='⚠️'),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: ui.Select):
        await interaction.response.send_modal(TicketModal(select.values[0]))

@bot.command()
async def painel(ctx):
    # Unificando tudo em uma única mensagem (Embed + View)
    embed = discord.Embed(
        title="✨ CENTRAL DE ATENDIMENTO - PSX",
        description="Seja bem-vindo ao nosso suporte oficial.\n\nSelecione a categoria desejada no menu abaixo para iniciar um atendimento privado com nossa equipe.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Estamos prontos para te ajudar!")
    
    await ctx.send(embed=embed, view=TicketView())

@bot.event
async def on_ready():
    print(f"Bot {bot.user} online e pronto para agir!")

# --- BOOT ---
if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('DISCORD_TOKEN'))
        
