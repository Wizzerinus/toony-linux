from cmd import Cmd
from getpass import getpass

import yaml

from code.common import Config


class ToonLinuxShell(Cmd):
    accounts = None
    games = {}
    launched_games = {}
    prompt = "ToonLinux> "

    value_replacements = {
        'true': True,
        'True': True,
        'false': False,
        'False': False,
    }

    @classmethod
    def game(cls, name):
        def decorator(func):
            cls.games[name] = func
            return func

        return decorator

    def __init__(self):
        super().__init__()
        self.load_toons()

        self.do_lc = self.do_launch
        self.do_dc = self.do_disconnect

    def emptyline(self):
        pass

    def load_toons(self):
        with open('accounts.yaml', 'r') as f:
            accounts = yaml.safe_load(f)

            self.accounts = {}
            for name, account in accounts.items():
                self.accounts[name] = account
                if account['game'] not in self.games:
                    raise ValueError(f'Unknown game {account["game"]}')
                if 'aliases' in account:
                    for alias in account['aliases']:
                        self.accounts[alias] = account

    def save_accounts(self):
        accounts = dict(self.accounts)
        for login, account in self.accounts.items():
            if login in account.get('aliases', []):
                del accounts[login]

        with open('accounts.yaml', 'w') as f:
            yaml.dump(accounts, f)

    def extract_kwargs(self, arg):
        args, kwargs = [], {}
        for arg in arg.split():
            if '=' in arg:
                key, value = arg.split('=')
                if value in self.value_replacements:
                    value = self.value_replacements[value]
                kwargs[key] = value
            else:
                args.append(arg)
        return args, kwargs

    def resolve_account(self, arg):
        if arg in self.accounts:
            return self.accounts[arg]['login']
        return None

    def filter_accounts(self):
        self.launched_games = {login: game for login, game in self.launched_games.items() if game.is_active()}

    def do_accounts(self, arg):
        print('Reloading all accounts')
        self.load_toons()

    def do_update(self, arg):
        if not arg:
            print('Updating all games')
            for game in self.games.values():
                game(None).update()
        elif arg in self.games:
            print(f'Updating single game: {arg}')
            self.games[arg](None).update()
        else:
            print(f'Unknown game {arg}')

    def do_notoken(self, arg):
        if arg not in self.accounts:
            print(f'Account {arg} not found')
            return

        account = self.accounts[arg]
        if account['game'] != 'clash':
            print('Revoking non-clash tokens is not yet supported.')
            return

        game = self.games[account['game']]()
        result = game.revoke_token(account.get('token'))
        if result:
            del account['token']
            self.save_accounts()

    def do_launch(self, arg):
        self.filter_accounts()
        toons, kwargs = self.extract_kwargs(arg)
        if kwargs:
            print('Running with keyword arguments: ', kwargs)
        for toon in toons:
            if toon not in self.accounts:
                print(f'Account {toon} not found')
                continue

            account = self.accounts[toon]
            if (account['game'], account['login']) in self.launched_games and not kwargs.get('force'):
                print(f'Account {account["login"]} on game {account["game"]} already launched '
                      '(use force=true to override)')
                continue

            game = self.games[account['game']](account)
            toon_name = account['display_name']

            password_reset = False
            if 'password' not in account and Config().GameData[account['game']].uses_password:
                password_reset = True
                account['password'] = getpass(f'Enter password for {toon_name}: ')

            login_successful = game.login(**account, **kwargs)
            if not login_successful:
                if password_reset:
                    del account['password']
                continue
            if password_reset:
                print('Saving password for this account for the rest of this session')
            elif game.account_needs_change:
                print('Saving the account...')
                self.save_accounts()

            print(f'Successfully logged in as {toon_name}')
            self.launched_games[account['game'], account['login']] = game

    def do_disconnect(self, arg):
        if arg not in self.accounts:
            print(f'Account {arg} not found')
            return

        account = self.accounts[arg]
        game = self.launched_games.get((account['game'], account['login']))
        if not game or not game.is_active():
            print(f'Account {arg} not launched')
            return

        game.stop()

    # TODO: figure out why this does not work
    """
    def do_log(self, arg):
        arg = self.resolve_account(arg)
        if arg not in self.launched_games:
            print(f'Account {arg} not launched')
            return

        game = self.launched_games[arg]
        print(game.handler.app.stdout.read().decode('utf-8'))

    def do_logs(self, arg):
        for account, game in self.launched_games.items():
            print(f'{account}:', game.handler.app.stdout.read().decode('utf-8'))
    """
