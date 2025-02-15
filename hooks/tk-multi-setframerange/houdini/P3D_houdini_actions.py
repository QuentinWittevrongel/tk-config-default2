# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import hou

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class FrameOperation(HookBaseClass):
    """
    Hook called to perform a frame operation with the
    current scene
    """

    def get_frame_range(self, **kwargs):
        """
        get_frame_range will return a tuple of (in_frame, out_frame)

        :returns: Returns the frame range in the form (in_frame, out_frame)
        :rtype: tuple[int, int]
        """
        current_in, current_out = hou.playbar.playbackRange()
        return (current_in, current_out)

    def set_frame_range(self, in_frame=None, out_frame=None, **kwargs):
        """
        set_frame_range will set the frame range using `in_frame` and `out_frame`

        :param int in_frame: in_frame for the current context
            (e.g. the current shot, current asset etc)

        :param int out_frame: out_frame for the current context
            (e.g. the current shot, current asset etc)

        """
        # Get the current engine.
        currentEngine = sgtk.platform.current_engine()
        # Get the current context.
        currentContext = currentEngine.context
        # Get the context project.
        ctxtProject = currentContext.project
        # Get the context step.
        ctxtStep = currentContext.step
        # Get the context entity.
        ctxtEntity = currentContext.entity
        # Get the context task.
        ctxtTask = currentContext.task
        # Get the context user.
        ctxtUser = currentContext.user

        outerStartFrame = in_frame - 24
        outerEndFrame   = out_frame + 24
        innerStartFrame = in_frame
        innerEndFrame   = out_frame

        if(ctxtEntity["type"] == "Shot" and ctxtStep["name"] == "Lighting"):
            outerStartFrame = in_frame - 12
            outerEndFrame = out_frame + 12
            innerStartFrame = in_frame
            innerEndFrame = out_frame
        else:
            outerStartFrame = in_frame - 24
            outerEndFrame = out_frame + 24
            innerStartFrame = in_frame
            innerEndFrame = out_frame

        # Set the outer frame range for the current scene.
        hou.playbar.setFrameRange(outerStartFrame, outerEndFrame)
        # set frame ranges for plackback.
        hou.playbar.setPlaybackRange(innerStartFrame, innerEndFrame)
