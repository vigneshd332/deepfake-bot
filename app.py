import os
import logging
from discord.ext import commands
import asyncio
import boto3
from cogs.config_cog import ConfigCog
from cogs.message_cog import MessageCog


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

MAX_BOTS = 10


if __name__ == "__main__":

    # Start with an event loop
    loop = asyncio.get_event_loop()
    idx = 0

    # S3 setup
    cloudcube_url = os.environ['CLOUDCUBE_URL']
    access_key = os.environ['CLOUDCUBE_ACCESS_KEY_ID']
    secret_key = os.environ['CLOUDCUBE_SECRET_ACCESS_KEY']

    bucket_name = cloudcube_url.split('.')[0].split('//')[1]
    cube_name = cloudcube_url.split('/')[-1]

    s3 = boto3.client('s3',
                      aws_access_key_id=access_key,
                      aws_secret_access_key=secret_key
                      )

    for i in range(MAX_BOTS):
        idx = i + 1
        try:
            # Read in the environment variables
            model_uid = os.environ[f'DEEPFAKE_MODEL_UID_{idx}']
            model_key = os.environ[f'DEEPFAKE_SECRET_KEY_{idx}']
            token = os.environ[f'DEEPFAKE_BOT_TOKEN_{idx}']

            # Download from S3
            config_file_name = f'{model_uid}-config.json'
            config_file_path = f'./tmp/{config_file_name}'

            model_file_name = f'{model_uid}-markov-model-encrypted.json.gz'
            model_file_path = f'./tmp/{model_file_name}'

            with open(model_file_path, 'wb') as f:
                s3.download_fileobj(bucket_name, f'{cube_name}/{model_file_name}', f)

            with open(config_file_path, 'wb') as f:
                s3.download_fileobj(bucket_name, f'{cube_name}/{config_file_name}', f)

            # Create a bot
            app = commands.Bot(command_prefix=f'df{idx}!')
            app.add_cog(ConfigCog(app, idx, model_file_path, model_key, config_file_path))
            app.add_cog(MessageCog(app))

            loop.create_task(app.start(token))

        except KeyError:
            # No more environment variables found, exit the loop
            break

    logger.info(f'Found {idx} bot configs...')

    try:
        loop.run_forever()
    finally:
        loop.stop()
