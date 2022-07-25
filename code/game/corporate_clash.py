import json

import requests

from code.common import Game, LoginState, Updater, UpdaterFile
from code.handler.windows_handler import WindowsHandler
from code.shell import ToonLinuxShell


@ToonLinuxShell.game('clash')
class CorporateClash(Game):
    force_account = ''

    def __init__(self):
        self.handler = WindowsHandler('CorporateClash.exe')
        super().__init__('CorporateClash')
        self.updater = ClashPatcher(self.game_directory)

    def update(self):
        self.updater.run()

    def login(self, login: str, password: str, toon_position: int = 6, **kwargs) -> bool:
        if toon_position != 6:
            self.force_account = toon_position
        return super().login(login, password, **kwargs)

    def process_offline(self):
        api_path = self.config.api_path + self.username
        response = requests.post(api_path, data={'password': self.password}).json()
        if response['status']:
            return LoginState.Online, response['token']

        print('Login failed:', response['friendlyreason'])
        return LoginState.Rejected, False

    def start_game(self, data, clash_district='', **kwargs):
        self.launch(dict(
            TT_GAMESERVER=self.config.gameserver,
            TT_PLAYCOOKIE=data,
            FORCE_TOON_SLOT=self.force_account,
            FORCE_DISTRICT=clash_district,
        ), **kwargs)


class ClashPatcher(Updater):
    updater_name = 'Corporate Clash Updater'
    manifest_files = [
        'https://corporateclash.net/api/v1/launcher/manifest/v2/windows_production.js',
        'https://corporateclash.net/api/v1/launcher/manifest/v2/resources_production.js',
    ]

    update_url = 'https://aws1.corporateclash.net/productionv2/'

    def get_partial_manifest(self, path: str):
        manifest = requests.get(path)
        if manifest.status_code != 200:
            raise ConnectionError(manifest.status_code)

        manifest = json.loads(manifest.text)
        for file in manifest['files']:
            self.patch_manifest.append(UpdaterFile(
                filename=file['fileName'], path=file['filePath'], network_path=file['filePath'],
                file_hash=file['sha1'], archive_hash=file['compressed_sha1'], hash_url=True))
