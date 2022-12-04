"""
Need to add the hook python file in the config.env.includes.settings.tk-multi-publish2.yml
"""


import os
import sgtk
import inspect

from tank_vendor import six

# Import the houdini module of the P3D framework.
P3Dfw = sgtk.platform.current_engine().frameworks["tk-framework-P3D"].import_module("houdini")
publihTools = P3Dfw.PublishTools()

# Inherit from {self}/publish_file.py 
# Check config.env.includes.settings.tk-multi-publish2.yml
HookBaseClass = sgtk.get_hook_baseclass()


class HoudiniPlayblastReviewPlugin(HookBaseClass):
    ''' Plugin for sending maya playblast to shotgrid for review.
    Without creating a publish file.'''

    def accept(self, settings, item):

        self.logger.info("Playblast Review | accept")

        accepted = True

        # because a publish template is configured, disable context change. This
        # is a temporary measure until the publisher handles context switching
        # natively.
        item.context_change_allowed = False
        # Get the file path to the review file.
        filePath = item.properties.get("path")


        return {"accepted": accepted, "checked": True}

    def validate(self, settings, item):

        publihTools.hookUploadReviewValidate(
            self,
            settings,
            item
        )

        # Run the base class validation
        return super(HoudiniPlayblastReviewPlugin, self).validate(settings, item)

    def publish(self, settings, item):

        publihTools.hookUploadReviewPublish(
            self,
            settings,
            item
        )

    def finalize(self, settings, item):
        ''' Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        Args:
            settings    (:class:`PluginSetting`)    : The settings for the plugin.
            item        (:class:`PublishItem`)      : The item to process.
        # '''
        publihTools.hookUploadReviewFinalize(
            self,
            settings,
            item
        )

    @property
    def icon(self):
        # Look for icon one level up from this hook's folder in "icons" folder.
        return os.path.join(self.disk_location, "icons", "review.png")

    @property
    def description(self):
        return """
        <p>This plugin create a version for the selected playblast.</p>
        """

    @property
    def settings(self):
        return {}

    @property
    def item_filters(self):
        return ["houdini.playblast.review"]

    def _getVersionEntity(self, item):
        ''' Returns the best entity to link the version to. '''
        if item.context.entity:
            return item.context.entity
        elif item.context.project:
            return item.context.project
        else:
            return None