
import os
import maya.cmds as cmds
import maya.mel as mel
import sgtk

from tank_vendor import six

# Import the maya module of the P3D framework.
P3Dfw = sgtk.platform.current_engine().frameworks["tk-framework-P3D"].import_module("maya")
publihTools = P3Dfw.PublishTools()

HookBaseClass = sgtk.get_hook_baseclass()

class MayaSaveUtilityPublishPlugin(HookBaseClass):

    def accept(self, settings, item):

        accepted = True

        # Check if the scene has been saved.
        path = _session_path()
        if(not path):
            self.logger.info(
                "The scene has not been saved.",
                extra=_get_save_as_action(),
            )
            accepted = False
        
        return {"accepted": accepted, "checked": True}


    def validate(self, settings, item):

        # Check if the scene has been saved.
        path = _session_path()
        if(not path):
            errorMsg = "The scene has not been saved."
            self.logger.error(
                errorMsg,
                extra=_get_save_as_action(),
            )
            raise Exception(errorMsg)

        return True

    def publish(self, settings, item):

        # Save the scene.
        cmds.file(save=True, force=True)
        
    def finalize(self, settings, item):
        return None

    @property
    def description(self):
        return """
        <p>This plugin save the actual scene.</p>
        """

    @property
    def settings(self):
        # Inherit the settings from the base publish plugin.
        base_settings = super(MayaSaveUtilityPublishPlugin, self).settings or {}

        return base_settings

    @property
    def item_filters(self):
        return ["maya.workscene"]

def _session_path():
    """
    Return the path to the current session
    :return:
    """
    path = cmds.file(query=True, sn=True)

    if path is not None:
        path = six.ensure_str(path)

    return path


def _get_save_as_action():
    """
    Simple helper for returning a log action dict for saving the session
    """

    engine = sgtk.platform.current_engine()

    # default save callback
    callback = cmds.SaveScene

    # if workfiles2 is configured, use that for file save
    if "tk-multi-workfiles2" in engine.apps:
        app = engine.apps["tk-multi-workfiles2"]
        if hasattr(app, "show_file_save_dlg"):
            callback = app.show_file_save_dlg

    return {
        "action_button": {
            "label": "Save As...",
            "tooltip": "Save the current session",
            "callback": callback,
        }
    }