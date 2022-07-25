from traceback import print_exc

from code.shell import ToonLinuxShell
from code.game import corporate_clash, rewritten  # noqa: F401


def loop(shell):
    try:
        shell.cmdloop()
    except Exception:
        print_exc()
        loop(shell)


if __name__ == '__main__':
    shell = ToonLinuxShell()
    loop(shell)
