import os
import subprocess
from glob import glob

from code.common import Handler


class WindowsHandler(Handler):
    def find(self, prefix):
        subpaths = ['Program Files', 'Program Files (x86)', 'users/*/AppData']
        for subpath in subpaths:
            found = glob(f'{prefix}/drive_c/{subpath}/**/{self.filename}', recursive=True)
            if found:
                if len(found) > 1:
                    raise ValueError(f'Multiple installations found: {found}')
                return found[0]

        raise ValueError('File not found')

    def launch(self, path, env=None, cwd='', pipe_stderr=True, pipe_stdout=True, **kwargs):
        env = env or {}

        args = dict(env=dict(os.environ, **env), cwd=cwd)
        if pipe_stderr:
            args['stderr'] = subprocess.PIPE
        if pipe_stdout:
            args['stdout'] = subprocess.PIPE

        self.app = subprocess.Popen(['wine', path], **args)
