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

import re
import os.path

from setzer.helpers.observable import Observable
import setzer.popovers.document_switcher.document_switcher_item as document_switcher_item
from setzer.popovers.document_switcher.document_switcher_viewgtk import DocumentSwitcherView
from setzer.dialogs.dialog_locator import DialogLocator
from setzer.app.color_manager import ColorManager
from setzer.app.service_locator import ServiceLocator


class DocumentSwitcher(Observable):

    def __init__(self, popover_manager, workspace):
        Observable.__init__(self)
        self.popover_manager = popover_manager
        self.workspace = workspace
        self.main_window = ServiceLocator.get_main_window()
        self.view = DocumentSwitcherView(popover_manager)

        self.root_selection_mode = False

        self.workspace.connect('new_document', self.on_new_document)
        self.workspace.connect('document_removed', self.on_document_removed)
        self.workspace.connect('new_active_document', self.on_new_active_document)

        self.popover_manager.connect('popdown', self.on_popover_popdown)
        self.popover_manager.connect('popup', self.on_popover_popup)

        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect('enter', self.on_enter)
        motion_controller.connect('motion', self.on_hover)
        motion_controller.connect('leave', self.on_leave)
        self.view.document_list.add_controller(motion_controller)

        event_controller = Gtk.GestureClick()
        event_controller.connect('pressed', self.on_button_press)
        event_controller.connect('released', self.on_button_release)
        event_controller.set_button(1)
        self.view.document_list.add_controller(event_controller)

        self.view.set_root_document_button.connect('clicked', self.set_selection_mode)
        self.view.unset_root_document_button.connect('clicked', self.unset_root_document)
        self.update_unset_root_button()

    def on_new_document(self, workspace, document):
        self.view.document_list.items.append(document)
        self.view.document_list.update_items()

        document.connect('filename_change', self.on_name_change)
        document.connect('displayname_change', self.on_name_change)
        document.connect('modified_changed', self.on_modified_changed)
        document.connect('is_root_changed', self.on_is_root_changed)

    def on_document_removed(self, workspace, document):
        self.view.document_list.items.remove(document)
        self.view.document_list.update_items()

        document.disconnect('filename_change', self.on_name_change)
        document.disconnect('displayname_change', self.on_name_change)
        document.disconnect('modified_changed', self.on_modified_changed)
        document.disconnect('is_root_changed', self.on_is_root_changed)

    def on_new_active_document(self, workspace, document):
        self.view.document_list.update_items()

    def on_name_change(self, document, name=None):
        self.view.document_list.update_items()

    def on_is_root_changed(self, document, is_root):
        self.view.document_list.update_items()
        self.update_unset_root_button()

    def on_root_state_changed(self, workspace, state):
        self.update_unset_root_button()

    def on_modified_changed(self, document):
        self.view.document_list.update_items()

    def on_enter(self, controller, x, y):
        self.view.document_list.pointer_x = x
        self.view.document_list.pointer_y = y
        self.view.document_list.queue_draw()

    def on_hover(self, controller, x, y):
        self.view.document_list.pointer_x = x
        self.view.document_list.pointer_y = y
        self.view.document_list.queue_draw()

    def on_leave(self, controller):
        self.view.document_list.pointer_x = None
        self.view.document_list.pointer_y = None
        self.view.document_list.queue_draw()

    def on_button_press(self, event_controller, n_press, x, y):
        self.view.document_list.selected_index = self.view.document_list.get_hover_item()
        self.view.document_list.close_button_active = (self.view.document_list.pointer_x > self.view.document_list.get_allocated_width() - 34)
        self.view.document_list.queue_draw()

    def on_button_release(self, event_controller, n_press, x, y):
        if self.root_selection_mode:
            if self.view.document_list.get_hover_item() != None and self.view.document_list.get_hover_item() == self.view.document_list.selected_index:
                document = self.view.document_list.visible_items[self.view.document_list.get_hover_item()]
                self.workspace.set_one_document_root(document)
                self.activate_normal_mode()
        else:
            if self.view.document_list.close_button_active:
                if self.view.document_list.get_hover_item() != None and self.view.document_list.get_hover_item() == self.view.document_list.selected_index and (self.view.document_list.pointer_x > self.view.document_list.get_allocated_width() - 34):
                    document = self.view.document_list.visible_items[self.view.document_list.get_hover_item()]
                    if document.source_buffer.get_modified():
                        active_document = self.workspace.get_active_document()
                        if document != active_document:
                            previously_active_document = active_document
                            self.workspace.set_active_document(document)
                        else:
                            previously_active_document = None

                        self.popover_manager.popdown()
                        dialog = DialogLocator.get_dialog('close_confirmation')
                        dialog.run({'unsaved_documents': [document], 'document': document, 'previously_active_document': previously_active_document}, self.on_close_document_callback)
                        return True
                    else:
                        if document == self.workspace.get_active_document():
                            self.popover_manager.popdown()
                        self.workspace.remove_document(document)
            else:
                if self.view.document_list.get_hover_item() != None and self.view.document_list.get_hover_item() == self.view.document_list.selected_index:
                    document = self.view.document_list.visible_items[self.view.document_list.get_hover_item()]
                    self.workspace.set_active_document(document)
                    self.popover_manager.popdown()
        self.view.document_list.selected_index = None
        self.view.document_list.close_button_active = False

    def on_close_document_callback(self, parameters, response):
        not_save_to_close = response['not_save_to_close_documents']
        if parameters['document'] not in not_save_to_close:
            self.workspace.remove_document(parameters['document'])
        if parameters['previously_active_document'] != None:
            self.workspace.set_active_document(parameters['previously_active_document'])
            self.popover_manager.popup_at_button('document_switcher')

    def on_popover_popup(self, name):
        if name != 'document_switcher': return

        self.view.document_list.selected_index = None
        self.view.document_list.close_button_active = False

    def on_popover_popdown(self, name):
        if name != 'document_switcher': return

        self.view.scrolled_window.get_vadjustment().set_value(0)
        self.view.document_list.pointer_x = None
        self.view.document_list.pointer_y = None
        self.view.document_list.selected_index = None
        self.view.document_list.close_button_active = False
        active_document = self.workspace.get_active_document()
        if active_document != None:
            active_document.view.source_view.grab_focus()

    def set_selection_mode(self, action, parameter=None):
        self.activate_selection_mode()

    def unset_root_document(self, action, parameter=None):
        self.workspace.unset_root_document()
        self.activate_normal_mode()

    def activate_normal_mode(self):
        self.root_selection_mode = False
        self.view.scrolled_window.get_vadjustment().set_value(0)
        self.activate_set_root_document_button()
        self.update_unset_root_button()
        self.view.root_explaination_revealer.set_reveal_child(False)
        self.view.document_list.root_selection_mode = False
        self.view.document_list.update_items()

    def activate_selection_mode(self):
        self.root_selection_mode = True
        self.view.scrolled_window.get_vadjustment().set_value(0)
        self.view.set_root_document_button.set_sensitive(False)
        self.view.unset_root_document_button.set_sensitive(True)
        self.view.root_explaination_revealer.set_reveal_child(True)
        self.view.document_list.root_selection_mode = True
        self.view.document_list.update_items()

    def activate_set_root_document_button(self):
        if len(self.workspace.open_latex_documents) > 0:
            self.view.set_root_document_button.set_sensitive(True)
        else:
            self.view.set_root_document_button.set_sensitive(False)

    def update_unset_root_button(self):
        if self.workspace.root_document != None:
            self.view.unset_root_document_button.set_sensitive(True)
        else:
            self.view.unset_root_document_button.set_sensitive(False)


