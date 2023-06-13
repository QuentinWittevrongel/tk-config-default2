"""
Need to add the hook python file in the config.env.includes.settings.tk-multi-publish2.yml
"""


import os
import maya.cmds as cmds
import maya.mel as mel
import sgtk
import inspect
import json

from tank_vendor import six

# Import the maya module of the P3D framework.
P3Dfw = sgtk.platform.current_engine().frameworks["tk-framework-P3D"].import_module("maya")
publihTools = P3Dfw.PublishTools()

# Inherit from {self}/publish_file.py 
# Check config.env.includes.settings.tk-multi-publish2.yml
HookBaseClass = sgtk.get_hook_baseclass()


class MayaShotAssetInstanceLocalAlembicPublishPlugin(HookBaseClass):

    def accept(self, settings, item):
    
        return publihTools.hookPublishAccept(
            self,
            settings,
            item,
            self.publishTemplate,
            self.propertiesPublishTemplate,
            isChild=True
        )

    def validate(self, settings, item):

        mayaObject = publihTools.getItemProperty(item, "mayaObject")
        asset = mayaObject.fullname
        # Get the namespace.
        namespace = mayaObject.rootNamespace

        # Get the local controller.
        localCon = '{RIG}|{NS}:base_module|{NS}:base_controllers_GRP|{NS}:base_FK_GRP|{NS}:base_global_CON|{NS}:base_local_CON'.format(
            RIG = mayaObject.groupRig,
            NS = namespace
        )

        # Check if there is at least two keyframe.
        if(not cmds.objExists(localCon)):
            errorMsg = "The asset {} has no local controller.".format(mayaObject.name)
            self.logger.error(errorMsg)
            raise Exception(errorMsg)

        publihTools.hookPublishValidateMayaObject(
            self,
            settings,
            item,
            self.propertiesPublishTemplate,
            addFields={
                "Asset"     : mayaObject.name,
                "instance"  : "{:03d}".format(mayaObject.instance)
            }
        )

        # run the base class validation
        return super(MayaShotAssetInstanceLocalAlembicPublishPlugin, self).validate(settings, item)


    def publish(self, settings, item):

        # Get the asset.
        mayaObject = publihTools.getItemProperty(item, "mayaObject")
        asset = mayaObject.fullname
        # Get the namespace.
        namespace = mayaObject.rootNamespace

        # Get the local controller.
        localCon = '{RIG}|{NS}:base_module|{NS}:base_controllers_GRP|{NS}:base_FK_GRP|{NS}:base_global_CON|{NS}:base_local_CON'.format(
            RIG = mayaObject.groupRig,
            NS = namespace
        )
        startFrame, endFrame = publihTools.getSceneFrameRange()

        # Check if there is at least two keyframe.
        if(not cmds.objExists(localCon)):
            errorMsg = "The asset {} has no local controller.".format(mayaObject.name)
            self.logger.error(errorMsg)
            raise Exception(errorMsg)



        # Get the path to create and publish.
        publish_path = item.properties["path"]

        # Ensure the publish folder exists:
        publish_folder = os.path.dirname(publish_path)
        self.parent.ensure_folder_exists(publish_folder)
        # Publish the alembic.
        publihTools.exportAlembic(
            [localCon],
            startFrame,
            startFrame,
            publish_path,
            exportABCVersion = 1,
            spaceType = "world"
        )

        # let the base class register the publish
        super(MayaShotAssetInstanceLocalAlembicPublishPlugin, self).publish(settings, item)

    @property
    def publishTemplate(self):
        return "Publish Template"

    @property
    def propertiesPublishTemplate(self):
        return "publish_template"

    @property
    def description(self):
        return """
        <p>This plugin publishs the nimation frames as a json file.
        You need to select root transform of the asset.</p>
        """

    @property
    def settings(self):
        # inherit the settings from the base publish plugin
        base_settings = super(MayaShotAssetInstanceLocalAlembicPublishPlugin, self).settings or {}

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
        return ["maya.shot.assetInstance.local.abc"]