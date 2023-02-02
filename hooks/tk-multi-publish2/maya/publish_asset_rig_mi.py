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


class MayaAssetRigMIPublishPlugin(HookBaseClass):

    def accept(self, settings, item):

        return publihTools.hookPublishAcceptLOD(
            self,
            settings,
            item,
            self.publishTemplate,
            self.propertiesPublishTemplate,
            "MI"
        )

    def validate(self, settings, item):

        publihTools.hookPublishValidateAsset(
            self,
            settings,
            item,
            self.propertiesPublishTemplate,
            "MI",
            addFields={"lod":"mid"}
        )

        # run the base class validation
        return super(MayaAssetRigMIPublishPlugin, self).validate(settings, item)


    def publish(self, settings, item):

        publihTools.hookPublishMayaRigLODPublish(
            self,
            settings,
            item,
            "MI"
        )

        # let the base class register the publish
        super(MayaAssetRigMIPublishPlugin, self).publish(settings, item)

    @property
    def publishTemplate(self):
        return "Asset Rig MI Publish Template"

    @property
    def propertiesPublishTemplate(self):
        return "asset_rig_mi_publish_template"

    @property
    def description(self):
        return """
        <p>This plugin publish the selected assets for the model pipeline step
        You need to select root transform of the asset.</p>
        """

    @property
    def settings(self):
        # inherit the settings from the base publish plugin
        base_settings = super(MayaAssetRigMIPublishPlugin, self).settings or {}

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
        return ["maya.asset.rig.mid.ma"]