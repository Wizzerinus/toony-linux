import abc
import bz2
import gzip
import hashlib
import os
from enum import Enum
from typing import Tuple, Any, List, Optional

import requests
import yaml


class LoginState(Enum):
    Offline = 'offline'
    Queue = 'queued'
    Online = 'online'
    Rejected = 'rejected'
    LoginToken = 'lt'


class Subconfig:
    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        val = self._data[key]
        if isinstance(val, dict):
            return Subconfig(self._data[key])
        return val

    def __getattr__(self, item):
        return self[item]


class Config(Subconfig):
    _singleton = None

    def __new__(cls, *args, **kwargs):
        if not cls._singleton:
            cls._singleton = super().__new__(cls, *args, **kwargs)
        return cls._singleton

    def __init__(self):
        with open('config.yaml', 'r') as f:
            super().__init__(yaml.safe_load(f))


class Handler(abc.ABC):
    app = None

    def __init__(self, filename: str):
        self.filename = filename

    @abc.abstractmethod
    def find(self, prefix: str) -> str:
        pass

    @abc.abstractmethod
    def launch(self, file_path: str, env: dict = None, cwd: str = None, **kwargs) -> None:
        pass


class Game(abc.ABC):
    state = LoginState.Offline
    handler = None
    path = None
    username = password = None

    def __init__(self, game_name, account):
        if not self.handler:
            raise ValueError('Handler not set')

        self.config = Config().Games[game_name]
        self.account = account
        self.account_needs_change = False
        prefix = os.path.expanduser(self.config.prefix)
        self.path = self.handler.find(prefix)
        self.game_directory = os.path.dirname(self.path)

    def login(self, login: str, password: str, **kwargs) -> bool:
        self.username = login
        self.password = password
        self.state = LoginState.Offline
        return self.process_step(**kwargs)

    def process_step(self, **kwargs):
        data = None
        for i in range(10):
            func = getattr(self, f'process_{self.state.value}')
            self.state, data = func() if self.state == LoginState.Offline else func(data, **kwargs)
            tl = self.try_launch(data, **kwargs)
            if tl is not None:
                return tl
        return False

    def try_launch(self, data, **kwargs) -> Optional[bool]:
        if self.state == LoginState.Online:
            self.start_game(data, **kwargs)
            return True
        elif not data:
            return False

    @abc.abstractmethod
    def process_offline(self) -> Tuple[LoginState, Any]:
        pass

    # Queue does not always exist, so those methods are not abstract.
    def process_queued(self, data, **kwargs) -> Tuple[LoginState, Any]:
        return LoginState.Offline, False

    @abc.abstractmethod
    def start_game(self, data, **kwargs):
        pass

    def is_playable(self) -> bool:
        return self.state == LoginState.Online

    def is_active(self) -> bool:
        return self.is_playable() and self.handler.app and self.handler.app.poll() is None

    def launch(self, env: dict = None, **kwargs):
        self.handler.launch(self.path, env, cwd=self.game_directory, **kwargs)

    def update(self):
        pass

    def stop(self):
        self.handler.app.kill()
        self.handler.app = None


class UpdaterFile:
    def __init__(self, path: str, filename: str, file_hash: str, archive_hash: str,
                 network_path: str, hash_url: bool = False, algo: str = 'gzip'):
        self.path = path
        self.filename = filename
        self.file_hash = file_hash
        self.archive_hash = archive_hash
        self.network_path = network_path
        self.hash_url = hash_url
        self.algo = algo


class Updater(abc.ABC):
    manifest_files = []
    update_url = ''
    updater_name = ''

    patch_manifest: List[UpdaterFile]

    def __init__(self, game_dir: str):
        self.game_directory = game_dir + os.path.sep
        self.patch_manifest = []
        self.files_needed = []

    @abc.abstractmethod
    def get_partial_manifest(self, path: str):
        pass

    def get_patch_manifest(self):
        for manifest_file in self.manifest_files:
            self.get_partial_manifest(manifest_file)

    def check_local_files(self, debug: bool = False):
        for file in self.patch_manifest:
            full_path = self.game_directory + file.path

            if os.path.exists(full_path):
                file_hash = self.sha1_hash_file(full_path)

                if file_hash == file.file_hash:
                    continue

            if debug:
                print(f'File "{file.filename}" at "{file.path}" needs updating. Queuing.')
            self.files_needed.append(file)

    def is_updated(self) -> bool:
        self.get_patch_manifest()
        self.check_local_files(True)

        value = not self.files_needed

        self.patch_manifest.clear()
        self.files_needed.clear()

        return value

    @staticmethod
    def sha1_hash_file(file_path) -> str:
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha1()
                while chunk := f.read(8192):
                    file_hash.update(chunk)

            return file_hash.hexdigest()
        else:
            raise FileNotFoundError

    @staticmethod
    def sha1_hash_path(s) -> str:
        hash_obj = hashlib.sha1(bytes(s, encoding='UTF-8'))
        return hash_obj.hexdigest()

    def verify(self, path: str, file_hash: str) -> bool:
        return self.sha1_hash_file(path) == file_hash

    @staticmethod
    def decompress_file(archive: str, local_file: str, algo: str):
        with open(archive, 'rb') as b:
            with open(local_file, 'wb') as lf:
                if algo == 'bzip2':
                    lf.write(bz2.decompress(b.read()))
                elif algo == 'gzip':
                    lf.write(gzip.decompress(b.read()))

    def extract(self, download_path: str, extraction_path: str, algo: str) -> int:
        try:
            self.decompress_file(download_path, extraction_path, algo)
            return 0
        except OSError:
            os.remove(extraction_path)
            return -1
        finally:
            os.remove(download_path)

    @staticmethod
    def download(url: str, filepath: str) -> int:
        try:
            response = requests.get(url)
            stream = response.content

            with open(filepath, 'wb') as f:
                f.write(stream)

            return 0
        except (OSError, ConnectionError) as e:
            print(e)
            return -1

    def acquire_file(self, file: UpdaterFile):
        file_target = self.sha1_hash_path(file.network_path) if file.hash_url else file.network_path

        url = self.update_url + file_target
        download_path = self.game_directory + file_target
        extracted_path = download_path + '~'

        state = self.download(url, download_path)

        if state != 0:
            os.remove(download_path)
            raise OSError

        if not self.verify(download_path, file.archive_hash):
            raise OSError(f'File hash mismatch: expected {file.archive_hash}, '
                          f'got {self.sha1_hash_file(download_path)}')

        if self.extract(download_path, extracted_path, file.algo) != 0:
            raise OSError

        if self.verify(extracted_path, file.file_hash):
            file.filename = file_target + '~'
            return
        else:
            raise OSError

    def download_game_files(self):
        for file in self.files_needed:
            self.acquire_file(file)
            print(f'Downloaded "{file.path}"')

    def replace_game_files(self):
        for file in self.files_needed:
            local_path = self.game_directory + file.path
            local_dir = os.path.dirname(local_path)

            if os.path.isdir(local_dir):
                if os.path.isfile(local_path):
                    os.remove(local_path)
            else:
                os.mkdir(local_dir)

            os.replace(self.game_directory + file.filename, self.game_directory + file.path)
        self.patch_manifest.clear()
        self.files_needed.clear()

    def run(self):
        print('')
        print(self.updater_name)
        print('Fetching new patch manifest')
        self.get_patch_manifest()
        print('Checking local files for inconsistencies')
        self.check_local_files(True)
        print('Downloading updated game files')
        self.download_game_files()
        print('Patching local game files')
        self.replace_game_files()

