#!/usr/bin/env python3
# coding: utf-8

# Copyright (C) 2017-present Robert Griesel
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk


class OpenDocumentDialog(object):

    def __init__(self, main_window, workspace):
        self.main_window = main_window
        self.workspace = workspace
        self.view = None

    def run(self):
        self.setup()
        self.view.open_multiple(self.main_window, None, self.dialog_process_response)

    def setup(self):
        self.view = Gtk.FileDialog()
        self.view.set_modal(True)
        self.view.set_title(_('Open'))

        file_filter = Gtk.FileFilter()
        file_filter.add_pattern('*.tex')
        file_filter.add_pattern('*.bib')
        file_filter.add_pattern('*.cls')
        file_filter.add_pattern('*.sty')
        file_filter.set_name(_('LaTeX and BibTeX Files'))
        self.view.set_default_filter(file_filter)

    def dialog_process_response(self, dialog, result):
        try:
            files = dialog.open_multiple_finish(result)
        except Exception: pass
        else:
            if files != None:
                for file in files:
                    self.workspace.open_document_by_filename(file.get_path())


