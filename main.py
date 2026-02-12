import discord
from discord.ext import commands
from discord import ui
import datetime
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# --- 1. SISTEMA DE AVALIAÇÃO (CORRIGIDO) ---
class EvalDropdown(ui.Select):
    def __init__(self, user_name):
        self.user_name = user_name
        # Adicionei todas as 5 opções aqui:
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
            msg = f"Sentimos muito, **{self.user_name}**. 😔 Vamos melhorar nosso atendimento!"

        await interaction.response.send_message(msg, ephemeral=True)

        # SUBSTITUA PELO ID DO SEU CANAL DE AVALIAÇÕES
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

# --- 2. RESTANTE DO CÓDIGO (TICKET E PAINEL) ---
class CloseTicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_button(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.user
        view_eval = ui.View()
        view_eval.add_item(EvalDropdown(user.name))
        
        try:
            await user.send(content="Seu ticket foi fechado. Avalie abaixo:", view=view_eval)
        except:
            pass 
        await interaction.response.send_message("Finalizando...")
        await interaction.channel.delete()

class TicketModal(ui.Modal, title='Abrir Ticket'):
    def __init__(self, categoria):
        super().__init__()
        self.categoria = categoria
    motivo = ui.TextInput(label='Motivo', style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(name=f'ticket-{interaction.user.name}', overwrites=overwrites)
        await channel.send(content=f"{interaction.user.mention} Categoria: {self.categoria}", view=CloseTicketView())
        await interaction.response.send_message(f"Ticket: {channel.mention}", ephemeral=True)

class TicketDropdown(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label='Dúvidas', emoji='❓'),
            discord.SelectOption(label='Vendas', emoji='💰'),
            discord.SelectOption(label='Carrinho', emoji='🛒'),
            discord.SelectOption(label='Outros', emoji='⚠️'),
        ]
        super().__init__(placeholder='Selecione...', options=options)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self.values[0]))

@bot.command()
async def painel(ctx):
    view = ui.View(); view.add_item(TicketDropdown())
    await ctx.send(content="**Precisa de ajuda?**", view=view)

# LINHA PARA O RENDER
bot.run(os.environ.get('DISCORD_TOKEN'))
                            
