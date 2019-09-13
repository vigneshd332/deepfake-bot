import os
import logging
from discord.ext import commands
import asyncio

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DeepFakeBot(commands.Cog):
    def __init__(self, bot, index):
        self.bot = bot
        self.index = index

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info('Logged in as')
        logger.info(self.bot.user.name)
        logger.info(self.bot.user.id)
        logger.info('------')

    @commands.command()
    async def repeat(self, ctx, msg):
        """Function for testing. Bot will repeat the message in the command."""
        logger.info(msg)
        channel = ctx.message.channel
        await channel.send(f'{self.index}:  {msg}')


if __name__ == "__main__":

    # Start with an event loop
    loop = asyncio.get_event_loop()

    for idx in range(1, 10**10):
        try:
            with open(f'./config/{idx}/.gitkeep'):
                # TODO: read in model artifacts here
                pass

            # Create as many bots as there are config folders...
            app = commands.Bot(command_prefix=f'df{idx}!')
            app.add_cog(DeepFakeBot(app, idx))

            token = os.environ[f'DEEPFAKE_BOT_TOKEN_{idx}']
            loop.create_task(app.start(token))

        except FileNotFoundError:
            break

    try:
        loop.run_forever()
    finally:
        loop.stop()
