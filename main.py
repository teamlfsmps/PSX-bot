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

# --- COMPONENTES DE AVALIAÇÃO ---
class FeedbackModal(ui.Modal):
    def __init__(self, nota, user_name):
        super().__init__(title="Feedback do Atendimento")
        self.nota = nota
        self.user_name = user_name
    
    comentario = ui.TextInput(label='O que achou do atendimento?', style=discord.TextStyle.paragraph, placeholder='Escreva aqui seu feedback...', required=False)

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
            embed.add_field(name="Membro", value=self.user_name, inline=True)
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

# --- SISTEMA DE TICKETS ---
class CloseTicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.user
        data_f = datetime.datetime.now().strftime("%d/%m/%Y")
        
        embed_fin = discord.Embed(title="Ticket Finalizado com Sucesso", color=discord.Color.red())
        embed_fin.description = f"🔒 | **Fechado por:** {user.mention}\n📅 | **Data:** {data_f}\n\nA PSX agradece o contato! Por favor, avalie-nos abaixo."
        
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
        
        emb = discord.Embed(title="🎫 Suporte PSX", description=f"Olá {interaction.user.mention}!\n\n**📂 Categoria:** {self.categoria}\n**📝 Motivo:** {self.motivo.value}\n\nAguarde o atendimento da nossa equipe.", color=discord.Color.blue())
        await channel.send(content=interaction.user.mention, embed=emb, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Seu ticket foi aberto em {channel.mention}", ephemeral=True)

class TicketView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.select(placeholder="Escolha uma categoria para atendimento...", options=[
        discord.SelectOption(label='Dúvidas', description='Tire suas dúvidas gerais sobre a loja', emoji='❓'),
        discord.SelectOption(label='Vendas', description='Questões relacionadas a compras e pagamentos', emoji='💰'),
        discord.SelectOption(label='Carrinho', description='Problemas ou dúvidas com produtos no carrinho', emoji='🛒'),
        discord.SelectOption(label='Outros', description='Assuntos diversos não listados', emoji='⚠️')])
    async def select_callback(self, interaction, select):
        await interaction.response.send_modal(TicketModal(select.values[0]))

# --- COMANDOS DE BARRA (SLASH COMMANDS) ---

@bot.tree.command(name="painel", description="Envia o painel de atendimento oficial")
async def painel(interaction: discord.Interaction):
    embed = discord.Embed(title="CENTRAL DE ATENDIMENTO - PSX", description="Selecione a categoria desejada no menu abaixo para iniciar um atendimento privado.", color=discord.Color.blue())
    embed.set_image(url="https://cdn.discordapp.com/attachments/1470856469179269338/1471317877125808410/1770749281157.png")
    embed.set_footer(text="PSX Store | Atendimento Rápido")
    await interaction.response.send_message(embed=embed, view=TicketView())

@bot.tree.command(name="ajuda", description="Lista detalhada de comandos")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(
        title="✨ Central de Informações PSX",
        description="Aqui estão todos os meus comandos disponíveis para facilitar sua navegação!",
        color=discord.Color.gold(),
        timestamp=datetime.datetime.now()
    )
    
    embed.add_field(name="📂 **Categorias**", value="---", inline=False)
    
    embed.add_field(
        name="🎫 **Tickets**", 
        value="`/painel` - Abre o menu de suporte\n`/fechar` - Encerra o atendimento", 
        inline=True
    )
    
    embed.add_field(
        name="⚙️ **Utilidade**", 
        value="`/ping` - Velocidade de resposta\n`/ajuda` - Lista de comandos", 
        inline=True
    )

    embed.add_field(
        name="🎮 **Divertidos**", 
        value="`Dado`, `Moeda` (Em breve!)", 
        inline=True
    )

    embed.set_footer(text="Dica: Use / antes de cada comando!", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Verifica a latência do bot")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 **Pong!** Minha velocidade atual é de `{round(bot.latency * 1000)}ms`", ephemeral=True)

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('DISCORD_TOKEN'))
            
