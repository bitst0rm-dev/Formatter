import os
import threading
import time

import sublime
import sublime_plugin

from ..core import (CONFIG, CleanupHandler, ConfigHandler, DotFileHandler,
                    InterfaceHandler, LayoutHandler, OptionHandler,
                    SyntaxHandler, log, reload_modules)
from ..core.constants import PACKAGE_NAME
from .recursive_format import RecursiveFormat
from .single_format import SingleFormat


class SyncScrollManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = False
        self.thread = None

    def start_sync_scroll(self, target_type, active_view, target_view):
        with self.lock:
            if not self.running:
                self.running = True
                self.thread = threading.Thread(
                    target=self.sync_scroll, args=(target_type, active_view, target_view)
                )
                self.thread.start()

    def stop_sync_scroll(self):
        with self.lock:
            self.running = False
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=0.4)
                if self.thread.is_alive():
                    self.thread = None

    def sync_scroll(self, target_type, active_view, target_view):
        while self.running:
            # log.debug('Sync scroll target: %s', target_type)
            target_view.set_viewport_position(active_view.viewport_position(), False)
            time.sleep(0.25)


class SavePasteManager:
    def __init__(self, view):
        self.view = view

    def apply_formatting(self, operation):
        path = self.view.file_name()
        if path and os.path.splitext(path)[1] not in ['.sublime-settings']:
            auto_format_user_config = DotFileHandler(view=self.view).get_auto_format_user_config(active_file_path=path)
            auto_format_user_operation = OptionHandler.query(auto_format_user_config, False, operation)
            auto_format_config_operation = OptionHandler.query(CONFIG, False, 'auto_format', 'config', operation)
            if (auto_format_user_config and auto_format_user_operation) or auto_format_config_operation:
                get_auto_format_args = DotFileHandler(view=self.view).get_auto_format_args(active_file_path=path)
                if get_auto_format_args:
                    CleanupHandler.clear_console()

                    SingleFormat(self.view, **get_auto_format_args).run()
                    return

        self._on_paste_or_save(opkey=operation)

    def _on_paste_or_save(self, opkey=None):
        if not opkey:
            return None

        unique = OptionHandler.query(CONFIG, {}, 'format_on_priority') or OptionHandler.query(CONFIG, {}, 'format_on_unique')
        if unique and isinstance(unique, dict) and unique.get('enable', False):
            self._on_paste_or_save__unique(unique, opkey)
        else:
            self._on_paste_or_save__regular(opkey)

    def _on_paste_or_save__unique(self, unique, opkey):
        def are_unique_values(unique):
            flat_values = [value for key, values_list in unique.items() if key != 'enable' for value in values_list]
            return (len(flat_values) == len(set(flat_values)))

        formatters = OptionHandler.query(CONFIG, {}, 'formatters')

        if are_unique_values(unique):
            for uid, value in unique.items():
                if uid == 'enable':
                    continue

                v = OptionHandler.query(formatters, None, uid)
                if self._should_skip_formatter(uid, v, opkey):
                    continue

                syntax = self._get_syntax(uid)
                if syntax in value:
                    CleanupHandler.clear_console()

                    SingleFormat(view=self.view, uid=uid, type=value.get('type', None)).run()
                    break
        else:
            InterfaceHandler.popup_message('There are duplicate syntaxes in your "format_on_priority" option. Please sort them out.', 'ERROR')

    def _on_paste_or_save__regular(self, opkey):
        seen = set()
        formatters = OptionHandler.query(CONFIG, {}, 'formatters')

        for uid, value in formatters.items():
            if self._should_skip_formatter(uid, value, opkey):
                continue

            syntax = self._get_syntax(uid)
            if syntax in value.get('syntaxes', []) and syntax not in seen:
                CleanupHandler.clear_console()

                log.debug('"%s" (UID: %s | Syntax: %s)', opkey, uid, syntax)
                SingleFormat(view=self.view, uid=uid, type=value.get('type', None)).run()
                seen.add(syntax)

    def _should_skip_formatter(self, uid, value, opkey):
        is_qo_mode = ConfigHandler.is_quick_options_mode()
        is_rff_on = OptionHandler.query(CONFIG, False, 'quick_options', 'recursive_folder_format')

        if not isinstance(value, dict) or ('disable' in value and value.get('disable', True)) or ('enable' in value and not value.get('enable', False)):
            return True

        if (is_qo_mode and uid not in OptionHandler.query(CONFIG, [], 'quick_options', opkey)) or (not is_qo_mode and not value.get(opkey, False)):
            return True

        if (is_qo_mode and is_rff_on) or (not is_qo_mode and OptionHandler.query(value, False, 'recursive_folder_format', 'enable')):
            mode = 'Quick Options' if is_qo_mode else 'User Settings'
            log.info('%s mode: %s has the "%s" option enabled, which is incompatible with "recursive_folder_format" mode.', mode, uid, opkey)
            return True

        return False

    def _get_syntax(self, uid):
        is_selected = any(not sel.empty() for sel in self.view.sel())

        if is_selected:
            # Selections: find the first non-empty region or use the first region if all are empty
            region = next((region for region in self.view.sel() if not region.empty()), self.view.sel()[0])
        else:
            # Entire file
            region = sublime.Region(0, self.view.size())

        uid, syntax = SyntaxHandler(view=self.view, uid=uid, region=region, auto_format_config=None).get_assigned_syntax(view=self.view, uid=uid, region=region)
        return syntax


class FormatterListener(sublime_plugin.EventListener):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sync_scroll_manager = SyncScrollManager()

    def on_load(self, view):
        if view == RecursiveFormat.CONTEXT['new_view']:
            RecursiveFormat(view).next_thread(view, is_ready=False)

        if view.file_name() and view.file_name().endswith(PACKAGE_NAME + '.sublime-settings'):
            view.run_command('collapse_setting_sections')

    def on_activated(self, view):
        ConfigHandler.project_config_overwrites_config()

        if OptionHandler.query(CONFIG, False, 'layout', 'sync_scroll') and LayoutHandler.want_layout():
            self.sync_scroll_manager.stop_sync_scroll()

            src_view = self._find_src_view_by_dst_view(view)
            if src_view:
                self.sync_scroll_manager.start_sync_scroll('src', view, src_view)
            else:
                dst_view = self._find_dst_view_by_src_view(view)
                if dst_view:
                    self.sync_scroll_manager.start_sync_scroll('dst', view, dst_view)

    def _find_src_view_by_dst_view(self, dst_view):
        src_view_id = dst_view.settings().get('txt_vref')
        if src_view_id:
            for window in sublime.windows():
                for view in window.views():
                    if view.id() == src_view_id:
                        return view
        return None

    def _find_dst_view_by_src_view(self, src_view):
        src_view_id = src_view.id()
        for window in sublime.windows():
            for view in window.views():
                if view.settings().get('txt_vref') == src_view_id:
                    return view
        return None

    def on_pre_close(self, view):
        def _set_single_layout(window, view):
            # Auto-switch to single layout upon closing the latest view
            group, _ = window.get_view_index(view)
            if len(window.views_in_group(group)) == 1:
                sublime.set_timeout(lambda: window.set_layout(LayoutHandler.assign_layout('single')), 0)

        window = view.window()
        if window and LayoutHandler.want_layout() and window.num_groups() == 2:
            _set_single_layout(window, view)

    def on_post_text_command(self, view, command_name, args):
        if command_name in ['paste', 'paste_and_indent']:
            SavePasteManager(view).apply_formatting('format_on_paste')
            return None

    def on_pre_save(self, view):
        SavePasteManager(view).apply_formatting('format_on_save')

    def on_post_save(self, view):
        if OptionHandler.query(CONFIG, False, 'debug') and OptionHandler.query(CONFIG, False, 'dev'):
            # For development only
            self.sync_scroll_manager.stop_sync_scroll()
            reload_modules(print_tree=False)