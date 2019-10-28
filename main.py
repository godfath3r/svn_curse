#! /usr/bin/env python3
import sys
import os
import dir
import curse
from svn import local
from config import Config

from exceptions import QuitSignal


def _get_working_copy( argv ):
    if (len(argv) > 1):
        cwd = argv[1]
    else:
        cwd = os.getcwd()
    return cwd


def main():
    base = _get_working_copy(sys.argv)
    client = local.LocalClient(base)
    client.callback_get_login = login_handler

    nav = Navigation(client, base)
    nav.base_status()
    nav.input_nav()


class NavigationStatus(object):
    def __init__(self):
        self._map = {
            Config.keys['up']: 'up',
            Config.keys['down']: 'down',
            Config.keys['enter_dir']: 'enter directory',
            Config.keys['back']: 'previous directory',
            Config.keys['view_status']: 'view working copy status',
            Config.keys['browse_repo']: 'browse remote repo',
            Config.keys['quit']: 'quit'
        }
        self.text = None
        self.enter_previous = True
        self.main = True
        self.text_only = False

    def shortcuts_(self, navigation):
        excludes = []

        if self.text:
            self.main = False
        if self.main:
            excludes.extend([
                Config.keys['down'],
                Config.keys['up'],
                Config.keys['enter_dir']
            ])
        else:
            excludes.extend([
                Config.keys['view_status'],
                Config.keys['browse_repo']
            ])
        if not navigation.history:
            excludes.append([
                Config.keys['back']
            ])
        if navigation.mode == 'local':
            excludes.extend([
                Config.keys['back'],
                Config.keys['enter_dir']
            ])

        if self.text is not None and self.text_only:
            excludes = self._map.keys()

        nav_text = ', '.join(['{}: {}'.format(x, y) for x, y in sorted(self._map.items()) if x not in excludes])
        return nav_text


class Navigation(object):
    def __init__(self, client, base):
        self.c = curse.Curse()
        self._client = client
        self._base = base
        self.history = []
        self.mode = None
        self._status = NavigationStatus()

    @property
    def path(self):
        try:
            return os.path.join(*self.history)
        except TypeError:
            return None

    def input_nav(self):
        try:
            while True:
                cha = self.c.screen.getch()
                if cha == ord(Config.keys['quit']):
                    raise QuitSignal("Quit from input_nav.")
                if not self._status.main:
                    if cha == ord(Config.keys['back']) and self.mode == 'remote':
                        if self._remove():
                            self.browse_repo(self.path)
                    elif cha == ord(Config.keys['down']):
                        self.c.go_down()
                    elif cha == ord(Config.keys['up']):
                        self.c.go_up()
                    elif cha == ord(Config.keys['enter_dir']) and self.mode == 'remote':
                        if self._append():
                            self.browse_repo(self.path)
                else:
                    if cha == ord(Config.keys['browse_repo']):
                        self.mode = 'remote'
                        self._status.enter_previous = False
                        self.browse_repo()
                    elif cha == ord(Config.keys['view_status']):
                        self.mode = 'local'
                        self.view_status(self._base)

        except QuitSignal:
            self.c.quit()
            sys.exit(0)

    def base_status(self, text=None, text_only=False):
        self._status.text_only = text_only
        if text and text_only:
            self._status.text = str(text)
            self.c.update_status_line(self._status.text)
        elif text:
            self._status.text = str(text)
            self.c.update_status_line(' - '.join([self._status.text, self._status.shortcuts_(self)]))
        else:
            self.c.update_status_line(self._status.shortcuts_(self))

    def view_status(self, working_copy):
        self.base_status("status loading...", text_only=True)
        files = self._client.status()

        self.base_status(working_copy)
        self.c.print_local_files(files)

    def browse_repo(self, rel=None):
        self.c.screen.clear()
        self.base_status("browse loading...", text_only=True)
        d = dir.Dir(self._client)
        files = d.ls(rel)
        if files is None:
            self.base_status(os.path.join(self._base, rel) + " - Not under version control.", text_only=True)
            self.history = self.history[:-1]
        else:
            self.base_status(os.path.join(self._base, rel if rel else ''))
            self.c.print_remote_files(files)

    def _append(self):
        """ Returns True if append something, else False"""
        if self.c.selected:
            line = str(self.c.lines[self.c.selected])
            if line.endswith('/'):
                self.history.append(line.strip('/'))
                return True
        return False

    def _remove(self):
        """ Returns True if remove something, else False"""
        if self.history:
            self.history = self.history[:-1]
            return True
        return False


def login_handler(*args):
    # TODO: Use python keyring

    # hard-code credentials
    # return True, "username", "password", True

    # or prompt user
    user = input( "Username: " )
    passw = getpass.getpass( "Password: " )
    return True, user, passw, True


if __name__ == '__main__':
    main()
