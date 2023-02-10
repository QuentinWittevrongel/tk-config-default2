import  os
import  hou
import  sgtk

from    tank_vendor import six

# Import the node definition.
from    adamPipe.lookdevAssetNode       import LookdevAssetNode

# Import the houdini module of the P3D framework.
P3Dfw = sgtk.platform.current_engine().frameworks["tk-framework-P3D"].import_module("houdini")
publihTools = P3Dfw.PublishTools()

HookBaseClass = sgtk.get_hook_baseclass()

class HoudiniSelectionHdaPublishPlugin(HookBaseClass):

    @property
    def publishTemplate(self):
        return "Publish Template"

    @property
    def propertiesPublishTemplate(self):
        return "publish_template"

    @property
    def description(self):
        return """
        <p>This plugin publishs the selected digital asset.</p>
        """

    @property
    def settings(self):
        # Inherit the settings from the base publish plugin.
        base_settings = super(HoudiniSelectionHdaPublishPlugin, self).settings or {}

        # Settings specific to this class
        houdini_publish_settings = {
            self.publishTemplate: {
                "type"          : "template",
                "default"       : None,
                "description"   : "Template path for published work files. Should"
                "correspond to a template defined in "
                "templates.yml.",
            }
        }

        # Update the base settings
        base_settings.update(houdini_publish_settings)

        return base_settings

    @property
    def item_filters(self):
        return ["houdini.selection.hda.node"]

    def accept(self, settings, item):

        # Perform the base accept method.
        status = publihTools.hookPublishAccept(
            self,
            settings,
            item,
            self.publishTemplate,
            self.propertiesPublishTemplate
        )
        accepted = status['accepted']
        checked = status['checked']

        # Get the node.
        node = item.properties["node"]

        # Check if the node is a digital asset.
        nodeDefinition = node.type().definition()
        if(not nodeDefinition):
            errorMsg = "The node is not a digital asset."
            self.logger.info(errorMsg)
            accepted = False


        return {"accepted": accepted, "checked": checked}

    def validate(self, settings, item):

        # Check if the node still exists.
        node = item.properties["node"]
        if(not node):
            error = "The node does not exist anymore."
            self.logger.error(error)
            raise Exception(error)

        # Get the asset name.
        assetName = node.type().name()
        # Get the name out of it.
        nodeName = assetName.split('_')[-1]
        # Split the node name and the version.
        nodeName, nodeVersion = nodeName.split('.v')

        # Perform the base validation.
        publihTools.hookPublishValidate(
            self,
            settings,
            item,
            self.propertiesPublishTemplate,
            isChild=False,
            addFields = {"node" : nodeName}
        )

        # Override the publish type using the category.
        category = node.type().category().name()
        if(category == 'Object'):
            item.properties["publish_type"] = "Houdini Object HDA"

        # Run the base class validation.
        return super(HoudiniSelectionHdaPublishPlugin, self).validate(settings, item)

    def publish(self, settings, item):

        # Perform the digital asset export.
        publihTools.hookPublishDigitalAssetPublish(
            self,
            settings,
            item,
        )

        # Let the base class register the geometry publish.
        super(HoudiniSelectionHdaPublishPlugin, self).publish(settings, item)

