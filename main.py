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

# --- SISTEMA DE AVALIAÇÃO COM FEEDBACK ---
class FeedbackModal(ui.Modal):
    def __init__(self, nota, user_name):
        super().__init__(title="Feedback do Atendimento")
        self.nota = nota
        self.user_name = user_name
    
    comentario = ui.TextInput(label='Comentário (Opcional)', style=discord.TextStyle.paragraph, placeholder='Diga o que achou do nosso suporte...', required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if int(self.nota) <= 2:
            msg = f"Sentimos muito, {self.user_name}. 😔 Vamos trabalhar para melhorar!"
            cor = discord.Color.red()
        else:
            msg = f"Obrigado pelo feedback positivo, {self.user_name}! 🥰"
            cor = discord.Color.green()

        await interaction.response.send_message(msg, ephemeral=True)

        canal = bot.get_channel(1471325652991869038)
        if canal:
            txt = self.comentario.value if self.comentario.value else "Sem comentário."
            embed = discord.Embed(title="📥 Avaliação PSX Store", color=cor, timestamp=datetime.datetime.now())
            embed.add_field(name="Usuário", value=self.user_name, inline=True)
            embed.add_field(name="Nota", value=f"{self.nota} ⭐", inline=True)
            embed.add_field(name="Feedback", value=txt, inline=False)
            await canal.send(embed=embed)

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
        super().__init__(placeholder="Selecione sua nota aqui", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(FeedbackModal(self.values[0], self.user_name))

# --- TICKET E FINALIZAÇÃO ---
class CloseTicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.user
        data_atual = datetime.datetime.now().strftime("%d/%m/%Y")
        
        # Embed Arrumadinha de Finalização
        embed_fin = discord.Embed(title="Seu Ticket foi Finalizado!", color=discord.Color.red())
        embed_fin.description = f"🔒 | **Fechado por:** {user.mention}\n📅 | **Data:** {data_atual}\n\nPor favor, avalie nosso atendimento abaixo:"
        
        view_eval = ui.View(); view_eval.add_item(EvalDropdown(user.name))
        
        try: await user.send(embed=embed_fin, view=view_eval)
        except: pass
        await interaction.channel.delete()

class TicketModal(ui.Modal, title='Formulário de Suporte'):
    def __init__(self, categoria):
        super().__init__()
        self.categoria = categoria
    motivo = ui.TextInput(label='Qual o motivo do contato?', style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        channel = await guild.create_text_channel(name=f'ticket-{interaction.user.name}', overwrites=overwrites)
        
        emb = discord.Embed(title="🎫 Suporte PSX", description=f"Olá {interaction.user.mention}, você abriu um ticket!\n\n**📂 Categoria:** {self.categoria}\n**📝 Motivo:** {self.motivo.value}\n\nEm breve nossa equipe irá te atender.", color=discord.Color.blue())
        await channel.send(content=interaction.user.mention, embed=emb, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Seu ticket foi aberto em {channel.mention}", ephemeral=True)

class TicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.select(placeholder="Escolha uma categoria para atendimento...", options=[
        discord.SelectOption(label='Dúvidas', description='Tire suas dúvidas gerais', emoji='❓'),
        discord.SelectOption(label='Vendas', description='Questões sobre compras e pagamentos', emoji='💰'),
        discord.SelectOption(label='Carrinho', description='Dúvidas sobre produtos no carrinho', emoji='🛒'),
        discord.SelectOption(label='Outros', description='Assuntos diversos', emoji='⚠️')])
    async def select_callback(self, interaction, select):
        await interaction.response.send_modal(TicketModal(select.values[0]))

# --- COMANDOS DE BARRA ---

@bot.tree.command(name="painel", description="Envia o painel de tickets")
async def painel(interaction: discord.Interaction):
    embed = discord.Embed(title="CENTRAL DE ATENDIMENTO - PSX", description="Selecione a categoria desejada no menu abaixo para iniciar um atendimento privado com nossa equipe.", color=discord.Color.blue())
    embed.set_image(url="https://cdn.discordapp.com/attachments/1470856469179269338/1471317877125808410/1770749281157.png")
    embed.set_footer(text="Estamos prontos para te ajudar!")
    await interaction.response.send_message(embed=embed, view=TicketView())

@bot.tree.command(name="ajuda", description="Veja meus comandos")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(title="❓ Central de Ajuda", color=discord.Color.gold(), timestamp=datetime.datetime.now())
    embed.add_field(name="🎫 Suporte", value="`/painel` - Abrir menu de tickets", inline=True)
    embed.add_field(name="⚙️ Sistema", value="`/ping` - Ver latência do bot", inline=True)
    embed.add_field(name="📖 Informação", value="`/ajuda` - Ver esta lista", inline=True)
    embed.set_footer(text="PSX Store - Qualidade e Rapidez")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Veja a velocidade do bot")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 **Pong!** Minha latência atual é `{round(bot.latency * 1000)}ms`", ephemeral=True)

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('DISCORD_TOKEN'))
                 
