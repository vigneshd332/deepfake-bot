import requests
import logging
from discord.ext import commands


logger = logging.getLogger(__name__)


class SillyCog(commands.Cog):
    """Some silly, fun commands"""
    def __init__(self, bot):
        self.bot = bot
        self.config = self.bot.get_cog('ConfigCog').configuration

    async def cog_check(self, ctx):
        if ctx.guild.id not in self.config.white_list_server_ids:
            await ctx.send('Sorry, I don\'t have permission to run on this server.')
            return False

        return True

    @commands.command()
    async def catfact(self, ctx):
        """Because everyone loves cat facts"""

        response = requests.get('https://catfact.ninja/fact')

        if response.status_code == 200:
            result = response.json()['fact']
            await ctx.send(result)
        else:
            await ctx.send('Something is wrong. Sorry...')

    @commands.command()
    async def catpic(self, ctx):
        """Because everyone loves cat pics"""
        
        response = requests.get('https://api.thecatapi.com/v1/images/search')

        if response.status_code == 200:
            result = response.json()[0]['url']
            await ctx.send(result)
        else:
            await ctx.send('Something is wrong. Sorry...')

    @commands.command()
    async def asciify(self, ctx, txt):
        """Makes ascii art out of your text. E.g.: `df1!asciify "I am awesome"`"""
        
        url = 'http://artii.herokuapp.com/make?text=' + txt.replace(' ', '+')
        response = requests.get(url)

        if response.status_code == 200:
            await ctx.send(f'```{response.text}```')
        else:
            await ctx.send('Something is wrong. Sorry...')
