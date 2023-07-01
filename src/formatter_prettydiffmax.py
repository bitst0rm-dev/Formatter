#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# @id           $Id$
# @rev          $Format:%H$ ($Format:%h$)
# @tree         $Format:%T$ ($Format:%t$)
# @date         $Format:%ci$
# @author       $Format:%an$ <$Format:%ae$>
# @copyright    Copyright (c) 2019-present, Duc Ng. (bitst0rm)
# @link         https://github.com/bitst0rm
# @license      The MIT License (MIT)

import os
import logging
import tempfile
from . import common

log = logging.getLogger('root')
INTERPRETER_NAMES = ['node']
EXECUTABLE_NAMES = ['prettydiff']


class PrettydiffmaxFormatter:
    def __init__(self, view, identifier, region, is_selected):
        self.view = view
        self.identifier = identifier
        self.region = region
        self.is_selected = is_selected
        self.pathinfo = common.get_pathinfo(view.file_name())

    def get_cmd(self, text):
        interpreter = common.get_interpreter_path(INTERPRETER_NAMES)
        executable = common.get_executable_path(self.identifier, EXECUTABLE_NAMES)

        if not interpreter or not executable:
            return None

        cmd = [interpreter, executable]

        cmd.extend(['beautify'])

        args = common.get_args(self.identifier)
        if args:
            cmd.extend(args)

        config = common.get_config_path(self.view, self.identifier, self.region, self.is_selected)
        if config:
            cmd.extend(['config', config])

        tmp_file = None
        if self.pathinfo[0]:
            cmd.extend(['source', self.pathinfo[0]])
        else:
            suffix = '.' + common.get_assign_syntax(self.view, self.identifier, self.region, self.is_selected)
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=suffix, dir=self.pathinfo[1], encoding='utf-8') as file:
                file.write(text)
                file.close()
                tmp_file = file.name
                cmd.extend(['source', tmp_file])

        return cmd, tmp_file

    def format(self, text):
        cmd, tmp_file = self.get_cmd(text)
        log.debug('Current executing arguments: %s', cmd)
        if not cmd:
            if tmp_file and os.path.isfile(tmp_file):
                os.unlink(tmp_file)
            return None

        try:
            proc = common.exec_cmd(cmd, self.pathinfo[0])
            stdout, stderr = proc.communicate()

            if tmp_file and os.path.isfile(tmp_file):
                os.unlink(tmp_file)

            errno = proc.returncode
            if errno > 0:
                log.error('File not formatted due to an error (errno=%d): "%s"', errno, stderr.decode('utf-8'))
            else:
                return stdout.decode('utf-8')
        except OSError:
            if tmp_file and os.path.isfile(tmp_file):
                os.unlink(tmp_file)

            log.error('Error occurred when running: %s', ' '.join(cmd))

        return None