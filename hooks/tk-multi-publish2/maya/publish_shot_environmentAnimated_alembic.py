
import os
import maya.cmds as cmds
import maya.mel as mel
import sgtk

from tank_vendor import six

# Import the maya module of the P3D framework.
P3Dfw = sgtk.platform.current_engine().frameworks["tk-framework-P3D"].import_module("maya")
publihTools = P3Dfw.PublishTools()

HookBaseClass = sgtk.get_hook_baseclass()

class MayaShotEnvironmentAnimatedAlembicPublishPlugin(HookBaseClass):

    def accept(self, settings, item):

        self.logger.info("Shot Environment Alembic Publish | accept")

        return publihTools.hookPublishAccept(
            self,
            settings,
            item,
            self.publishTemplate,
            self.propertiesPublishTemplate,
            isChild=True
        )

    def validate(self, settings, item):

        self.logger.info("Shot Environment Alembic Publish | validate")

        mayaObject = publihTools.getItemProperty(item, "mayaObject")
        self.logger.debug("mayaObject: {}".format(mayaObject))

        publihTools.hookPublishValidateMayaObject(
            self,
            settings,
            item,
            self.propertiesPublishTemplate,
            addFields={
                "Asset" : mayaObject.name
            }
        )

        # Get the animated assets in the properties.
        animatedAssets = publihTools.getItemProperty(item, "animatedAssets")
        # Check if the animated assets exists.
        for asset in animatedAssets:
            if( not cmds.objExists(asset.fullname) ):
                errorMsg = "The asset {} does not exist.".format(asset.fullname)
                self.logger.error(errorMsg)
                raise Exception(errorMsg)

        # Override the publish type.
        item.properties["publish_type"] = "Alembic Environment"

        # run the base class validation
        return super(MayaShotEnvironmentAnimatedAlembicPublishPlugin, self).validate(settings, item)

    def publish(self, settings, item):

        self.logger.info("Shot Environment Alembic Publish | publish")

        publihTools.hookPublishAlembicAnimationEnvironmentPublish(
            self,
            settings,
            item,
            useFrameRange=True
        )

        # let the base class register the publish
        super(MayaShotEnvironmentAnimatedAlembicPublishPlugin, self).publish(settings, item)

    @property
    def publishTemplate(self):
        return "Publish Template"

    @property
    def propertiesPublishTemplate(self):
        return "publish_template"

    @property
    def description(self):
        return """
        <p>This plugin publish the assets that are not deformed and that are animated in an environment.
        A keyframe is needed to tag the asset as animated.
        You need to select root transform of the environment.</p>
        """

    @property
    def settings(self):
        # inherit the settings from the base publish plugin
        base_settings = super(MayaShotEnvironmentAnimatedAlembicPublishPlugin, self).settings or {}

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
        return ["maya.shot.environmentAnimated.abc"]