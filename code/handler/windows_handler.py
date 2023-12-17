import os
import subprocess
from glob import glob

from code.common import Config, Handler


class WindowsHandler(Handler):
    def find(self, prefix):
        if self.force_path:
            # Note that in this case we do not have to check the file's existance
            # because the updater will download it
            os.makedirs(f'{prefix}/drive_c/{self.force_path}', exist_ok=True)
            return f'{prefix}/drive_c/{self.force_path}/{self.filename}'

        subpaths = ['Program Files', 'Program Files (x86)', 'users/*/AppData']
        for subpath in subpaths:
            found = glob(f'{prefix}/drive_c/{subpath}/**/{self.filename}', recursive=True)
            if found:
                if len(found) > 1:
                    raise ValueError(f'Multiple installations found: {found}')
                return found[0]

        raise ValueError('File not found')

    def launch(self, path, env=None, cwd=None, pipe_stderr=True, pipe_stdout=True, **kwargs):
        env = env or {}

        args = dict(env=dict(os.environ, **env))
        if cwd is not None:
            args['cwd'] = cwd
        if pipe_stderr:
            args['stderr'] = subprocess.PIPE
        if pipe_stdout:
            args['stdout'] = subprocess.PIPE

        self.app = subprocess.Popen([Config().Handlers.Windows.wine_executable, path], **args)
