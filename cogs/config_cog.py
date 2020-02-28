from discord.ext import commands
from cryptography.fernet import Fernet
import gzip
import markovify
import logging

logger = logging.getLogger(__name__)


class ConfigCog(commands.Cog):
    """Loads the configuration and stores the state of your bot"""

    class BotConfig(object):
        """Lets us quickly read in our json config"""
        def __init__(self, config_dict):
            self.__dict__ = config_dict

    def __init__(self, bot, idx, model_uid, model_key, s3):
        self.bot = bot
        self.idx = idx
        self.model_uid = model_uid
        self.model_key = model_key
        self.s3 = s3

        # Download the model file
        s3.get_file(f'{model_uid}-markov-model-encrypted.json.gz')

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
        self.config_parameters = []
        for k in self.configuration.__dict__.keys():
            if not k.startswith('__'):
                self.config_parameters.append(k)
        
        # Set the command prefix
        self.bot.command_prefix = self.configuration.bot_prefix

    def update_s3(self):
        """Saves the current bot configuration to S3. Returns false if there was an issue."""
        return self.s3.update_json(f'{self.model_uid}-config.json', self.configuration.__dict__)

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

    @config.group()
    async def whitelist(self, ctx):
        """Used to change the servers on which the bot has permission to reply"""
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
        for k in self.config_parameters:
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

        if ctx.message.author.id != self.configuration.owner_id:
            await ctx.send('Sorry. You don\'t have permission to do that.')
            return

        # Make sure this is something configurable
        if parameter not in self.config_parameters:
            await ctx.send(f'{parameter} is not a valid parameter')
            return
        
        # Use another command. Otherwise, reading a list will be problematic.
        if parameter == 'white_list_server_ids':
            await ctx.send('That can\'t be changed with `config set` '
                           'Use `{self.bot.command_prefix}config whitelist add/remove` instead.')
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

        # Also update the prefix if applicable
        if parameter == 'bot_prefix':
            self.bot.command_prefix = new_value

        # Update the config file in S3
        if self.update_s3():
            await ctx.send(f'`{parameter}` changed from {old_value} to {new_value}')
        else:
            await ctx.send('There was a problem updating config...')

    @whitelist.command()
    async def add(self, ctx, *args):
        """Adds a server id to the whitelist"""
        if len(args) == 1:
            value = args[0]
        else:
            await ctx.send(f'**Usage**: `{self.bot.command_prefix}config whitelist add <value>`')
            return

        if ctx.message.author.id != self.configuration.owner_id:
            await ctx.send('Sorry. You don\'t have permission to do that.')
            return

        if value not in self.configuration.white_list_server_ids:
            self.configuration.white_list_server_ids.append(value)
            if self.update_s3():
                await ctx.send(f'Added {value} to server white list')
            else:
                await ctx.send('There was a problem updating config...')
        else:
            await ctx.send(f'{value} was already white listed')

    @whitelist.command()
    async def remove(self, ctx, *args):
        """Removes a server id from the whitelist"""
        if len(args) == 1:
            value = args[0]
        else:
            await ctx.send(f'**Usage**: `{self.bot.command_prefix}config whitelist remove <value>`')
            return

        if ctx.message.author.id != self.configuration.owner_id:
            await ctx.send('Sorry. You don\'t have permission to do that.')
            return

        if value in self.configuration.white_list_server_ids:
            self.configuration.white_list_server_ids.remove(value)
            if self.update_s3():
                await ctx.send(f'Removed {value} from server white list')
            else:
                await ctx.send('There was a problem updating config...')
        else:
            await ctx.send(f'{value} was already not in white list')
