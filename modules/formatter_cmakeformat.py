import logging
from ..core import common

log = logging.getLogger(__name__)
INTERPRETERS = ['python3', 'python']
EXECUTABLES = ['cmake-format']
DOTFILES = ['.cmake-format.yaml', '.cmake-format.json', '.cmake-format.py']
MODULE_CONFIG = {
    'source': 'https://github.com/cheshirekow/cmake_format',
    'name': 'CMake-format',
    'uid': 'cmakeformat',
    'type': 'beautifier',
    'syntaxes': ['cmake'],
    'exclude_syntaxes': None,
    'executable_path': '/path/to/bin/cmake-format',
    'args': None,
    'config_path': {
        'default': 'cmakeformat_rc.py'
    },
    'comment': 'requires "environ": {"PYTHONPATH": ["/lib/python3.7/site-packages"]}. requires python on PATH if omit interpreter_path'
}


class CmakeformatFormatter(common.Module):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_cmd(self):
        cmd = self.get_combo_cmd(runtime_type='python')
        if not cmd:
            return None

        path = self.get_config_path()
        if path:
            cmd.extend(['--config-files', path, '--'])

        cmd.extend(['-'])

        log.debug('Command: %s', cmd)
        cmd = self.fix_cmd(cmd)

        return cmd

    def format(self):
        cmd = self.get_cmd()
        if not self.is_valid_cmd(cmd):
            return None

        try:
            exitcode, stdout, stderr = self.exec_cmd(cmd)

            if exitcode > 0:
                self.print_exiterr(exitcode, stderr)
            else:
                return stdout
        except OSError:
            self.print_oserr(cmd)

        return None
