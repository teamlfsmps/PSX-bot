import discord
from discord.ext import commands
from discord import ui, app_commands
import datetime
import os
import asyncio
from flask import Flask
from threading import Thread

# --- SERVIDOR WEB (KEEP ALIVE) ---
app = Flask('')
@app.route('/')
def home(): return "Bot PSX Multi-Servidor Online!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- BANCO DE DADOS EM MEMÓRIA ---
servidores_config = {}

# --- CONFIGURAÇÃO DO BOT ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, help_command=None)
    async def setup_hook(self):
        await self.tree.sync()
        print(f"Comandos sincronizados para {self.user}")

bot = MyBot()

# --- SISTEMA DE AVALIAÇÃO COM FEEDBACK ESCRITO ---
class FeedbackModal(ui.Modal):
    def __init__(self, nota, user_name, guild_id):
        super().__init__(title="Feedback do Atendimento")
        self.nota = nota
        self.user_name = user_name
        self.guild_id = guild_id
    
    comentario = ui.TextInput(label='O que achou do atendimento?', style=discord.TextStyle.paragraph, placeholder='Escreva aqui (opcional)...', required=False)

    async def on_submit(self, interaction: discord.Interaction):
        config = servidores_config.get(self.guild_id)
        msg = f"Obrigado pelo feedback de {self.nota} estrelas, {self.user_name}! 🥰" if int(self.nota) >= 3 else f"Sentimos muito, {self.user_name}. Vamos melhorar! 😔"
        await interaction.response.send_message(msg, ephemeral=True)

        # Envia para o canal de log configurado ou o padrão
        log_id = int(config['log_id']) if config and config.get('log_id') else 1471325652991869038
        canal = bot.get_channel(log_id)
        if canal:
            cor = discord.Color.green() if int(self.nota) >= 3 else discord.Color.red()
            embed = discord.Embed(title="📥 Nova Avaliação Recebida", color=cor, timestamp=datetime.datetime.now())
            embed.add_field(name="Membro", value=self.user_name, inline=True)
            embed.add_field(name="Nota", value=f"{self.nota} ⭐", inline=True)
            embed.add_field(name="Feedback", value=self.comentario.value or "Sem comentário.", inline=False)
            await canal.send(embed=embed)

class EvalDropdown(ui.Select):
    def __init__(self, user_name, guild_id):
        self.user_name = user_name
        self.guild_id = guild_id
        options = [discord.SelectOption(label=f"{i} Estrelas", value=str(i), emoji="⭐") for i in range(5, 0, -1)]
        super().__init__(placeholder="Selecione sua nota aqui", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(FeedbackModal(self.values[0], self.user_name, self.guild_id))

# --- SISTEMA DE TICKETS ---
class CloseTicketView(ui.View):
    def __init__(self, guild_id): 
        super().__init__(timeout=None)
        self.guild_id = guild_id
    
    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.user
        data_f = datetime.datetime.now().strftime("%d/%m/%Y")
        embed_fin = discord.Embed(title="Ticket Finalizado", description=f"🔒 **Fechado por:** {user.mention}\n📅 **Data:** {data_f}\n\nAvalie-nos abaixo:", color=discord.Color.red())
        
        view_eval = ui.View(); view_eval.add_item(EvalDropdown(user.name, self.guild_id))
        try: await user.send(embed=embed_fin, view=view_eval)
        except: pass
        await interaction.channel.delete()

class TicketModal(ui.Modal, title='Formulário de Suporte'):
    def __init__(self, categoria, guild_id):
        super().__init__()
        self.categoria = categoria
        self.guild_id = guild_id
    motivo = ui.TextInput(label='Qual o motivo do contato?', style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        channel = await guild.create_text_channel(name=f'ticket-{interaction.user.name}', overwrites=overwrites)
        
        emb = discord.Embed(title="🎫 Suporte PSX", description=f"Olá {interaction.user.mention}!\n\n**📂 Categoria:** {self.categoria}\n**📝 Motivo:** {self.motivo.value}", color=discord.Color.blue())
        await channel.send(content=interaction.user.mention, embed=emb, view=CloseTicketView(self.guild_id))
        await interaction.response.send_message(f"✅ Ticket criado em {channel.mention}", ephemeral=True)

class TicketView(ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        config = servidores_config.get(guild_id)
        
        # Categorias Padrão caso não tenha config !rr
        options = [
            discord.SelectOption(label='Dúvidas', description='Tire suas dúvidas gerais', emoji='❓'),
            discord.SelectOption(label='Vendas', description='Questões sobre compras', emoji='💰'),
            discord.SelectOption(label='Carrinho', description='Produtos no carrinho', emoji='🛒'),
            discord.SelectOption(label='Outros', description='Assuntos diversos', emoji='⚠️')
        ]

        # Se houver configuração do !rr, usa as categorias personalizadas
        if config and config.get('categorias'):
            options = [discord.SelectOption(label=c['nome'], description=c['desc']) for c in config['categorias']]

        select = ui.Select(placeholder="Escolha uma categoria...", options=options)
        async def callback(interaction):
            await interaction.response.send_modal(TicketModal(select.values[0], guild_id))
        select.callback = callback
        self.add_item(select)

# --- COMANDO DE CONFIGURAÇÃO !RR ---
@bot.command()
@commands.has_permissions(administrator=True)
async def rr(ctx):
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        await ctx.send("⚙️ **Iniciando Configuração PSX**\n1° Etapa - Diga o **ID do canal de logs** de avaliações:")
        msg_log = await bot.wait_for('message', check=check, timeout=60)
        
        await ctx.send("2° Etapa - Diga o **Texto do Painel** (Ex: Olá, este é o suporte...):")
        msg_texto = await bot.wait_for('message', check=check, timeout=120)

        await ctx.send("3° Etapa - Diga as **Categorias** (Siga o modelo: `Nome | Descrição # Nome | Descrição`):")
        msg_cats = await bot.wait_for('message', check=check, timeout=180)
        
        cats = []
        for p in msg_cats.content.split('#'):
            if '|' in p:
                nome, desc = p.split('|')
                cats.append({'nome': nome.strip(), 'desc': desc.strip()})

        await ctx.send("4° Etapa - Mande o link do **Banner** ou digite `skip`:")
        msg_banner = await bot.wait_for('message', check=check, timeout=60)
        banner = None if msg_banner.content.lower() == 'skip' else msg_banner.content

        servidores_config[ctx.guild.id] = {'log_id': msg_log.content, 'texto': msg_texto.content, 'categorias': cats, 'banner': banner}
        await ctx.send("✅ **Configuração salva com sucesso!** Use `/painel` para ver seu novo ticket.")
    except asyncio.TimeoutError:
        await ctx.send("❌ Tempo esgotado.")

# --- COMANDOS DE BARRA (SLASH COMMANDS) ---
@bot.tree.command(name="painel", description="Envia o painel de atendimento")
async def painel(interaction: discord.Interaction):
    config = servidores_config.get(interaction.guild_id)
    
    # Se não configurou, usa o padrão bonitão que já tínhamos
    txt = config['texto'] if config else "Selecione a categoria desejada para iniciar um suporte privado."
    banner = config['banner'] if config else "https://cdn.discordapp.com/attachments/1470856469179269338/1471317877125808410/1770749281157.png"

    embed = discord.Embed(title="CENTRAL DE ATENDIMENTO - PSX", description=txt, color=discord.Color.blue())
    if banner: embed.set_image(url=banner)
    embed.set_footer(text="PSX Store | Atendimento Rápido")
    
    await interaction.response.send_message(embed=embed, view=TicketView(interaction.guild_id))

@bot.tree.command(name="ajuda", description="Lista detalhada de comandos")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(title="✨ Central de Informações PSX", description="Aqui estão os comandos para navegar no bot!", color=discord.Color.gold())
    embed.add_field(name="📂 **Categorias**", value="---", inline=False)
    embed.add_field(name="🎫 **Tickets**", value="`/painel` - Abrir suporte\n`!rr` - Configurar (ADM)", inline=True)
    embed.add_field(name="⚙️ **Utilidade**", value="`/ping` - Latência\n`/ajuda` - Comandos", inline=True)
    embed.set_footer(text="Use / antes de cada comando!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Verifica a latência do bot")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 **Pong!** `{round(bot.latency * 1000)}ms`", ephemeral=True)

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('DISCORD_TOKEN'))
    
