
"""
Need to add the hook python file in the config.env.includes.settings.tk-multi-publish2.yml
"""


import os
import maya.cmds as cmds
import maya.mel as mel
import sgtk
import inspect

from tank_vendor import six

# Import the maya module of the P3D framework.
P3Dfw = sgtk.platform.current_engine().frameworks["tk-framework-P3D"].import_module("maya")
publihTools = P3Dfw.PublishTools()

# Inherit from {self}/publish_file.py 
# Check config.env.includes.settings.tk-multi-publish2.yml
HookBaseClass = sgtk.get_hook_baseclass()


class MayaEnvironmentScenePublishPlugin(HookBaseClass):

    def accept(self, settings, item):

        self.logger.info("Environment Maya Publish | accept")

        return publihTools.hookPublishAccept(
            self,
            settings,
            item,
            self.publishTemplate,
            self.propertiesPublishTemplate,
            isChild=True
        )

    def validate(self, settings, item):

        self.logger.info("Environment Maya Publish | validate")

        publihTools.hookPublishValidateMayaObject(
            self,
            settings,
            item,
            self.propertiesPublishTemplate
        )

        # Override the publish type.
        item.properties["publish_type"] = "Maya Environment"

        # Run the base class validation
        return super(MayaEnvironmentScenePublishPlugin, self).validate(settings, item)


    def publish(self, settings, item):

        self.logger.info("Environment Maya Publish | publish")

        publihTools.hookPublishMayaEnvironmentPublish(
            self,
            settings,
            item,
            isChild=True
        )

        # let the base class register the publish
        super(MayaEnvironmentScenePublishPlugin, self).publish(settings, item)


    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        pass

    @property
    def publishTemplate(self):
        return "Environment Scene Publish Template"

    @property
    def propertiesPublishTemplate(self):
        return "environment_scene_publish_template"

    @property
    def description(self):
        return """
        <p>This plugin publish the environment for the rig pipeline step
        You need to select root transform of the environment.</p>
        """

    @property
    def settings(self):
        # inherit the settings from the base publish plugin
        base_settings = super(MayaEnvironmentScenePublishPlugin, self).settings or {}

        # settings specific to this class
        maya_publish_settings = {
            self.publishTemplate : {
                "type": "template",
                "default": None,
                "description": "Template path for published work files. Should"
                "correspond to a template defined in "
                "templates.yml.",
            }
        }

        # update the base settings
        base_settings.update(maya_publish_settings)

        return base_settings


    @property
    def item_filters(self):
        return ["maya.environment.ma"]


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