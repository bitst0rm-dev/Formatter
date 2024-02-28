#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# @copyright    Copyright (c) 2019-present, Duc Ng. (bitst0rm)
# @link         https://github.com/bitst0rm
# @license      The MIT License (MIT)

import logging
from ..core import common

log = logging.getLogger(__name__)
INTERPRETERS = ['node']
EXECUTABLES = ['prettier', 'bin-prettier.js']
MODULE_CONFIG = {
    'source': 'https://github.com/prettier/prettier',
    'name': 'Prettier',
    'uid': 'prettier',
    'type': 'beautifier',
    'syntaxes': ['css', 'scss', 'less', 'js', 'jsx', 'json', 'html', 'graphql', 'markdown', 'tsx', 'vue', 'yaml'],
    'exclude_syntaxes': None,
    'executable_path': '/path/to/node_modules/.bin/prettier or /path/to/node_modules/.bin/bin-prettier.js',
    'args': None,
    'config_path': {
        'default': 'prettier_rc.json'
    },
    'comment': 'requires node on PATH if omit interpreter_path'
}


class PrettierFormatter(common.Module):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_cmd(self):
        if common.IS_WINDOWS:
            executable = self.get_executable(runtime_type='node')
            if not executable.endswith('js'):
                cmd = [executable]

                cmd.extend(self.get_args())
            else:
                cmd = self.get_combo_cmd(runtime_type='node')
        else:
            cmd = self.get_combo_cmd(runtime_type='node')

        if not self.is_valid_cmd(cmd):
            return None

        cmd.extend(['--no-color'])

        path = self.get_config_path()
        if path:
            cmd.extend(['--no-config', '--config', path])

        file = self.get_pathinfo()['path']
        dummy = file if file else 'dummy.' + self.get_assigned_syntax()
        cmd.extend(['--stdin-filepath', dummy])

        log.debug('Current arguments: %s', cmd)
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
