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

#imagem
IMAGEM_FOOTER = "https://cdn.discordapp.com/attachments/1356012837264298196/1356012878817132694/16693356531179.png?ex=67eef967&is=67eda7e7&hm=692e9393bdb4a26d372e5213498db246b08fd43fa19c4210eb971d7600365a1a&"


@bot.command()
@commands.has_permissions(administrator=True)
async def revisao(ctx, usuario: discord.Member, status: str, *, motivo: str = "Não especificado"):
    if status.lower() not in ["aceita", "negada"]:
        await ctx.send("Status inválido! Use 'aceito' ou 'negado'.")
        return
    
    revisor = ctx.author
    data_revisao = datetime.now(FUSO_HORARIO)
    
    if status.lower() == "aceita":
        embed = discord.Embed(title="✅ - REVISÃO ACEITA", color=0x00ff00)
        embed.description = f"→ {usuario.mention}, sua revisão de punição foi **ACEITA**."
        embed.add_field(name="Motivo:", value=f"{motivo}", inline=False)
        embed.add_field(name="Revisor:", value=f"{revisor.mention}", inline=False)
        embed.add_field(name="Data de Revisão:", value=data_revisao, inline=False)
        embed.add_field(name="Status:", value=f"→ Sua punição foi removida/reduzida. Caso tenha dúvidas, entre em contato pelo canal <#{CANAL_ATENDIMENTO}>.", inline=False)
    
    else:
        embed = discord.Embed(title="❌ - REVISÃO NEGADA", color=0xff0000)
        embed.description = f"→ {usuario.mention}, sua revisão de punição foi **NEGADA**."
        embed.add_field(name="Motivo:", value=f"{motivo}", inline=False)
        embed.add_field(name="Revisor:", value=f"{revisor.mention}", inline=False)
        embed.add_field(name="Data de Revisão:", value=data_revisao, inline=False)
        embed.add_field(name="Status:", value=f"→ A punição permanecerá ativa. Consulte as regras em <#{CANAL_REGRAS}> ou entre em contato pelo canal <#{CANAL_ATENDIMENTO}>.", inline=False)
        embed.add_field(name="⏰", value="**Você poderá enviar uma nova revisão após 7 dias a partir desta resposta. Enviar antes desse prazo poderá resultar no encerramento automático da solicitação.**", inline=False)
    
    embed.set_footer(text="Rede Hypex", icon_url=IMAGEM_FOOTER)
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
        "hy!punir @usuário tempo motivo - Aplica um mute temporário.\n"
        "hy!banir @usuário motivo - Bane um usuário permanentemente.\n"
        "hy!desbanir ID_DO_USUÁRIO - Remove um banimento pelo ID.\n"
        "hy!kick @usuário motivo - Expulsa um usuário do servidor.\n"
        "hy!remover_punicao @usuário - Remove todas as punições ativas.\n"
        "hy!revisao @usuário [aceita/negada] [motivo] - Revisão de punição.\n",
        inline=False)

    embed.add_field(name="📊 Comandos de Monitoramento", value=
        "`hy!strikes @usuário` - Mostra a quantidade de strikes.\n"
        "`hy!historico @usuário` - Exibe o histórico de punições.\n"
        "`hy!remover_strike @usuário` - Remove um strike ativo.\n",
        inline=False)

    embed.add_field(name="📜 Comando de Listagem", value=
        "`hy!comandos` - Exibe esta lista de comandos.\n",
        inline=False)

    embed.set_footer(text="Apenas administradores podem usar esses comandos.")
    await ctx.send(embed=embed, ephemeral=True)

# Rodar o bot
bot.run(TOKEN)