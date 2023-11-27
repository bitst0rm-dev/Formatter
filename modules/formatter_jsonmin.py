#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# @rev          $Format:%H$ ($Format:%h$)
# @tree         $Format:%T$ ($Format:%t$)
# @date         $Format:%ci$
# @author       $Format:%an$ <$Format:%ae$>
# @copyright    Copyright (c) 2019-present, Duc Ng. (bitst0rm)
# @link         https://github.com/bitst0rm
# @license      The MIT License (MIT)

import logging
import json
import sublime
from ..core import common

log = logging.getLogger(__name__)
MODULE_CONFIG = {
    'source': 'build-in',
    'name': 'JSONMin',
    'uid': 'jsonmin',
    'type': 'minifier',
    'syntaxes': ['json'],
    'exclude_syntaxes': None,
    "executable_path": None,
    'args': None,
    'config_path': None,
    'comment': 'build-in, no executable, no config'
}


class JsonminFormatter(common.Module):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def format(self):
        try:
            text = self.get_text_from_region(self.region)
            obj = sublime.decode_value(text)
            result = json.dumps(obj, ensure_ascii=False, separators=(',', ':'), indent=None)
            return result
        except ValueError as err:
            log.error('File not formatted due to ValueError: "%s"', err)

        return None
