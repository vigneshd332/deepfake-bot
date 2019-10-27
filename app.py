import os
import logging
from discord.ext import commands
import asyncio
from cogs.config_cog import ConfigCog
from cogs.message_cog import MessageCog


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":

    # Start with an event loop
    loop = asyncio.get_event_loop()
    idx = 0

    # Check each config subfolder
    sub_folders = [i[0] for i in os.walk('./config')]

    for config_path in sub_folders:
        try:
            files = os.listdir(config_path)
            config_file_found = False
            model_file_found = False
            for f in files:
                if f.endswith('-config.json'):
                    config_file_found = True
                    config_file = os.path.join(config_path, f)
                if f.endswith('-markov-model-encrypted.json.gz'):
                    model_file_found = True
                    model_file = os.path.join(config_path, f)

            if not (config_file_found and model_file_found):
                continue

            # Create as many bots as there are config folders...
            bot_idx = config_path.split(os.sep)[-1]
            model_key = os.environ[f'DEEPFAKE_SECRET_KEY_{bot_idx}']
            token = os.environ[f'DEEPFAKE_BOT_TOKEN_{bot_idx}']

            app = commands.Bot(command_prefix=f'df{bot_idx}!')
            app.add_cog(ConfigCog(app, idx, model_file, model_key, config_file))
            app.add_cog(MessageCog(app))

            loop.create_task(app.start(token))
            idx += 1

        except FileNotFoundError:
            logger.error(f'Problem loading files from {config_path}')

    logger.info(f'Found {idx} bot configs...')

    try:
        loop.run_forever()
    finally:
        loop.stop()
