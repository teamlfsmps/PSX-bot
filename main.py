import discord
from discord.ext import commands
from discord import ui
import datetime
import random
import os

# --- CONFIGURAÇÃO BÁSICA ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
# O prefixo será '!' conforme suas fotos anteriores
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# --- 1. SISTEMA DE AVALIAÇÃO ---
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
            msg = f"Sentimos muito, **{self.user_name}**. 😔 Vamos melhorar!"

        await interaction.response.send_message(msg, ephemeral=True)

        # ID do canal de logs que você configurou
        ID_CANAL_LOG = 1471325652991869038  
        canal_logs = bot.get_channel(1471325652991869038)
        
        if canal_logs:
            cor = discord.Color.green() if nota >= 3 else discord.Color.red()
            embed_log = discord.Embed(
                title="⭐ Nova Avaliação",
                description=f"**Usuário:** {self.user_name}\n**Nota:** {self.values[0]} estrelas",
                color=cor,
                timestamp=datetime.datetime.now()
            )
            await canal_logs.send(embed=embed_log)

# --- 2. BOTÃO DE FECHAR TICKET ---
class CloseTicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_button(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.user
        embed_dm = discord.Embed(
            title="Seu Ticket foi Finalizado!",
            description=f"🔒 **Fechado por:** {user.mention}\n📅 **Data:** {datetime.datetime.now().strftime('%d/%m/%Y')}",
            color=discord.Color.red()
        )
        view_eval = ui.View()
        view_eval.add_item(EvalDropdown(user.name))
        try:
            await user.send(embed=embed_dm, view=view_eval)
        except:
            pass 
        await interaction.response.send_message("Fechando canal...")
        await interaction.channel.delete()

# --- 3. FORMULÁRIO (MODAL) ---
class TicketModal(ui.Modal, title='Abrir Ticket'):
    def __init__(self, categoria):
        super().__init__()
        self.categoria = categoria
    
    motivo = ui.TextInput(label='Motivo do ticket', placeholder='Descreva aqui...', style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(name=f'ticket-{user.name}', overwrites=overwrites)
        embed_welcome = discord.Embed(
            title="👋 Atendimento Iniciado",
            description=f"📂 **Categoria:** {self.categoria}\n📝 **Motivo:** {self.motivo.value}",
            color=discord.Color.blue()
        )
        await channel.send(content=f"{user.mention}", embed=embed_welcome, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Ticket criado: {channel.mention}", ephemeral=True)

# --- 4. MENU DROPDOWN ---
class TicketDropdown(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label='Dúvidas', description='Categoria de dúvida', emoji='❓'),
            discord.SelectOption(label='Vendas', description='Categoria de compras', emoji='💰'),
            discord.SelectOption(label='Carrinho', description='Seu carrinho de compras', emoji='🛒'),
            discord.SelectOption(label='Outros', description='Outros assuntos', emoji='⚠️'),
        ]
        super().__init__(placeholder='Selecione uma categoria...', options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self.values[0]))

class TicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

# --- 5. COMANDOS E EVENTOS ---
@bot.event
async def on_ready():
    print(f'Bot {bot.user} está online no Render!')

@bot.command()
async def painel(ctx):
    embed = discord.Embed(
        title="Central de Atendimento",
        description="Selecione uma opção abaixo para falar com o suporte.",
        color=discord.Color.blue()
    )
    # Substitua pelo seu link de banner real
    embed.set_image(url="https://cdn.discordapp.com/attachments/1470856469179269338/1471317877125808410/1770749281157.png?ex=698e7f0d&is=698d2d8d&hm=4a68d8503bdf9f6bd16068a9d197d75260a1fcf123e1408d297a0c631adb8f34&")
    await ctx.send(content="**Ei, precisa de ajuda?**", embed=embed, view=TicketView())

@bot.command()
async def dado(ctx):
    num = random.randint(1, 6)
    await ctx.send(f'🎲 | **{ctx.author.name}**, caiu: **{num}**!')

@bot.command()
async def ping(ctx):
    await ctx.send(f'🏓 | Pong! **{round(bot.latency * 1000)}ms**')

# --- INICIALIZAÇÃO SEGURA (RENDER) ---
# Aqui ele busca o Token das 'Environment Variables' do Render
bot.run(os.environ.get('DISCORD_TOKEN'))
      
