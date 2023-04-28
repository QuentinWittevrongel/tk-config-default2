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


class MayaShotAssetInstanceFramesJsonPublishPlugin(HookBaseClass):

    def accept(self, settings, item):

        acceptStates = publihTools.hookPublishAccept(
            self,
            settings,
            item,
            self.publishTemplate,
            self.propertiesPublishTemplate,
            isChild=True
        )
        # Uncheck by default.
        acceptStates["checked"] = False
    
        return acceptStates

    def validate(self, settings, item):

        mayaObject = publihTools.getItemProperty(item, "mayaObject")
        asset = mayaObject.fullname

        # Get every controllers children of the asset. Transforms that ends with _CON.
        controllers = cmds.listRelatives(asset, allDescendents=True, type='transform', fullPath=True)
        controllers = [x for x in controllers if x.endswith('_CON')]

        # Get the keyed frames.
        keyedframes = cmds.keyframe(controllers, query=True, timeChange=True)
        if(keyedframes):
            keyedFrames = list(set(keyedframes))
        else:
            keyedFrames = []
        # Check if there is at least two keyframe.
        if(len(keyedFrames) < 2):
            errorMsg = "The asset {} has no animation.".format(mayaObject.name)
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
        return super(MayaShotAssetInstanceFramesJsonPublishPlugin, self).validate(settings, item)


    def publish(self, settings, item):

        # Get the asset.
        mayaObject = publihTools.getItemProperty(item, "mayaObject")
        asset = mayaObject.fullname

        # Get every controllers children of the asset. Transforms that ends with _CON.
        controllers = cmds.listRelatives(asset, allDescendents=True, type='transform', fullPath=True)
        controllers = [x for x in controllers if x.endswith('_CON')]

        # Get the keyed frames.
        keyedframes = cmds.keyframe(controllers, query=True, timeChange=True)
        if(keyedframes):
            keyedFrames = list(set(keyedframes))
        # Sort the keyed frames.
        keyedFrames.sort()


        # Get the path to create and publish.
        publish_path = item.properties["path"]

        # Ensure the publish folder exists:
        publish_folder = os.path.dirname(publish_path)
        self.parent.ensure_folder_exists(publish_folder)
        # Write a json file.
        with open(publish_path, 'w') as f:
            json.dump(keyedFrames, f, indent=4)


        # let the base class register the publish
        super(MayaShotAssetInstanceFramesJsonPublishPlugin, self).publish(settings, item)

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
        base_settings = super(MayaShotAssetInstanceFramesJsonPublishPlugin, self).settings or {}

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
        return ["maya.shot.assetInstance.frames.json"]