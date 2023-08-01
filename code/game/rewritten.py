import json
import os
import subprocess
from threading import Timer
from typing import Tuple, Any

import requests

from code.common import Game, LoginState, Updater, UpdaterFile
from code.handler.native_handler import NativeHandler
from code.shell import ToonLinuxShell


@ToonLinuxShell.game('rewritten')
class ToontownRewritten(Game):
    def __init__(self, account):
        self.handler = NativeHandler('TTREngine')
        super().__init__('ToontownRewritten', account)
        self.updater = RewrittenUpdater(self.game_directory)

    def process_offline(self) -> Tuple[LoginState, Any]:
        api_path = self.config.api_path
        response = requests.post(api_path, data={'username': self.username, 'password': self.password}).json()
        return self.get_login_state(response)

    def get_login_state(self, response: dict) -> Tuple[LoginState, Any]:
        if response['success'] == 'partial':
            print('Two-partial authentication detected. Enter the authenticator token below.')
            auth = input()
            if not auth:
                print('Cancelling login attempt.')
                return LoginState.Rejected, False
            response = requests.post(self.config.api_path, data=dict(appToken=auth,
                                                                     authToken=response['responseToken']))

        if response['success'] == 'delayed':
            print('Login delayed. You\'re at position', response['position'], 'relogging in 15 seconds.')
            return LoginState.Queue, response['queueToken']

        if response['success'] == 'true':
            return LoginState.Online, response

        print('Login failed:', response['banner'])
        return LoginState.Rejected, False

    def process_queued(self, token, **kwargs) -> Tuple[LoginState, Any]:
        def retry_login():
            response = requests.post(self.config.api_path, data={'queueToken': token}).json()
            self.state, data = self.get_login_state(response)
            self.try_launch(data, **kwargs)

        timer = Timer(15, retry_login)
        timer.start()
        return LoginState.Queue, False

    def start_game(self, data, **kwargs):
        self.launch(dict(
            TTR_GAMESERVER=data['gameserver'],
            TTR_PLAYCOOKIE=data['cookie'],
        ), **kwargs)

    def update(self, force: bool = False):
        self.updater.run(force)


class RewrittenUpdater(Updater):
    updater_name = 'Toontown Rewritten Updater'
    manifest_files = ['https://cdn.toontownrewritten.com/content/patchmanifest.txt']
    update_url = 'https://download.toontownrewritten.com/patches/'

    def get_partial_manifest(self, path: str):
        manifest = requests.get(path)
        if manifest.status_code != 200:
            raise ConnectionError(manifest.status_code)

        manifest = json.loads(manifest.text)
        for filename, file in manifest.items():
            if 'linux2' not in file['only']:
                print(f'Skipping {filename} because it is not for Linux.')
                continue

            self.patch_manifest.append(UpdaterFile(
                file_hash=file['hash'], archive_hash=file['compHash'], filename=filename, path=filename,
                network_path=file['dl'], algo='bzip2'
            ))

    def run(self):
        super().run()
        print('Adding execution privileges to the game executable')
        subprocess.run(['chmod', '+x', f'{self.game_directory}{os.sep}TTREngine'])
