
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

        # Get the engine.
        engine = sgtk.platform.current_engine()
        # Get the current context.
        context = engine.context
        # Get the current entity.
        entity = context.entity

        # Get the shotgrid api.
        sg = engine.shotgun
        # Get the cut_in and cut_out of the current task.
        filter = [["id", "is", entity["id"]]]
        fields = ["sg_cut_in", "sg_cut_out"]
        entityData = sg.find_one("Shot", filter, fields)

        # Check if the entity exist.
        if(not entityData):
            errorMsg = "The entity has not been found."
            self.logger.error(errorMsg)
            return {"accepted": False, "checked": True}

        # Check if the cut_in and cut_out are set.
        if(not entityData["sg_cut_in"] or not entityData["sg_cut_out"]):
            errorMsg = "The cut_in and cut_out are not set."
            self.logger.info(errorMsg)
            return {"accepted": False, "checked": True}

        return {"accepted": accepted, "checked": True}

    def validate(self, settings, item):

        # Get the engine.
        engine = sgtk.platform.current_engine()
        # Get the current context.
        context = engine.context
        # Get the current entity.
        entity = context.entity

        # Get the shotgrid api.
        sg = engine.shotgun
        # Get the cut_in and cut_out of the current task.
        filter = [["id", "is", entity["id"]]]
        fields = ["sg_cut_in", "sg_cut_out"]
        entityData = sg.find_one("Shot", filter, fields)

        # Check if the entity exist.
        if(not entityData):
            errorMsg = "The task has not been found."
            self.logger.error(errorMsg)
            raise Exception(errorMsg)
        
        # Check if the cut_in and cut_out are set.
        if(not entityData["sg_cut_in"] or not entityData["sg_cut_out"]):
            errorMsg = "The cut_in and cut_out are not set."
            self.logger.error(errorMsg)
            raise Exception(errorMsg)

        return True

    def publish(self, settings, item):

        # Get the engine.
        engine = sgtk.platform.current_engine()
        # Get the current context.
        context = engine.context
        # Get the current entity.
        entity = context.entity

        # Get the shotgrid api.
        sg = engine.shotgun
        # Get the cut_in and cut_out of the current task.
        filter = [["id", "is", entity["id"]]]
        fields = ["sg_cut_in", "sg_cut_out"]
        entityData = sg.find_one("Shot", filter, fields)

        in_frame = entityData["sg_cut_in"]
        out_frame = entityData["sg_cut_out"]

        # set frame ranges for plackback
        cmds.playbackOptions(
            minTime             = in_frame,
            maxTime             = out_frame,
            animationStartTime  = in_frame  - 24,
            animationEndTime    = out_frame + 24,
        )

        # set frame ranges for rendering
        cmds.setAttr("defaultRenderGlobals.startFrame", in_frame)
        cmds.setAttr("defaultRenderGlobals.endFrame", out_frame)
        

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