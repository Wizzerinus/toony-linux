import os
import subprocess

from code.common import Handler


class NativeHandler(Handler):
    def find(self, prefix: str) -> str:
        return os.path.join(prefix, self.filename)

    def launch(self, path, env=None, cwd='', pipe_stderr=True, pipe_stdout=True, **kwargs):
        env = env or {}

        args = dict(env=dict(os.environ, **env), cwd=cwd)
        if pipe_stderr:
            args['stderr'] = subprocess.PIPE
        if pipe_stdout:
            args['stdout'] = subprocess.PIPE

        self.app = subprocess.Popen([path], **args)
