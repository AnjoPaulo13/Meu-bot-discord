import discord
from discord.ext import commands
from datetime import datetime, timedelta

class StaffLog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    # Emojis        
    e_foguete = "<:rocket:1055153521391042591>"
    e_adicionado = "<:adicionado:1055153598511714397>"
    e_up = "<:up:1358670708238192770>"
    e_down = "<:down:1358672309984165918>"

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

    def get_staff_rank(self, member: discord.Member):
    ranked_roles = [
        (role, self.STAFF_ROLES[role.id])
        for role in member.roles if role.id in self.STAFF_ROLES
    ]
    if not ranked_roles:
        return 0, None
    ranked_roles.sort(key=lambda x: x[1], reverse=True)
    return ranked_roles[0][1], ranked_roles[0][0].name.strip()
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.roles == after.roles:
            return

        channel = after.guild.get_channel(self.LOG_CHANNEL_ID)
        if not channel:
            return

        # Atualiza o timestamp dinamicamente
        timestamp_unix = int(datetime.now().timestamp())

        old_rank, old_role = self.get_staff_rank(before)
        new_rank, new_role = self.get_staff_rank(after)

        if old_rank == 0 and new_rank > 0:
            await channel.send(
                f"**{self.e_foguete} - Adicionado**;\n\n{self.e_adicionado} - {after.mention}, adicionado como {new_role} da Rede Hypex.\n\n<t:{timestamp_unix}:F>"
            )
        elif old_rank > 0 and new_rank == 0:
            await channel.send(
                f"**{self.e_foguete} - Removido**;\n\n⛔ - {after.mention}, removido da equipe de ({old_role}) da Rede Hypex.\n\n<t:{timestamp_unix}:F>"
            )
        elif old_rank > 0 and new_rank > 0:
            if new_rank > old_rank:
                await channel.send(
                    f"**{self.e_foguete} - Promovido**;\n\n{self.e_up} - {after.mention}, promovido de {old_role} para {new_role} da Rede Hypex.\n\n<t:{timestamp_unix}:F>"
                )
            elif new_rank < old_rank:
                await channel.send(
                    f"**{self.e_foguete} - Rebaixado**;\n\n{self.e_down} - {after.mention}, rebaixado de {old_role} para {new_role} da Rede Hypex.\n\n<t:{timestamp_unix}:F>"
                )

async def setup(bot):
    await bot.add_cog(StaffLog(bot))