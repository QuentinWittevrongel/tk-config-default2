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

class HoudiniSequenceSetDressingPublishPlugin(HookBaseClass):

    @property
    def publishTemplate(self):
        return "Publish Template"

    @property
    def propertiesPublishTemplate(self):
        return "publish_template"

    @property
    def description(self):
        return """
        <p>This plugin publishs the digital asset for the set dressing.</p>
        """

    @property
    def settings(self):
        # Inherit the settings from the base publish plugin.
        base_settings = super(HoudiniSequenceSetDressingPublishPlugin, self).settings or {}

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
        return ["houdini.sequence.setDressing.node"]

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

        # Extract the node name.
        fullName = node.name()
        name = fullName.split("_")[-2]

        # Perform the base validation.
        publihTools.hookPublishValidate(
            self,
            settings,
            item,
            self.propertiesPublishTemplate,
            isChild=False,
            addFields = {"node" : name}
        )

        # Run the base class validation.
        return super(HoudiniSequenceSetDressingPublishPlugin, self).validate(settings, item)

    def publish(self, settings, item):

        # Perform the digital asset export.
        publihTools.hookPublishDigitalAssetPublish(
            self,
            settings,
            item,
        )

        # Let the base class register the geometry publish.
        super(HoudiniSequenceSetDressingPublishPlugin, self).publish(settings, item)

