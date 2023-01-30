import  os
import  hou
import  sgtk

from    tank_vendor import six

# Import the node definition.
from    adamPipe.materialXExportNode    import MaterialXExportNode

# Import the houdini module of the P3D framework.
P3Dfw = sgtk.platform.current_engine().frameworks["tk-framework-P3D"].import_module("houdini")
publihTools = P3Dfw.PublishTools()

HookBaseClass = sgtk.get_hook_baseclass()

class HoudiniAssetMaterialXPublishPlugin(HookBaseClass):

    @property
    def publishTemplate(self):
        return "Asset MaterialX Publish Template"

    @property
    def propertiesPublishTemplate(self):
        return "asset_materialX_publish_template"

    @property
    def description(self):
        return """
        <p>This plugins publishes the MaterialX of an asset for the Lookdev Asset nodes.</p>
        """

    @property
    def settings(self):
        # Inherit the settings from the base publish plugin.
        base_settings = super(HoudiniAssetMaterialXPublishPlugin, self).settings or {}

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
        return ["houdini.asset.materialX"]

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
        # Check if the output path is not empty.
        outputPath = node.parm("materialXFile").eval()
        if(not outputPath):
            accepted = False
            msg = "The output path is empty."
            self.logger.info(msg)

        # Check if the node has the publish template selected for the MaterialX.
        publishMTLXTemplate = settings[self.publishTemplate].value
        selectedMTLXTemplate = node.parm("availablePaths").evalAsString()
        if( selectedMTLXTemplate != publishMTLXTemplate ):
            accepted = False
            msg = "The selected template for the MaterialX export is not the publish template."
            self.logger.info(msg)

        return {"accepted": accepted, "checked": checked}

    def validate(self, settings, item):

        # Check if the node still exists.
        node = item.properties["node"]
        if(not node):
            error = "The node does not exist anymore."
            self.logger.error(error)
            raise Exception(error)

        # Perform the base validation.
        publihTools.hookPublishValidate(
            self,
            settings,
            item,
            self.propertiesPublishTemplate,
            isChild=False,
            addFields={
                'lod'       : node.parm("lod").evalAsString(),
                'variant'   : node.parm('textureName').evalAsString()
            }
        )

        # run the base class validation
        return super(HoudiniAssetMaterialXPublishPlugin, self).validate(settings, item)

    def publish(self, settings, item):

        publisher = self.parent

        # Get the path to create and publish.
        publish_path = item.properties["path"]

        # Ensure the publish folder exists.
        publish_folder = os.path.dirname(publish_path)
        self.parent.ensure_folder_exists(publish_folder)

        # Get the materialX node.
        node = item.properties["node"]
        # Update the output path.
        MaterialXExportNode.setOutputPathField(node)
        # Run the render for the materialX.
        MaterialXExportNode.render(node)

        # Let the base class register the publish.
        super(HoudiniAssetMaterialXPublishPlugin, self).publish(settings, item)

