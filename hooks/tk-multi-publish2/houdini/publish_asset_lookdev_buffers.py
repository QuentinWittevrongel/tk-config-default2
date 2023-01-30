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

class HoudiniAssetLookdevBuffersPublishPlugin(HookBaseClass):

    @property
    def publishTemplate(self):
        return "Asset Geo Publish Template"

    @property
    def propertiesPublishTemplate(self):
        return "publish_template"

    @property
    def description(self):
        return """
        <p>This plugin publishes the resolution buffers of an asset for the Lookdev Asset nodes.</p>
        """

    @property
    def settings(self):
        # Inherit the settings from the base publish plugin.
        base_settings = super(HoudiniAssetLookdevBuffersPublishPlugin, self).settings or {}

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
        return ["houdini.asset.lookdev.buffers"]

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

        # Check if the node has the publish template selected for the Geometry.
        publishGEOTemplate = settings[self.publishTemplate].value
        selectedGEOTemplate = node.parm(LookdevAssetNode.AVAILABLEPATHS_MENU_NAME).evalAsString()
        if( selectedGEOTemplate != publishGEOTemplate ):
            accepted = False
            msg = "The selected template for the geometry export is not the publish template."
            self.logger.info(msg)

        return {"accepted": accepted, "checked": checked}

    def validate(self, settings, item):

        # Check if the node still exists.
        node = item.properties["node"]
        if(not node):
            error = "The node does not exist anymore."
            self.logger.error(error)
            raise Exception(error)

        # Check if the node has the publish template selected for the Geometry.
        publishGEOTemplate = settings["Asset Geo Publish Template"].value
        selectedGEOTemplate = node.parm(LookdevAssetNode.AVAILABLEPATHS_MENU_NAME).evalAsString()
        if( selectedGEOTemplate != publishGEOTemplate ):
            error = "The selected template for the geometry export is not the publish template."
            self.logger.error(error)
            raise Exception(error)

        # Get the resolution.
        resolution = item.properties["resolution"]
        if(resolution == ""):
            error = "The resolution is not defined."
            self.logger.error(error)
            raise Exception(error)

        # Get the operator path.
        operatorPath = item.properties["operatorPath"]
        if(operatorPath == ""):
            error = "The operator path is not defined."
            self.logger.error(error)
            raise Exception(error)

        # Perform the base validation.
        publihTools.hookPublishValidate(
            self,
            settings,
            item,
            self.propertiesPublishTemplate,
            isChild=False,
            addFields={'lod' : item.properties["resolution"]}
        )

        # Override the publish type.
        item.properties["publish_type"] = "Asset Buffers"

        # Run the base class validation.
        return super(HoudiniAssetLookdevBuffersPublishPlugin, self).validate(settings, item)

    def publish(self, settings, item):

        publisher = self.parent

        # Get the path to create and publish.
        publish_path = item.properties["path"]

        # Ensure the publish folder exists.
        publish_folder = os.path.dirname(publish_path)
        self.parent.ensure_folder_exists(publish_folder)

        # Get the node.
        node = item.properties["node"]

        # Switch to the correct resolution.
        self.logger.debug("Switching to the resolution: {}".format(item.properties["resolutionIndex"] + 1))
        resolution = item.properties["resolution"]
        LookdevAssetNode.selectResolution(node, item.properties["resolutionIndex"] + 1)

        # Update the geometry path.
        LookdevAssetNode.setOutputPathField(node)
        # Get the export geometry node.
        exportGeoNode = LookdevAssetNode.getAssetInstanceExportNode(node)
        # Run the render for the geometry.
        exportGeoNode.render()

        # Get the asset name from the context.
        currentEngine   = sgtk.platform.current_engine()
        currentContext  = currentEngine.context
        ctxtEntity      = currentContext.entity
        assetName       = ctxtEntity["name"]
        item.properties["publish_name"] = '{}_{}_buffers'.format(assetName, resolution)

        # Let the base class register the geometry publish.
        super(HoudiniAssetLookdevBuffersPublishPlugin, self).publish(settings, item)

