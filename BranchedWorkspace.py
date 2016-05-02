from collections import defaultdict
import os
import pickle
import re
import sublime
import sublime_plugin
import subprocess
import time

class GitCommand(sublime_plugin.WindowCommand):
    @staticmethod
    def _active_file_name(view):
        print("running def _active_file_name(view):")
        view = view.window().active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()

    @staticmethod
    def get_working_dir(view):
        print("running def get_working_dir(view):")
        win = view.window()
        folders = [] if win == None else win.folders()
        return folders[0] if folders != [] else None

    @staticmethod
    def run_command(command):
        print("running def run_command("+str(command)+"):")
        command = [arg for arg in re.split(r"\s+", command) if arg]
        if command[0] == 'git':
            command[0] = GIT
        return subprocess.check_output(command).decode('ascii').strip()

    @staticmethod
    def getBranch():
        print("running def getBranch():")
        os.chdir(sublime.active_window().folders()[0])
        return GitCommand.run_command('git rev-parse --abbrev-ref HEAD')


def _test_paths_for_executable(paths, test_file):
    print("running def _test_paths_for_executable(paths, test_file):")
    for directory in paths:
        file_path = os.path.join(directory, test_file)
        if os.path.exists(file_path) and os.access(file_path, os.X_OK):
            return file_path

def find_git():
    print("running def find_git():")
    path = os.environ.get('PATH', '').split(os.pathsep)
    if os.name == 'nt':
        git_cmd = 'git.exe'
    else:
        git_cmd = 'git'

    git_path = _test_paths_for_executable(path, git_cmd)

    if not git_path:
        # /usr/local/bin:/usr/local/git/bin
        if os.name == 'nt':
            extra_paths = (
                os.path.join(os.environ["ProgramFiles"], "Git", "bin"),
                os.path.join(os.environ["ProgramFiles(x86)"], "Git", "bin"),
            )
        else:
            extra_paths = (
                '/usr/local/bin',
                '/usr/local/git/bin',
            )
        git_path = _test_paths_for_executable(extra_paths, git_cmd)
    return git_path
GIT = find_git()

previous_branch = defaultdict(lambda: None)

class BranchedWorkspace(sublime_plugin.EventListener):
    def on_activated_async(self, view):
        print("running def on_activated(self, view):")
        working_dir = sublime.active_window().folders()
        print("working dir " + str(working_dir))
        working_dir = None if working_dir == [] else working_dir[0]
        new_root = git_root(working_dir)

        # the plugin only activates when the root folder is the git folder
        if working_dir != new_root:
            return

        new_branch = GitCommand.getBranch()

        print("branch is " + str(new_branch))

        if not previous_branch[working_dir]:
            # we try to load a saved config
            self.close_root(new_root)
            self.load_branch(new_branch, new_root)
            previous_branch[new_root] = new_branch
        elif previous_branch[working_dir] != new_branch:
            # we need to save the current state
            # and load the saved state (if any) for the new branch
            dic = defaultdict(list)
            for win in sublime.windows():
                # we only care about the same git repository
                if win.folders() == [] or win.folders()[0] != new_root:
                    continue
                for doc in win.views():
                    name = doc.file_name()
                    if name != None:
                        print("adding file " + name)
                        dic[win.id()].append(name)
                if dic[win.id()] == []:
                    # dic[win.id()] = win.folders()
                    pass

            self.save_current_branch(dic, previous_branch[working_dir], new_root)
            previous_branch[new_root] = new_branch
            self.close_root(new_root)
            self.load_branch(new_branch, new_root)
            for win in dic:
                print("win " + str(win))
                for doc in dic[win]:
                    print("\t" + doc)

    def close_root(self, root):
        print("running def close_root(self, "+str(root)+"):")
        for win in sublime.windows():
            if win.folders() != [] and win.folders()[0] == root:
                for view in win.views():
                    view.set_scratch(True)
                win.run_command('close_all')

    def load_saved_projects(self, view):
        print("running def load_saved_projects(self, view):")
        root = git_root(GitCommand.get_working_dir(view))
        print(root)

    def save_current_branch(self, dic, branch, root):
        print("running def save_current_branch(self, dic, "+str(branch)+", "+str(root)+"):")
        if not root:
            print("save: off of git")
        else:
            print("saving branch: " + branch)
            path = root + '/.git/BranchedProjects.sublime'
            obj = {}
            if os.path.isfile(path):
                with open(path, 'rb') as f:
                    obj = pickle.load(f)
                    f.close()
            obj[branch] = dic
            with open(path, 'w+b') as f:
                pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)
                f.close()


    def load_branch(self, branch, root):
        print("running def load_branch(self, "+str(branch)+", "+str(root)+"):")
        if not root:
            print("load: off of git")
        else:
            print("load branch: " + branch)
            path = root + '/.git/BranchedProjects.sublime'
            obj = defaultdict(lambda: defaultdict(list))
            if os.path.isfile(path):
                with open(path, 'rb') as f:
                    tmp = pickle.load(f)
                    for o in tmp:
                        obj[o] = tmp[o]
                    f.close()

            for win in obj[branch]:
                new_win = sublime.active_window()
                new_win.set_project_data({
                    'folders': [{'path': root, 'follow_symlinks': True}]
                })
                for doc in obj[branch][win]:
                    if os.path.isfile(doc):
                        print("loading file " + doc)
                        new_win.open_file(doc)
            no_win = True
            for win in sublime.windows():
                win_root = win.folders()
                win_root = win_root[0] if win_root != [] else None
                if win_root == root:
                    no_win = False
                    break

            if no_win:
                sublime.run_command('new_window')
                new_win = sublime.active_window()
                new_win.set_project_data({
                    'folders': [{'path': root, 'follow_symlinks': True}]
                })

git_root_cache = {}
def git_root(directory):
    print("running def git_root("+str(directory)+"):")
    retval = False
    leaf_dir = directory

    if leaf_dir in git_root_cache and git_root_cache[leaf_dir]['expires'] > time.time():
        return git_root_cache[leaf_dir]['retval']

    while directory:
        if os.path.exists(os.path.join(directory, '.git')):
            retval = directory
            break
        parent = os.path.realpath(os.path.join(directory, os.path.pardir))
        if parent == directory:
            retval = False
            break
        directory = parent

    git_root_cache[leaf_dir] = {
        'retval': retval,
        'expires': time.time() + 5
    }

    return retval
