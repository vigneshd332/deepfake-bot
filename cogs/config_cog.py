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

    def __init__(self, bot, idx, model_uid, model_key, s3):
        self.bot = bot
        self.idx = idx
        self.model_uid = model_uid
        self.model_key = model_key
        self.s3 = s3

        # Read in the model file
        with open(f'./tmp/{model_uid}-markov-model-encrypted.json.gz', mode='rb') as f:

            # Decryption
            encrypted_content = f.read()
            fer = Fernet(model_key.encode())
            decrypted_content = fer.decrypt(encrypted_content)

            # Loading with markovify
            model_raw_json = gzip.decompress(decrypted_content).decode()
            self.model = markovify.Text.from_json(model_raw_json)

        # Set the config parameters
        config_json = s3.get_json(f'{self.model_uid}-config.json')
        self.configuration = ConfigCog.BotConfig(config_json)
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
        if ctx.guild.id not in self.configuration.white_list_server_ids:
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

        if ctx.message.author != self.configuration.owner_id:
            await ctx.send('Sorry. You don\'t have permission to do that.')

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

        # Update the config file in S3
        s3_updated = self.s3.update_json(f'{self.model_uid}-config.json', self.configuration.__dict__)
        if s3_updated:
            await ctx.send(f'`{parameter}` changed from {old_value} to {new_value}')
        else:
            await ctx.send('There was a problem updating config...')
