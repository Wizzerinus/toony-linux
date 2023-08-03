import datetime
import json
from getpass import getpass
import time

import requests
from requests import JSONDecodeError

from code.common import Game, LoginState, Updater, UpdaterFile
from code.handler.windows_handler import WindowsHandler
from code.shell import ToonLinuxShell


CLOUDFLARE_CAPTCHA = '<!doctype html><html lang="en-us"><head><title>just a moment...</title>'

@ToonLinuxShell.game('clash')
class CorporateClash(Game):
    force_account = ''

    def __init__(self, account):
        self.handler = WindowsHandler('CorporateClash.exe')
        self.token = None
        super().__init__('CorporateClash', account)
        self.updater = ClashPatcher(self.game_directory)

    @staticmethod
    def get_headers(**kwargs):
        return dict(kwargs, **{'user-agent': 'Toony Linux 0.2.1 by Wizzerinus'})

    def update(self, force: bool = False):
        self.updater.run(force)

    def login(self, login: str, token: str = '', toon_position: int = 6, **kwargs) -> bool:
        if toon_position != 6:
            self.force_account = toon_position
        self.token = token
        if 'password' not in kwargs:
            kwargs['password'] = ''
        return super().login(login, **kwargs)

    def process_lt(self, ignored, **kwargs):
        if 'password' in self.account:
            password = self.account['password']
            print('Using password from the old login configuration.')
        else:
            password = getpass(f'You do not have a login token registered for username {self.username}. '
                               f'Enter your password here: ')
        if not password:
            return LoginState.Rejected, False

        current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        request = dict(username=self.username, password=password, friendly=f'Toony Linux {current_date}')
        response = requests.post(
            self.config.token_api, data=request, headers=self.get_headers()).json()

        if not response['status']:
            if response.get('toonstep'):
                print('Two-factor authentication detected. Authorize your token (id: %d) and try again.'
                      % response['id'])
            else:
                print('Login failed: %s (%d)' % (response['message'], response['reason']))
            return LoginState.Rejected, False

        print('Successfully obtained the token!')
        self.account['token'] = self.token = response['token']
        self.account.pop('password', None)
        self.account_needs_change = True
        return LoginState.Offline, True

    def process_offline(self):
        if not self.token:
            return LoginState.LoginToken, True
        response = requests.post(
            self.config.login_api, headers=self.get_headers(Authorization=f'Bearer {self.token}'))
        try:
            response = response.json()
        except JSONDecodeError:
            if response.status_code == 429:
                print('We are being rate limited, retrying in 15 seconds...')
                time.sleep(15)
                return LoginState.Offline, True

            # TODO: figure out what's the best way to do this
            if response.text.lower().startswith(CLOUDFLARE_CAPTCHA):
                print('Cloudflare requires a captcha. Retry again later.')
                return LoginState.Offline, False

            print(response.text)
            print('ISP consumed the JSON output, retrying in 5 seconds...')
            time.sleep(5)
            return LoginState.Offline, True

        if response.get('bad_token'):
            print('Your token has been revoked. Removing it from the configuration.')
            del self.account['token']
            self.account_needs_change = True
            return LoginState.Rejected, False

        if response['status']:
            return LoginState.Online, response['token']

        if response.get('toonstep'):
            print('Two-factor authentication detected. Authorize your token and try again.')
            return LoginState.Rejected, False

        if 'A lot of Toons' in response['message']:
            print("We're rate limited, retrying...")
            return LoginState.Offline, True
        print('Login failed:', response['message'])
        return LoginState.Rejected, False

    def start_game(self, data, **kwargs):
        self.launch(dict(
            TT_GAMESERVER=self.config.gameserver,
            TT_PLAYCOOKIE=data,
            FORCE_TOON_SLOT=self.force_account,
        ), **kwargs)

    def revoke_token(self, token):
        if not token:
            print('This account has no token!')
            return

        response = requests.post(
            self.config.login_api, headers=self.get_headers(Authorization=f'Bearer {token}')).json()
        if response.get('bad_token'):
            print('This token does not exist.')
            return False

        if not response['success']:
            print('Unknown error revoking the token!')
            return False

        return True


class ClashPatcher(Updater):
    updater_name = 'Corporate Clash Updater'
    manifest_files = [
        'https://corporateclash.net/api/v1/launcher/manifest/v3/production/windows',
        'https://corporateclash.net/api/v1/launcher/manifest/v3/production/resources',
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
