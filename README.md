# ST_Plugins

### Install

##### ST3 on Mac

In Terminal.app, run:

    cd ~/Library/Application\ Support/Sublime\ Text\ 3/Packages
    git clone https://github.com/Xaelias/ST_Plugins.git

Then restart ST3.

### BranchedWorkspace

No configuration; works as-is. Behavior may not be perfect for everybody, but it has worked well enough for me.

**Notes:**

* Switching branches **WILL** erase any unsaved modifications or new files in the buffer--without confirmation. Swapping workspace closes your previous branch's workspace then opens the newly checked-out branch's workspace.
* For the plugin swap workspaces, you must unfocus then refocus the cursor in the editor after checking out a different branch. 
