from discord.ext import commands
from cryptography.fernet import Fernet
import gzip
import markovify
import json
import logging

logger = logging.getLogger(__name__)


class ConfigCog(commands.Cog):
    """Loads the configuration and stores the state of our bot"""

    # Lets us quickly read in our json config
    class BotConfig(object):
        def __init__(self, config_dict):
            self.__dict__ = config_dict

    def __init__(self, bot, index, model_file, model_key, config_file):
        self.bot = bot
        self.index = index
        self.model_key = model_key
        self.config_file = config_file

        # Read in the model file
        with open(model_file, mode='rb') as f:

            # Decryption
            encrypted_content = f.read()
            fer = Fernet(model_key.encode())
            decrypted_content = fer.decrypt(encrypted_content)

            # Loading with markovify
            model_raw_json = gzip.decompress(decrypted_content).decode()
            self.model = markovify.Text.from_json(model_raw_json)

        # Read in the config file
        with open(config_file) as f:
            self.configuration = ConfigCog.BotConfig(json.loads(f.read()))
            self.configuration.parameters = []
            for k in self.configuration.__dict__.keys():
                if not k.startswith('__'):
                    self.configuration.parameters.append(k)

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info('Logged in as')
        logger.info(self.bot.user.name)
        logger.info(self.bot.user.id)

    async def cog_check(self, ctx):
        """Only let the bot owner issue commands"""
        if ctx.message.author.id != self.config.owner_id:
            await ctx.send('Sorry, you don\'t have permission to do that.')
            return False

        if ctx.guild.id not in self.config.white_list_server_ids:
            await ctx.send('Sorry, I don\'t have permission to run on this server.')
            return False

        return True

    @commands.group()
    async def config(self, ctx):
        """Used to configure your bot"""
        pass

    @config.command()
    async def help(self, ctx):
        response = f'**Usage**:\n`{self.bot.command_prefix}config set <parameter name> <value>`\n'
        response += f'`{self.bot.command_prefix}config show`\n'
        await ctx.send(response)

    @config.command()
    async def show(self, ctx):
        """Dsiplays the current configuration"""
        response = ''
        for k in self.configuration.parameters:
            v = self.configuration.__getattribute__(k)
            response += f'`{k}: {v}`\n'

        await ctx.send(response)

    @config.command()
    async def set(self, ctx, *args):
        """Changes a configuration parameter"""
        if len(args) == 2:
            parameter = args[0]
            value = args[1]
        else:
            await ctx.send(f'**Usage**: `{self.bot.command_prefix}config set <parameter name> <value>`')
            return

        # Make sure this is something configurable
        if parameter not in self.configuration.parameters:
            await ctx.send(f'{parameter} is not a valid parameter')
            return

        # Check the data type
        try:
            old_value = self.configuration.__getattribute__(parameter)
            new_value = type(old_value)(value)
        except ValueError:
            type_name = type(self.configuration.__getattribute__(parameter)).__name__
            await ctx.send(f'Can\'t convert `{value}` into type: `{type_name}`')
            return

        # Make the change if all is well
        self.configuration.__setattr__(parameter, new_value)
        await ctx.send(f'`{parameter}` changed from {old_value} to {new_value}')
