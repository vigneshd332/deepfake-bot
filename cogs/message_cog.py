import logging
from discord.ext import commands
import asyncio
import random
import time

from cogs.nlp_functions import *
from datetime import datetime

logger = logging.getLogger(__name__)


class MessageCog(commands.Cog):
    """Commands and functions that relate to generating and sending messages"""
    def __init__(self, bot):
        self.bot = bot
        self.config = self.bot.get_cog('ConfigCog').configuration
        self.model = self.bot.get_cog('ConfigCog').model
        self.can_reply = True
        self.last_message_time = None
        self.next_message_time = None

        self.TIME_TOLERANCE = 1

    async def cog_check(self, ctx):
        """Only let the bot owner issue commands"""
        if ctx.message.author.id != self.config.owner_id:
            await ctx.send('Sorry, you don\'t have permission to do that.')
            return False

        if ctx.guild.id not in self.config.white_list_server_ids:
            await ctx.send('Sorry, I don\'t have permission to run on this server.')
            return False

        return True

    async def start_conversation(self, ctx):
        """Start a new conversation if enough time has passed since when the bot last spoke."""
        if time.time() >= self.next_message_time - self.TIME_TOLERANCE:
            txt = self.model.make_short_sentence(self.config.max_sentence_length, tries=100)
            txt = punctuate(txt)
            await self.type_response(ctx, txt)
        else:
            logger.info(f'{self.bot.user.name}: conversation started {self.next_message_time - time.time()}s too early')

    async def sleep_and_start_conversation(self, ctx):
        """Runs as a background task"""
        await asyncio.sleep(self.next_message_time - self.last_message_time)
        await self.start_conversation(ctx)

    def schedule_new_conversation(self, ctx):
        """Schedule a new conversation. Calling this again will defer any other scheduled conversations."""
        self.last_message_time = time.time()
        self.next_message_time = self.last_message_time + \
                                 self.config.new_conversation_min_wait + \
                                 random.random() * \
                                 (self.config.new_conversation_max_wait - self.config.new_conversation_min_wait)

        t = datetime.utcfromtimestamp(self.next_message_time).strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f'{self.bot.user.name}: New conversation scheduled for {t}')

    async def type_response(self, ctx, txt):
        """Take some time to type the response"""
        typing_speed = normal_with_min(
            self.config.avg_typing_speed,
            self.config.std_dev_typing_speed,
            self.config.min_typing_speed
        )
        typing_time = (len(txt) / 5) / (typing_speed / 60)
        logger.info(f'{self.bot.user.name}: typing for {typing_time}s at {typing_speed} wpm')

        async with ctx.channel.typing():
            # Ignore other messages while typing
            self.can_reply = False
            await asyncio.sleep(typing_time)
            await ctx.send(txt)

            # Setup the next random conversation
            self.can_reply = True
            self.schedule_new_conversation(ctx)

        self.bot.loop.create_task(
            self.sleep_and_start_conversation(ctx)
        )

    @commands.command()
    async def repeat(self, ctx, msg):
        """Function for testing. Bot will repeat the message in the command."""
        logger.info(msg)
        channel = ctx.message.channel
        await channel.send(msg)

    @commands.command()
    async def generate(self, ctx):
        """Generates a random sentence from your model."""
        txt = self.model.make_short_sentence(self.config.max_sentence_length, tries=100)
        txt = punctuate(txt)
        if txt is not None:
            await self.type_response(ctx, txt)
        else:
            await ctx.send('Response generation failed :(')

    @commands.Cog.listener()
    async def on_message(self, msg):
        ctx = await self.bot.get_context(msg)

        # Reply to messages randomly
        if msg.author != self.bot.user and ctx.guild.id in self.config.white_list_server_ids:
            if self.can_reply and random.random() < self.config.reply_probability:

                # Delay the response for more lifelike behavior
                delay_time = normal_with_min(
                    self.config.avg_delay,
                    self.config.std_dev_delay,
                    self.config.min_delay
                )
                self.can_reply = False
                await asyncio.sleep(delay_time)

                # Generate some possible responses
                res = [
                        punctuate(self.model.make_short_sentence(self.config.max_sentence_length, tries=100))
                        for i in range(self.config.max_markov_chains)
                      ]

                # Select the best response
                sel = self.config.selection_algorithm
                if sel == 'cosine_similarity':
                    txt, cos = select_by_cosine_similarity(msg.clean_content, res)
                    logger.info(
                        f'{self.bot.user.name}: replying to {ctx.message.author.name} with cosine similarity: {cos}'
                    )
                elif sel == 'match_words':
                    txt, n_matches = select_by_matching_words(msg.clean_content, res)
                    logger.info(
                        f'{self.bot.user.name}: replying to {ctx.message.author.name} with {n_matches} matching words'
                    )

                else:
                    txt = f'Error: `{sel}` is not a valid selection algorithm'

                # Get rid of mentions
                if self.config.quiet_mode:
                    txt = txt.replace('@', '')

                await self.type_response(ctx, txt)
