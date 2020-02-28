import os
import logging
import json
from discord.ext import commands
import asyncio
import boto3
from cogs.config_cog import ConfigCog
from cogs.message_cog import MessageCog
from cogs.silly_cog import SillyCog


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

MAX_BOTS = 10


class S3:
    """Handles writing and reading files to and from S3"""
    def __init__(self):
        cloudcube_url = os.environ['CLOUDCUBE_URL']
        access_key = os.environ['CLOUDCUBE_ACCESS_KEY_ID']
        secret_key = os.environ['CLOUDCUBE_SECRET_ACCESS_KEY']

        self.bucket_name = cloudcube_url.split('.')[0].split('//')[1]
        self.cube_name = cloudcube_url.split('/')[-1]

        self.resource = boto3.resource('s3',
                                       aws_access_key_id=access_key,
                                       aws_secret_access_key=secret_key
                                       )
    
    def get_file(self, file_name):
        """Downloads a file to the ./tmp folder"""
        local_file_name = f'./tmp/{file_name}'
        with open(local_file_name, 'wb') as f:
            f.write(self.resource.Object(self.bucket_name, f'{self.cube_name}/{file_name}').get()['Body'].read())

    def get_json(self, file_name):
        """Reads the contents of a json file in S3 and returns it as an object"""
        raw_content = self.resource.Object(self.bucket_name, f'{self.cube_name}/{file_name}').get()['Body'].read()
        try:
            return json.loads(raw_content)
        except JSONDecodeError as e:
            logger.error(e)
            return False

    def update_json(self, file_name, obj):
        """Updates a json file in S3"""
        payload = json.dumps(obj)
        try:
            self.resource.Object(self.bucket_name, f'{self.cube_name}/{file_name}').put(Body=payload)
            return True
        except Exception as e:
            logger.error(e)
            return False


if __name__ == "__main__":

    # Start with an event loop
    loop = asyncio.get_event_loop()
    idx = 0

    # S3 handler
    my_s3 = S3()

    for i in range(MAX_BOTS):
        idx = i + 1
        try:
            # Read in the environment variables
            model_uid = os.environ[f'DEEPFAKE_MODEL_UID_{idx}']
            model_key = os.environ[f'DEEPFAKE_SECRET_KEY_{idx}']
            token = os.environ[f'DEEPFAKE_BOT_TOKEN_{idx}']

            # Create a bot
            app = commands.Bot(command_prefix=f'df{idx}?')
            app.add_cog(ConfigCog(app, idx, model_uid, model_key, my_s3))
            app.add_cog(MessageCog(app))
            app.add_cog(SillyCog(app))

            loop.create_task(app.start(token))

        except KeyError as e:
            # No more environment variables found, exit the loop
            break

    logger.info(f'Found {idx - 1} bot configs...')

    try:
        loop.run_forever()
    finally:
        loop.stop()
