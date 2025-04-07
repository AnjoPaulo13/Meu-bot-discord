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
import random
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#número aleatório
num_aleat = random.randint(1,100000000000000000000000000000)

# Carregar variáveis de ambiente
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "hy!"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Definir fuso horário para Brasília
FUSO_HORARIO = pytz.timezone("America/Sao_Paulo")

# Emojis
e_certo = "<:certo:1357559377921441975>"
e_errado = "<:errado:1357560063354601653>"
e_espere = "<:Espera:1357560117121253516>"
e_folha = "<:folha:1358624331063886036>"
e_youtube = "<:youtube:1358624299287580916>"
e_seta = "<:seta:1358643118768914635>"
e_seta_laranja = "<:setalaranja:1358643165233545467>"
e_foguete= "<:rocket:1055153521391042591>"
e_adicionado= "<:adicionado:1055153598511714397>"    
e_up= "<:up:1358670708238192770>"

# Emojis Gifs
g_martelo = "<a:gavel_gif:1042876485079412767>"
g_alerta = "<a:alert_dks:1042930533010767923>"

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
LOG_CHANNEL_ID_TICKET = 1358514192763715755
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

#Staff Log
    STAFF_ROLES = {
    1042250719450894361: 1,  # Equipe Staff
    1057811455388430456: 2,  # Builders
    1042250719450894365: 3,  # Ajudantes
    1042250719471882290: 4,  # Moderadores
    1042250719471882291: 5,  # Desenvolvedores
    1042250719471882292: 6,  # Administrador
    1042250719471882293: 7,  # Gerentes
    1042250719471882296: 8,  # Master
}

LOG_CHANNEL_ID = 1358433954146947142

def get_staff_rank(member: discord.Member):
    ranked_roles = [
        (role, STAFF_ROLES[role.id])
        for role in member.roles if role.id in STAFF_ROLES
    ]
    if not ranked_roles:
        return 0, None
    ranked_roles.sort(key=lambda x: x[1], reverse=True)
    return ranked_roles[0][1], ranked_roles[0][0].name.strip()

@bot.event
async def on_ready():
    print(f"Logado como {bot.user}")

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.roles == after.roles:
        return

    channel = after.guild.get_channel(LOG_CHANNEL_ID)
    if not channel:
        return

    timestamp_unix = int(datetime.now().timestamp())

    old_rank, old_role = get_staff_rank(before)
    new_rank, new_role = get_staff_rank(after)

    if old_rank == 0 and new_rank > 0:
        await channel.send(
            f"**{e_foguete} - Adicionado**;\n\n{e_adicionado} - {after.mention}, adicionado como {new_role} da Rede Hypex.\n\n<t:{timestamp_unix}:F>"
        )
    elif old_rank > 0 and new_rank == 0:
        await channel.send(
            f"**{e_foguete} - Removido**;\n\n⛔ - {after.mention}, removido da equipe de ({old_role}) da Rede Hypex.\n\n<t:{timestamp_unix}:F>"
        )
    elif old_rank > 0 and new_rank > 0:
        if new_rank > old_rank:
            await channel.send(
                f"**{e_foguete} - Promovido**;\n\n{e_up} - {after.mention}, promovido de {old_role} para {new_role} da Rede Hypex.\n\n<t:{timestamp_unix}:F>"
            )
        elif new_rank < old_rank:
            await channel.send(
                f"**{e_foguete} - Rebaixado**;\n\n{e_down} - {after.mention}, rebaixado de {old_role} para {new_role} da Rede Hypex.\n\n<t:{timestamp_unix}:F>"
            )

# --------Comando ticket---------

# Categorias de ticket
CATEGORIAS_TICKET = {
    "suporte": {
        "nome": "Suporte",
        "descricao": f"Problemas técnicos, bugs ou ajuda com comandos.",
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

        ticket_name = f"{categoria_id}-{user.name}-{user.id}-{num_aleat}".lower().replace(" ", "-")
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
            description=f"{user.mention}, sua solicitação foi enviada.\n **Motivo:** {cat_info['descricao']}",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"{cat_info['nome']} | Ticket de {user}", icon_url=IMAGEM_HYPEX)

        await ticket_channel.send(embed=embed, view=TicketOptionsView())

        # Descrição completa conforme a categoria escolhida
        descricao_completa = {
            "suporte": f"**{e_folha} - Suporte ao Jogador**\n\nSeu ticket foi criado e agora está na fila de atendimento da equipe Hypex!\nNosso time analisará sua solicitação e responderá o mais rápido possível.\n\nEnquanto isso:\n\n> Evite enviar mensagens repetidas para não atrasar o atendimento.\n> Certifique-se de que todas as informações e provas foram enviadas.\n> Fique de olho nas notificações do Discord!\n\nAgradecemos por entrar em contato com a Hypex, já já alguém da equipe estará com você!\n\nAtenciosamente,\nEquipe Hypex.",
            "denuncia": f"**{g_martelo} Denúncias**\n\nNotou alguma atitude suspeita ou comportamento inadequado dentro do servidor Hypex? Utilize este canal para enviar sua denúncia de forma clara e organizada. Sua colaboração é essencial para mantermos um ambiente justo e seguro para todos.\n\n> Nickname do jogador denunciado:\n> Motivo da denúncia:\n> Data e horário aproximado:\n> Servidor/minigame:\n> Provas (prints, vídeos):\n\n***Importante: Denúncias sem provas ou com informações incompletas podem ser desconsideradas. Evite denúncias falsas, isso pode resultar em punições para o denunciante.***\n\nAtenciosamente,\nEquipe Hypex.",
            "parceria": f"**{e_youtube} - Solicitação de Parceria**\n\nEstá interessado(a) em firmar uma parceria com o servidor Hypex? Valorizamos colaborações que tragam benefícios mútuos e fortaleçam nossa comunidade. Para que sua proposta seja avaliada corretamente, solicitamos que siga o modelo abaixo ao abrir o ticket:\n\n**Modelo de Solicitação:**\n\n> Nome do projeto ou criador:\n> Tipo de parceria desejada:\n> Plataformas utilizadas:\n> Métricas e dados relevantes:\n> Público-alvo:\n> Proposta detalhada:\n> Links relevantes:\n\nTodas as propostas serão avaliadas com atenção. Apenas solicitações completas e bem estruturadas serão consideradas.\n\nAtenciosamente,\nEquipe Hypex."
        }

        embed_info = discord.Embed(
            title=f"Informações sobre o Ticket - {cat_info['nome']}",
            description=descricao_completa[categoria_id],
            color=discord.Color.from_str("#20B2AA")
        )
        embed_info.set_footer(text="Hypex - Sistema de Tickets", icon_url=IMAGEM_HYPEX)
        await ticket_channel.send(embed=embed_info)
        

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

        with open(filename, "rb") as f:
            file = discord.File(f, filename=os.path.basename(filename))
            log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID_TICKET)

            if log_channel:
                log_embed = discord.Embed(
                    title="Ticket Fechado",
                    description=f"O ticket `{channel.name}` foi fechado por {user.mention}.",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                log_embed.set_footer(text="Sistema de Tickets\nPor: AnjoPaulo13")
                await log_channel.send(embed=log_embed, file=file)

            await channel.send(file=file)
            await channel.delete()
        
# ----- Comando para painel de ticket -----
@bot.command(name="config_ticket")
@commands.has_permissions(administrator=True)
async def config_ticket(ctx):
    embed = discord.Embed(
        title="🎫 Central de Tickets",
        description="Clique no botão abaixo para abrir um ticket.\nVocê poderá escolher o motivo depois.",
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
        
@bot.command()
@commands.has_permissions(administrator=True)
async def punir(ctx, usuario: discord.Member, tempo: str, *, motivo: str):
    duracao = parse_time(tempo)
    if duracao is None:
        await ctx.send("Formato de tempo inválido! Use algo como '1d 2h 30m'.")
        return

    fim_punicao = datetime.utcnow() + duracao
    cursor.execute(
        "INSERT INTO punicoes (usuario_id, moderador_id, tipo, motivo, duracao, timestamp, ativo) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (usuario.id, ctx.author.id, "Mute", motivo, tempo, fim_punicao.strftime('%Y-%m-%d %H:%M:%S'), 1)
    )
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
    # Tenta buscar o usuário
    try:
        usuario = await bot.fetch_user(usuario_id)
    except discord.NotFound:
        await ctx.send("Usuário não encontrado.")
        return

    # Pega a lista de banidos e verifica se o usuário está nela
    banidos = [entry async for entry in ctx.guild.bans()]
    if not any(ban_entry.user.id == usuario_id for ban_entry in banidos):
        await ctx.send("Esse usuário não está banido.")
        return

    # Tenta desbanir
    try:
        await ctx.guild.unban(usuario)

        nome_formatado = f"{usuario.name}#{usuario.discriminator} (`{usuario.id}`)"

        embed = discord.Embed(
            title="✅ DESBANIMENTO",
            color=discord.Color.green(),
            timestamp=datetime.now(FUSO_HORARIO)
        )
        embed.add_field(name="Usuário", value=nome_formatado, inline=False)
        embed.add_field(name="Desbanido por", value=ctx.author.mention, inline=False)

        # Adiciona avatar se disponível
        if usuario.avatar:
            embed.set_thumbnail(url=usuario.avatar.url)

        await send_log(embed)
        await ctx.send(f"✅ `{nome_formatado}` foi **desbanido** com sucesso.")
    except discord.Forbidden:
        await ctx.send("Não tenho permissão para desbanir esse usuário.")
    except discord.HTTPException as e:
        await ctx.send(f"Ocorreu um erro ao tentar desbanir o usuário. Código: {e.status}")
        
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
    
# Função auxiliar para enviar o log
async def send_log(embed):
    canal_log = bot.get_channel(LOG_CHANNEL_ID)
    if canal_log:
        await canal_log.send(embed=embed)
        
# Rodar o bot
bot.run(TOKEN)