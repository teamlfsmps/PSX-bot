import discord
from discord.ext import commands
from discord import ui, app_commands
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

# --- CONFIGURAÇÃO DO BOT ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, help_command=None)
    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

# --- MODAL DE FEEDBACK ESCRITO ---
class FeedbackModal(ui.Modal):
    def __init__(self, nota, user_name):
        super().__init__(title="Feedback Adicional")
        self.nota = nota
        self.user_name = user_name
    
    comentario = ui.TextInput(label='O que podemos melhorar ou o que gostou?', style=discord.TextStyle.paragraph, placeholder='Escreva seu feedback aqui (opcional)...', required=False)

    async def on_submit(self, interaction: discord.Interaction):
        # Mensagens diferenciadas por nota
        if int(self.nota) <= 2:
            msg_user = f"Sentimos muito pelo transtorno, {self.user_name}. 😔 Vamos trabalhar duro para melhorar nosso serviço!"
            cor_log = discord.Color.red()
        else:
            msg_user = f"Muito obrigado pela avaliação positiva, {self.user_name}! 🥰 Isso nos motiva a continuar evoluindo."
            cor_log = discord.Color.green()

        await interaction.response.send_message(msg_user, ephemeral=True)

        # Envio para o canal de logs
        ID_CANAL_LOG = 1471325652991869038
        canal = bot.get_channel(ID_CANAL_LOG)
        if canal:
            feedback_texto = self.comentario.value if self.comentario.value else "Nenhum comentário enviado."
            embed = discord.Embed(title="📥 Novo Feedback Recebido", color=cor_log, timestamp=datetime.datetime.now())
            embed.add_field(name="Membro", value=self.user_name, inline=True)
            embed.add_field(name="Nota", value=f"{self.nota} ⭐", inline=True)
            embed.add_field(name="Comentário", value=feedback_texto, inline=False)
            await canal.send(embed=embed)

# --- SELECT DE ESTRELAS ---
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
        super().__init__(placeholder="Avalie com estrelas aqui", options=options)

    async def callback(self, interaction: discord.Interaction):
        # Abre o modal para o usuário escrever o motivo/feedback
        await interaction.response.send_modal(FeedbackModal(self.values[0], self.user_name))

# --- ESTRUTURA DE TICKET E COMANDOS ---
class CloseTicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.user
        view_eval = ui.View(); view_eval.add_item(EvalDropdown(user.name))
        try: await user.send(content=f"Olá {user.mention}, seu ticket foi encerrado. Como foi sua experiência?", view=view_eval)
        except: pass
        await interaction.channel.delete()

class TicketModal(ui.Modal, title='Abrir Ticket'):
    def __init__(self, categoria):
        super().__init__()
        self.categoria = categoria
    motivo = ui.TextInput(label='Motivo do contato', style=discord.TextStyle.paragraph)
    async def on_submit(self, interaction: discord.Interaction):
        overwrites = {interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False), interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        channel = await interaction.guild.create_text_channel(name=f'ticket-{interaction.user.name}', overwrites=overwrites)
        embed = discord.Embed(title="Suporte Iniciado", description=f"**Categoria:** {self.categoria}\n**Motivo:** {self.motivo.value}", color=discord.Color.blue())
        await channel.send(content=interaction.user.mention, embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"Ticket criado: {channel.mention}", ephemeral=True)

class TicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.select(placeholder="Escolha uma categoria...", options=[
        discord.SelectOption(label='Dúvidas', description='Tire suas dúvidas gerais', emoji='❓'),
        discord.SelectOption(label='Vendas', description='Questões sobre compras', emoji='💰'),
        discord.SelectOption(label='Outros', description='Outros assuntos', emoji='⚠️')])
    async def select_callback(self, interaction, select):
        await interaction.response.send_modal(TicketModal(select.values[0]))

@bot.tree.command(name="painel", description="Envia o painel de atendimento")
async def painel_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="CENTRAL DE ATENDIMENTO - PSX", description="Selecione a categoria abaixo para iniciar o suporte.", color=discord.Color.blue())
    embed.set_image(url="https://cdn.discordapp.com/attachments/1470856469179269338/1471317877125808410/1770749281157.png")
    await interaction.response.send_message(embed=embed, view=TicketView())

@bot.tree.command(name="ping", description="Verifica a latência do bot")
async def ping_slash(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latência: **{round(bot.latency * 1000)}ms**")

@bot.tree.command(name="ajuda", description="Comandos do bot")
async def ajuda_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="❓ Ajuda", description="**/painel** - Abrir ticket\n**/ping** - Testar velocidade\n**/ajuda** - Ver esta lista", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('DISCORD_TOKEN'))
    
