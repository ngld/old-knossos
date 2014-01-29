import os.path
import logging
import pickle
import progress
from qt import QtCore, QtGui
from ui.main import Ui_MainWindow
from ui.progress import Ui_Dialog as Ui_Progress
from parser import EntryPoint

logging.basicConfig(level=logging.INFO)

main_win = None
progress_win = None
settings = {
    'fs2_path': None,
    'mods': None,
    'installed_mods': None
}
settings_path = os.path.expanduser('~/.fs2mod-py/settings.pick')


def init_ui(ui, win):
    ui.setupUi(win)
    for attr in ui.__dict__:
        setattr(win, attr, getattr(ui, attr))

    return win


def show_progress():
    global progress_win
    
    if progress_win is None:
        progress_win = init_ui(Ui_Progress(), QtGui.QDialog())
    
    progress_win.show()
    progress.reset()
    
    def update_prog(percent, text):
        progress_win.progressBar.setValue(percent * 100)
        progress_win.label.setText(text)
    
    progress.progress_callback = update_prog


def hide_progress():
    global progress_win
    
    progress_win.hide()


# FS2 tab
def save_settings():
    with open(settings_path, 'wb') as stream:
        pickle.dump(settings, stream)


def do_gog_extract():
    QtGui.QMessageBox.warning(main_win, 'Info', 'Not yet implemented!', QtGui.QMessageBox.Ok)
    pass


def select_fs2_path():
    global settings

    settings['fs2_path'] = QtGui.QFileDialog.getExistingDirectory()

    if settings['fs2_path'] is not None and os.path.isdir(settings['fs2_path']):
        save_settings()
        main_win.tabs.setTabEnabled(1, True)
        main_win.tabs.setCurrentIndex(1)


# Mod tab
def update_list(fetch=True):
    if fetch:
        pass


def select_mod():
    pass


def install_mod():
    pass


def uninstall_mod():
    pass


def main():
    global settings, main_win

    app = QtGui.QApplication([])

    main_win = init_ui(Ui_MainWindow(), QtGui.QMainWindow())
    
    # Try to load our settings.
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'rb') as stream:
                settings = pickle.load(stream)
        except:
            logging.exception('Failed to load settings from "%s"!', settings_path)
    else:
        if not os.path.isdir(os.path.dirname(settings_path)):
            os.makedirs(os.path.dirname(settings_path))

        save_settings()

    if settings['fs2_path'] is None:
        # Disable mod tab if we don't know where fs2 is.
        main_win.tabs.setTabEnabled(1, False)
    else:
        main_win.tabs.setCurrentIndex(1)

    main_win.gogextract.clicked.connect(do_gog_extract)
    main_win.select.clicked.connect(select_fs2_path)

    main_win.install_mod.clicked.connect(install_mod)
    main_win.uninstall_mod.clicked.connect(uninstall_mod)
    main_win.select_mod.clicked.connect(select_mod)
    main_win.update.clicked.connect(update_list)
    
    update_list(False)
    
    main_win.show()
    app.exec_()

if __name__ == '__main__':
    main()
