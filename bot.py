import discord
from discord.ext import commands
import sqlite3
import re
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import asyncio
import logging
import pytz
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "hy!"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Definir fuso horário para Brasília
FUSO_HORARIO = pytz.timezone("America/Sao_Paulo")

#Emojis
e_certo= "<:certo:1357559377921441975>"
e_errado= "<:errado:1357560063354601653>"
e_espere= "<:Espera:1357560117121253516>"

# Conectar ao banco de dados
db = sqlite3.connect("moderacao.db")
cursor = db.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS punicoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        moderador_id INTEGER,
        tipo TEXT,
        motivo TEXT,
        duracao TEXT,
        timestamp TEXT,
        ativo INTEGER
    )
""")
db.commit()

# Regex para converter tempo
TIME_REGEX = re.compile(r"(\d+)([smhd])")
TIME_MULTIPLIERS = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}

def parse_time(time_str):
    matches = TIME_REGEX.findall(time_str)
    if not matches:
        return None
    total_seconds = sum(int(value) * TIME_MULTIPLIERS[unit] for value, unit in matches)
    return timedelta(seconds=total_seconds)

# Canal de logs
LOG_CHANNEL_ID = 1043916988961017916

# IDs dos canais
CANAL_REGRAS = 1042250719920664639
CANAL_ATENDIMENTO = 1042250720583372964
CANAL_ENVIO = 1356009108402340162

# Cargo de admin
ADMIN_ROLE_ID = 1042250719450894361  

# ID da categoria de tickets
TICKET_CATEGORY_ID = 1358475716315975716


#imagem
IMAGEM_HYPEX = "https://cdn.discordapp.com/attachments/1356012837264298196/1356012878817132694/16693356531179.png?ex=67eef967&is=67eda7e7&hm=692e9393bdb4a26d372e5213498db246b08fd43fa19c4210eb971d7600365a1a&"
GIF_HYPEX = "https://cdn.discordapp.com/attachments/1357474337501745183/1357575717331931306/hypex_pulsante.gif?ex=67f0b469&is=67ef62e9&hm=19769528768c9d3430582d803f4459a97331533ee36d5565866ddc5f7503d3de&"

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(e)

# --------Comando ticket---------

# Categorias de ticket
CATEGORIAS_TICKET = {
    "suporte": {
        "nome": "Suporte",
        "descricao": "Problemas técnicos, bugs ou ajuda com comandos.",
        "emoji": "🛠️"
    },
    "denuncia": {
        "nome": "Denúncia",
        "descricao": "Reportar usuários, abusos ou violações de regras.",
        "emoji": "⚠️"
    },
    "parceria": {
        "nome": "Parceria",
        "descricao": "Solicitações de parceria com servidores ou bots.",
        "emoji": "🤝"
    }
}

# ----- Dropdown para escolher categoria -----
class CategoriaTicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=cat["nome"],
                description=cat["descricao"],
                emoji=cat["emoji"],
                value=key
            )
            for key, cat in CATEGORIAS_TICKET.items()
        ]
        super().__init__(placeholder="Escolha uma categoria", options=options, custom_id="categoria_ticket")

    async def callback(self, interaction: discord.Interaction):
        categoria_id = self.values[0]
        cat_info = CATEGORIAS_TICKET[categoria_id]
        guild = interaction.guild
        user = interaction.user

        ticket_name = f"{categoria_id}-{user.name}-{user.id}".lower().replace(" ", "-")
        existing_channel = discord.utils.get(guild.text_channels, name=ticket_name)
        if existing_channel:
            await interaction.response.send_message("Você já tem um ticket aberto nessa categoria!", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.get_role(ADMIN_ROLE_ID): discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        category = discord.utils.get(guild.categories, id=TICKET_CATEGORY_ID)
        ticket_channel = await guild.create_text_channel(ticket_name, overwrites=overwrites, category=category)

        embed = discord.Embed(
            title=f"{cat_info['emoji']} Ticket de {cat_info['nome']}",
            description=f"{user.mention}, sua solicitação foi enviada.
**Motivo:** {cat_info['descricao']}",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"{cat_info['nome']} | Ticket de {user}", icon_url=user.display_avatar.url)

        await ticket_channel.send(embed=embed, view=TicketOptionsView())
        await interaction.response.send_message(f"Seu ticket foi criado: {ticket_channel.mention}", ephemeral=True)

class SelectCategoriaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CategoriaTicketSelect())

# ----- View com botão "Abrir Ticket" principal -----
class AbrirTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green, custom_id="botao_abrir_ticket")
    async def abrir_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Selecione a Categoria do Ticket",
            description="Escolha abaixo o motivo do seu ticket para continuar.",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, view=SelectCategoriaView(), ephemeral=True)

# ----- View com botões do ticket -----
class TicketOptionsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Marcar como Resolvido", style=discord.ButtonStyle.blurple, custom_id="mark_resolved")
    async def marcar_resolvido(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Ticket Resolvido",
            description="Este ticket foi marcado como resolvido. Você pode reabrir ou fechar se necessário.",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Resolvido por {interaction.user}", icon_url=interaction.user.display_avatar.url)
        await interaction.message.edit(embed=embed, view=ResolvedTicketView())
        await interaction.response.send_message("Ticket marcado como resolvido!", ephemeral=True)

class ResolvedTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reabrir Ticket", style=discord.ButtonStyle.green, custom_id="reopen_ticket")
    async def reabrir_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Ticket Reaberto",
            description="Este ticket foi reaberto e está novamente disponível para atendimento.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Reaberto por {interaction.user}", icon_url=interaction.user.display_avatar.url)
        await interaction.message.edit(embed=embed, view=TicketOptionsView())
        await interaction.response.send_message("Ticket reaberto!", ephemeral=True)

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        user = interaction.user
        await channel.send("Fechando o ticket...")

        messages = [
            f"[{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {msg.author}: {msg.content}"
            async for msg in channel.history(limit=100, oldest_first=True)
        ]
        transcript = "\n".join(messages)

        os.makedirs("transcripts", exist_ok=True)
        filename = f"transcripts/transcript-{channel.name}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(transcript)

        file = discord.File(filename)
        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)

        if log_channel:
            log_embed = discord.Embed(
                title="Ticket Fechado",
                description=f"O ticket `{channel.name}` foi fechado por {user.mention}.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            log_embed.set_footer(text="Sistema de Tickets")
            await log_channel.send(embed=log_embed, file=file)

        await channel.send(file=file)
        await channel.delete()

# ----- Comando para painel de ticket -----
@bot.command(name="config_ticket")
@commands.has_permissions(administrator=True)
async def config_ticket(ctx):
    embed = discord.Embed(
        title="🎫 Central de Tickets",
        description="Clique no botão abaixo para abrir um ticket.
Você poderá escolher o motivo depois.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Sistema de Tickets")
    await ctx.send(embed=embed, view=AbrirTicketView())

#Comando para revisar
@bot.command()
@commands.has_permissions(administrator=True)
async def revisar(ctx, usuario: discord.Member, status: str, *, motivo: str = "Não especificado"):
    if status.lower() not in ["aceita", "negada"]:
        await ctx.send("Status inválido! Use 'aceito' ou 'negado'.")
        return
    
    revisor = ctx.author
    data_revisao = datetime.now()
    timestamp_unix = int(data_revisao.timestamp())

    
    if status.lower() == "aceita":
        embed = discord.Embed(title=f"{e_certo} - REVISÃO ACEITA", color=0x00ff00)
        embed.description = f"→ {usuario.mention}, sua revisão de punição foi **ACEITA**."
        embed.add_field(name="Motivo:", value=f"{motivo}", inline=False)
        embed.add_field(name="Revisor:", value=f"{revisor.mention}", inline=False)
        embed.add_field(name="Data de Revisão:", value=f"<t:{timestamp_unix}:F>", inline=False)
        embed.add_field(name="Status:", value=f"→ Sua punição foi removida/reduzida. Caso tenha dúvidas, entre em contato pelo canal <#{CANAL_ATENDIMENTO}>.", inline=False)
    
    else:
        embed = discord.Embed(title=f"{e_errado} - REVISÃO NEGADA", color=0xff0000)
        embed.description = f"→ {usuario.mention}, sua revisão de punição foi **NEGADA**."
        embed.add_field(name="Motivo:", value=f"{motivo}", inline=False)
        embed.add_field(name="Revisor:", value=f"{revisor.mention}", inline=False)
        embed.add_field(name="Data de Revisão:", value=f"<t:{timestamp_unix}:F>", inline=False)
        embed.add_field(name="Status:", value=f"→ A punição permanecerá ativa. Consulte as regras em <#{CANAL_REGRAS}> ou entre em contato pelo canal <#{CANAL_ATENDIMENTO}>.\n\n", inline=False)
        embed.add_field(name=f"{e_espere}", value="**Você poderá enviar uma nova revisão após 7 dias a partir desta resposta. Enviar antes desse prazo poderá resultar no encerramento automático da solicitação.**", inline=False)
    
    embed.set_footer(text="Rede Hypex", icon_url=IMAGEM_HYPEX)
    embed.set_thumbnail(url=GIF_HYPEX)
    canal = bot.get_channel(CANAL_ENVIO)
    await canal.send(embed=embed)
    await ctx.send(f"Revisão {status.upper()} enviada para {usuario.mention}!")
    
# Comando de Expulsão
@bot.command()
@commands.has_permissions(administrator=True)
async def kick(ctx, usuario: discord.Member, *, motivo: str):
    try:
        await usuario.kick(reason=motivo)
        embed = discord.Embed(title="👢 Usuário Expulso", color=0xFFA500)
        embed.add_field(name="Usuário", value=usuario.mention, inline=False)
        embed.add_field(name="Motivo", value=motivo, inline=False)
        embed.timestamp = datetime.now(FUSO_HORARIO)
        await send_log(embed)
        await ctx.send(f"{usuario.mention} foi expulso. Motivo: {motivo}")
    except discord.Forbidden:
        await ctx.send("Não tenho permissão para expulsar esse usuário.")
    except discord.HTTPException:
        await ctx.send("Ocorreu um erro ao tentar expulsar o usuário.")
        
# Comando para Punir
@bot.command()
@commands.has_permissions(administrator=True)
async def punir(ctx, usuario: discord.Member, tempo: str, *, motivo: str):
    duracao = parse_time(tempo)
    if duracao is None:
        await ctx.send("Formato de tempo inválido! Use algo como '1d 2h 30m'.")
        return
    fim_punicao = datetime.utcnow() + duracao
    cursor.execute("INSERT INTO punicoes (usuario_id, moderador_id, tipo, motivo, duracao, timestamp, ativo) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (usuario.id, ctx.author.id, "Mute", motivo, tempo, fim_punicao.strftime('%Y-%m-%d %H:%M:%S'), 1))
    db.commit()
    embed = discord.Embed(title="🔴 PUNIÇÃO APLICADA", color=0xFF0000)
    embed.add_field(name="Usuário", value=usuario.mention, inline=False)
    embed.add_field(name="Punido por", value=ctx.author.mention, inline=False)
    embed.add_field(name="Motivo", value=motivo, inline=False)
    embed.add_field(name="Duração", value=tempo, inline=False)
    embed.timestamp = datetime.now(FUSO_HORARIO)
    await send_log(embed)
    await ctx.send(f"✅ {usuario.mention} foi punido por {tempo}.")

# Comando para Banir
@bot.command()
@commands.has_permissions(administrator=True)
async def banir(ctx, usuario: discord.Member, *, motivo: str):
    try:
        await usuario.ban(reason=motivo)
        embed = discord.Embed(title="🚨 BANIMENTO", color=0xFF0000)
        embed.add_field(name="Usuário", value=usuario.mention, inline=False)
        embed.add_field(name="Banido por", value=ctx.author.mention, inline=False)
        embed.add_field(name="Motivo", value=motivo, inline=False)
        embed.timestamp = datetime.now(FUSO_HORARIO)
        await send_log(embed)
        await ctx.send(f"🚨 {usuario.mention} foi **banido**. Motivo: {motivo}")
    except discord.Forbidden:
        await ctx.send("Não tenho permissão para banir esse usuário.")
    except discord.HTTPException:
        await ctx.send("Ocorreu um erro ao tentar banir o usuário.")

# Comando para Desbanir
@bot.command()
@commands.has_permissions(administrator=True)
async def desbanir(ctx, usuario_id: int):
    try:
        usuario = await bot.fetch_user(usuario_id)
        await ctx.guild.unban(usuario)
        embed = discord.Embed(title="✅ DESBANIMENTO", color=0x00FF00)
        embed.add_field(name="Usuário", value=usuario.mention, inline=False)
        embed.add_field(name="Desbanido por", value=ctx.author.mention, inline=False)
        embed.timestamp = datetime.now(FUSO_HORARIO)
        await send_log(embed)
        await ctx.send(f"✅ {usuario.mention} foi **desbanido**.")
    except discord.NotFound:
        await ctx.send("Usuário não encontrado.")
    except discord.Forbidden:
        await ctx.send("Não tenho permissão para desbanir esse usuário.")
    except discord.HTTPException:
        await ctx.send("Ocorreu um erro ao tentar desbanir o usuário.")

# Comando para Remover Punições
@bot.command()
@commands.has_permissions(administrator=True)
async def remover_punicao(ctx, usuario: discord.Member):
    cursor.execute("UPDATE punicoes SET ativo = 0 WHERE usuario_id = ? AND ativo = 1", (usuario.id,))
    db.commit()
    embed = discord.Embed(title="⚠️ PUNIÇÃO REMOVIDA", color=0xFFFF00)
    embed.add_field(name="Usuário", value=usuario.mention, inline=False)
    embed.add_field(name="Removido por", value=ctx.author.mention, inline=False)
    embed.timestamp = datetime.now(FUSO_HORARIO)
    await send_log(embed)
    await ctx.send(f"⚠️ Punição de {usuario.mention} removida!")

# Comando para Remover Strike
@bot.command()
@commands.has_permissions(administrator=True)
async def remover_strike(ctx, usuario: discord.Member):
    cursor.execute("DELETE FROM punicoes WHERE usuario_id = ? AND ativo = 1 LIMIT 1", (usuario.id,))
    db.commit()
    embed = discord.Embed(title="✅ STRIKE REMOVIDO", color=0x00FF00)
    embed.add_field(name="Usuário", value=usuario.mention, inline=False)
    embed.add_field(name="Removido por", value=ctx.author.mention, inline=False)
    embed.timestamp = datetime.now(FUSO_HORARIO)
    await send_log(embed)
    await ctx.send(f"✅ Um strike foi removido de {usuario.mention}.")

# Comando para verificar strikes
@bot.command()
@commands.has_permissions(administrator=True)
async def strikes(ctx, usuario: discord.Member):
    cursor.execute("SELECT COUNT(*) FROM punicoes WHERE usuario_id = ? AND ativo = 1", (usuario.id,))
    total_strikes = cursor.fetchone()[0]
    embed = discord.Embed(title="⚠️ Histórico de Strikes", color=0xFFD700)
    embed.add_field(name="Usuário", value=usuario.mention, inline=False)
    embed.add_field(name="Total de Strikes", value=f"{total_strikes}/4", inline=False)
    embed.timestamp = datetime.now(FUSO_HORARIO)
    await send_log(embed)
    await ctx.send(embed=embed)

# Comando para exibir histórico de punições
@bot.command()
@commands.has_permissions(administrator=True)
async def historico(ctx, usuario: discord.Member):
    cursor.execute("SELECT tipo, motivo, duracao, timestamp FROM punicoes WHERE usuario_id = ?", (usuario.id,))
    punicoes = cursor.fetchall()
    embed = discord.Embed(title="📜 Histórico de Punições", color=0x00BFFF)
    embed.add_field(name="Usuário", value=usuario.mention, inline=False)
    for punicao in punicoes:
        embed.add_field(name=f"{punicao[0]} - {punicao[3]}", value=f"Motivo: {punicao[1]} | Duração: {punicao[2]}", inline=False)
    embed.timestamp = datetime.now(FUSO_HORARIO)
    await send_log(embed)
    await ctx.send(embed=embed)

# Comando para Exibir Comandos
@bot.command()
@commands.has_permissions(administrator=True)
async def comandos(ctx):
    embed = discord.Embed(title="📜 Lista de Comandos", color=0x3498db)
    embed.add_field(name="🔧 Comandos de Moderação", value=
        "`hy!punir @usuário tempo motivo` - Aplica um mute temporário.\n"
        "`hy!banir @usuário motivo` - Bane um usuário permanentemente.\n"
        "`hy!desbanir ID_DO_USUÁRIO` - Remove um banimento pelo ID.\n"
        "`hy!kick @usuário motivo` - Expulsa um usuário do servidor.\n"
        "`hy!remover_punicao @usuário` - Remove todas as punições ativas.\n"
        "`hy!revisar @usuário [aceita/negada] [motivo]` - Revisão de punição.\n",
        inline=False)

    embed.add_field(name="📊 Comandos de Monitoramento", value=
        "`hy!strikes @usuário` - Mostra a quantidade de strikes.\n"
        "`hy!historico @usuário` - Exibe o histórico de punições.\n"
        "`hy!remover_strike @usuário` - Remove um strike ativo.\n",
        inline=False)
        
    embed.add_field(name="🎫 Comando de tickets", value=
        "`hy!config_ticket` - Envia o painel inicial com o botão Abrir Ticket.\n",
        inline=False)    

    embed.add_field(name="📜 Comando de Listagem", value=
        "`hy!comandos` - Exibe esta lista de comandos.\n",
        inline=False)

    embed.set_footer(text="Apenas administradores podem usar esses comandos.")
    await ctx.send(embed=embed, ephemeral=True)

# Rodar o bot
bot.run(TOKEN)