#!/usr/bin/python
# find icons at /usr/share/icons
# pyinstaller -F grep_tool.py 打包
import os
import re
from gi.repository import Gtk as gtk, Gdk as gdk, Pango, GObject

ICONSIZE = gtk.IconSize.MENU
get_icon = lambda name: gtk.Image.new_from_icon_name(name, ICONSIZE)


class Tab(gtk.HBox):

    __gsignals__ = {
        "close": (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, []),
    }

    def __init__(self):
        gtk.HBox.__init__(self)

        self.pattern = ""
        self.path_option = ""
        self.include_option = ""
        self.binary_option = False
        self.ignore_pattern = ""
        self.ignore_case = False
        self.ignore_pattern_ignore_case = False

        self._close_btn = gtk.Button()
        self._close_btn.set_margin_left(10)
        self._close_btn.add(get_icon("window-close-symbolic"))
        self._close_btn.connect("clicked", self._close_cb)
        self.pack_end(self._close_btn, False, False, 0)

    def _close_cb(self, button):
        self.emit("close")


class grepWindow(gtk.Window):

    __gsignals__ = {
        "new-tab": (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, []),
        "close-tab": (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, [GObject.TYPE_PYOBJECT]),
    }

    def __init__(self, title = "grep tool"):
        gtk.Window.__init__(self, title=title)

        setting = gtk.Settings.get_default()
        setting.set_property('gtk-application-prefer-dark-theme', True)

        self._count = 0

        self.set_title("Grep Tool")
        self.set_icon_name("system-search-symbolic")
        self.set_position(gtk.WindowPosition.CENTER)

        self._button_box = gtk.Box()
        self.set_keep_above(True)
        self.modify_bg(0,gdk.Color(0xe000,0xe000,0xe000))
        self.add(self._button_box)

        self._notebook = gtk.Notebook()
        self._notebook.set_scrollable(True)
        self._notebook.set_show_border(False)
        self._notebook.set_size_request(20,1)
        self._button_box.pack_start(self._notebook, True, True, 10)
        self._hbox = gtk.HBox()
        self._notebook.set_action_widget(self._hbox, gtk.PackType.END)
        self._newtab_btn = gtk.Button.new_from_icon_name("tab-new-symbolic", gtk.IconSize.BUTTON)
        self._newtab_btn.connect("clicked", self._new_tab_cb)
        self._hbox.pack_start(self._newtab_btn, False, False, 0)
        self._hbox.show_all()

        self.hovering_over_link = False

        self.set_size_request(800,200)

        # folder tree
        directory = "/home/jiaying/"
        self._treestore = gtk.TreeStore(str)
        self.parents = {}
        self._row_activate_dict = {}

        self.get_tree_data(directory)

    def get_tree_data(self, directory, depth=1):
        if depth > 3:
            return
        for dirs in sorted(os.listdir(directory)):
            if dirs[0] == '.':
                continue
            path = os.path.join(directory, dirs)
            if os.path.isdir(path):
                os.chdir(path)
                self.parents[path] = self._treestore.append(self.parents.get(directory, None),[dirs])
                self._row_activate_dict[self._treestore[self.parents[path]].path.to_string()] = path
                # read subdirs as child rows
                self.get_tree_data(path, depth=depth+1)
                os.chdir("..") 
    
    def draw_each_page(self, tab):
        outer_box = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=10)
        outer_box.set_size_request(300,100)

        # 文件夹列表
        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.set_policy(gtk.PolicyType.AUTOMATIC,
                                   gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_size_request(200, 50)
        view = gtk.TreeView(self._treestore)
        column = gtk.TreeViewColumn('Files')
        view.append_column(column)
        cell = gtk.CellRendererText()
        column.pack_start(cell, True)
        column.add_attribute(cell, 'text', 0)

        view.connect('row-activated', self.folder_tree_select, tab)
        scrolled_window.add(view)
        outer_box.pack_start(scrolled_window, False, False, True)

        main_box = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=0)
        outer_box.pack_start(main_box, True, True, 0)

        # 第一行搜索栏
        search_box = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=0)
        search_box.set_size_request(300,20)
        main_box.pack_start(search_box, False, False, 10)

        # 第二行选项栏
        option_box = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=0)
        option_box.set_size_request(300,20)
        main_box.pack_start(option_box, False, False, 0)

        # 底层结果栏
        result_box = gtk.Box(spacing = 0)
        main_box.pack_start(result_box, True, True, 10)

        scrollWindow = gtk.ScrolledWindow()
        result_box.pack_start(scrollWindow, True, True, 0)

        tab.textView = gtk.TextView()
        tab.textView.set_property('editable', False)
        tab.textView.connect("key-press-event", self.key_press_event, tab)
        tab.textView.connect("event-after", self.event_after, tab)
        tab.textView.connect("motion-notify-event", self.motion_notify_event, tab)
        tab.buffer = tab.textView.get_buffer()
        tab.buffer.set_text("",-1)
        tab.tag = tab.buffer.create_tag("foreground", foreground="red")
        scrollWindow.add(tab.textView)
        display = tab.textView.get_display()
        self.hand_cursor = gdk.Cursor.new_from_name(display, "pointer")
        self.regular_cursor = gdk.Cursor.new_from_name(display, "text")

        tab.entry = gtk.Entry()
        tab.entry.set_size_request(250,20)
        tab.entry.set_text("Pattern")
        tab.entry.connect('changed', self.on_pattern_changed, tab)
        icon = "system-search-symbolic"
        tab.entry.set_icon_from_icon_name(gtk.EntryIconPosition.PRIMARY, icon)
        tab.entry.connect("activate", self.enter_pressed, tab)
        search_box.pack_start(tab.entry, True, True, 0)

        include_option = gtk.ListStore(str, str)
        include_option.append(['*.*','*.*'])
        include_option.append(['*.cpp','*.cpp'])
        include_option.append(['*.h','*.h'])
        include_option.append(['*.py','*.py'])
        include_option.append(['*.proto','*.proto'])
        include_combo = gtk.ComboBox.new_with_model_and_entry(include_option)
        include_combo.connect('changed', self.on_include_option_changed, tab)
        include_combo.set_entry_text_column(0)
        include_combo.set_active(0)
        include_combo.set_size_request(5,20)
        include_combo.set_popup_fixed_width(True)
        search_box.pack_start(include_combo, False, False, True)

        tab.ignore_case_checkbox = gtk.CheckButton("ignore case")
        tab.ignore_case_checkbox.connect("toggled", self.on_case_changed, tab)
        tab.ignore_case_checkbox.set_size_request(5,20)
        search_box.pack_start(tab.ignore_case_checkbox, False, False, True)

        tab.query_button = gtk.Button('Query')
        tab.query_button.connect('clicked', self.on_query_clicked, tab)
        include_combo.set_size_request(5,20)
        search_box.pack_start(tab.query_button, False, False, True)

        tab.ignore_entry = gtk.Entry()
        tab.ignore_entry.set_size_request(250,20)
        tab.ignore_entry.set_text("Ignore Pattern")
        tab.ignore_entry.connect('changed', self.on_ignore_pattern_changed, tab)
        icon = "edit-delete-symbolic"
        tab.ignore_entry.set_icon_from_icon_name(gtk.EntryIconPosition.PRIMARY, icon)
        tab.ignore_entry.connect("activate", self.enter_pressed, tab)
        option_box.pack_start(tab.ignore_entry, True, True, 0)

        tab.ignore_pattern_ignore_case_checkbox = gtk.CheckButton("ignore case")
        tab.ignore_pattern_ignore_case_checkbox.connect("toggled", self.on_ignore_pattern_case_changed, tab)
        tab.ignore_pattern_ignore_case_checkbox.set_size_request(5, 20)
        option_box.pack_start(tab.ignore_pattern_ignore_case_checkbox, False, False, True)

        ignore_binary_checkbox = gtk.CheckButton("include binary files")
        ignore_binary_checkbox.connect("toggled", self.on_binary_check_changed, tab)
        ignore_binary_checkbox.set_size_request(5,20)
        option_box.pack_start(ignore_binary_checkbox, False, False, True)

        accel = gtk.AccelGroup()
        accel.connect(gdk.keyval_from_name("Enter"), gdk.ModifierType.META_MASK, 0, self.enter_pressed)

        outer_box.show_all()
        return outer_box

    def enter_pressed(self, accel, tab):
        tab.query_button.emit("activate")

    def folder_tree_select(self, treeview, path, column, tab):
        file_path = self._row_activate_dict[path.to_string()]
        dirs = file_path.split('/')
        tab.label.set_text(dirs[-1])
        tab.path_option = file_path

    def on_pattern_changed(self, entry, tab):
        tab.pattern = entry.get_text()

    def on_path_option_changed(self, combo, tab):
        tree_iter = combo.get_active_iter()
        if tree_iter != None:
            model = combo.get_model()
            id, value = model[tree_iter][:2]
            tab.path_option = value
        else:
            entry = combo.get_child()
            tab.path_option = entry.get_text()

    def on_include_option_changed(self, combo, tab):
        tree_iter = combo.get_active_iter()
        if tree_iter != None:
            model = combo.get_model()
            id, value = model[tree_iter][:2]
            tab.include_option = value
        else:
            entry = combo.get_child()
            tab.include_option = entry.get_text()

    def insert_link(self, iter, text, tab):
        tag = tab.buffer.create_tag(tag_name=None, foreground="blue", underline=Pango.Underline.SINGLE)
        tag.page = text
        tab.buffer.insert_with_tags(iter, text, tag)

    def on_query_clicked(self, button, tab):
        if tab.pattern == "":
                return
        lines = ""
        tab.buffer.set_text("", 0)
        result = ""     
        command = "grep -r"
        if tab.ignore_case:
            command += "i"
        command += " \""+tab.pattern+"\" "+tab.path_option+" --include=\""+tab.include_option+"\""
        if tab.binary_option:
            command += " --binary-files='text'"
        if tab.ignore_pattern not in ["Ignore Pattern", ""]:
            command += " | grep -v"
            if tab.ignore_pattern_ignore_case:
                command += "i"
            command += " \""+tab.ignore_pattern+"\""
            if tab.binary_option:
                command += " --binary-files='text'"
        lines = getOutput(command)
        iter = tab.buffer.get_iter_at_offset(0)
        for line in lines:
            unpack = line.split(':', 1)
            if len(unpack) == 1:
                continue
            file, match = unpack
            self.insert_link(iter, file, tab)
            tab.buffer.insert(iter, ":"+match, -1)
            result += line
        f = re.finditer(tab.pattern,result)
        for i in f:
            start = tab.buffer.get_iter_at_offset(i.span()[0])
            end = tab.buffer.get_iter_at_offset(i.span()[1])
            tab.buffer.apply_tag(tab.tag, start, end)

    def on_ignore_pattern_changed(self, entry, tab):
        tab.ignore_pattern = entry.get_text()

    def on_case_changed(self, button, tab):
        tab.ignore_case = not tab.ignore_case
        if not tab.ignore_case and tab.ignore_pattern_ignore_case:
            tab.ignore_pattern_ignore_case_checkbox.set_active(False)
        button.set_label("ignoring" if tab.ignore_case else "not ignore")

    def on_ignore_pattern_case_changed(self, button, tab):
        tab.ignore_pattern_ignore_case = not tab.ignore_pattern_ignore_case
        if tab.ignore_pattern_ignore_case and not tab.ignore_case:
            tab.ignore_case_checkbox.set_active(True)
        button.set_label("ignoring" if tab.ignore_pattern_ignore_case else "not ignore")

    def on_binary_check_changed(self, button, tab):
        tab.binary_option = not tab.binary_option
        button.set_label("including binary" if tab.binary_option else "no binary")

    def follow_if_link(self, iter):
        tags = iter.get_tags()
        for tagp in tags:
            if hasattr(tagp, 'page'):
                page = tagp.page
                if page:
                    os.system("code "+page)

    def key_press_event(self, widget, event, tab):
        if event.keyval == gdk.KEY_Return or event.keyval == gdk.KEY_KP_Enter:
            iter = tab.buffer.get_iter_at_mark(tab.buffer.get_insert())
            self.follow_if_link(iter)
        return False

    def event_after(self, widget, ev, tab):
        if ev.type == gdk.EventType.BUTTON_RELEASE:
            if ev.button.button != gdk.BUTTON_PRIMARY:
                return False
            ex = ev.x
            ey = ev.y
        elif ev.type == gdk.EventType.TOUCH_END:
            ex = ev.x
            ey = ev.y
        else:
            return False
        mark = tab.buffer.get_selection_bounds()
        if mark:
            return False
        x, y = tab.textView.window_to_buffer_coords(gtk.TextWindowType.WIDGET, ex, ey)
        isok, iter = tab.textView.get_iter_at_location(x, y)
        if isok:
            self.follow_if_link(iter)
        return True

    def set_cursor_if_appropriate(self, x, y, tab):
        isok, iter = tab.textView.get_iter_at_location(x, y)
        hovering = False
        if isok:
            tags = iter.get_tags()
            for tagp in tags:
                if hasattr(tagp, 'page'):
                    page = tagp.page
                    if page:
                        hovering = True
                        break
        if hovering != self.hovering_over_link:
            self.hovering_over_link = hovering
            if hovering:
                tab.textView.get_window(gtk.TextWindowType.TEXT).set_cursor(self.hand_cursor)
            else:
                tab.textView.get_window(gtk.TextWindowType.TEXT).set_cursor(self.regular_cursor)

    def motion_notify_event(self, widget, event, tab):
        x, y = tab.textView.window_to_buffer_coords(gtk.TextWindowType.WIDGET, event.x, event.y)
        self.set_cursor_if_appropriate(x, y, tab)
        return False

    def _new_tab_cb(self, button):
        self.emit("new-tab")


def getOutput(cmd):
    r = os.popen(cmd)
    text = r.readlines()
    r.close()
    return text

def main():
    def _re(win, *args):
        win._count += 1
        tab = Tab()
        tab.label = gtk.Label("Tab " + str(win._count))
        tab.pack_start(tab.label, False, False, 5)
        tab_content = win.draw_each_page(tab)
        tab.connect("close", lambda t: win.emit("close-tab", tab_content))
        win._notebook.append_page(tab_content,tab)
        win._notebook.set_tab_detachable(tab_content, True)
        tab.show_all()

    def _cl(win, tab):
        win._notebook.remove_page(win._notebook.page_num(tab))

    win = grepWindow()
    win.connect("delete-event", gtk.main_quit)
    win.connect("realize", _re)
    win.connect("new-tab", _re)
    win.connect("close-tab", _cl)
    win.show_all()
    gtk.main()
  

if __name__ == "__main__":
    main()
