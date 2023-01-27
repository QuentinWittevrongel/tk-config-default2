import  os
import  hou
import  sgtk

from    tank_vendor import six

# Import the node definitions.
from    adamPipe.lookdevAssetNode       import LookdevAssetNode
from    adamPipe.materialXExportNode    import MaterialXExportNode

# Import the houdini module of the P3D framework.
P3Dfw = sgtk.platform.current_engine().frameworks["tk-framework-P3D"].import_module("houdini")
publihTools = P3Dfw.PublishTools()

HookBaseClass = sgtk.get_hook_baseclass()

class HoudiniAssetLookdevPublishPlugin(HookBaseClass):

    @property
    def publishTemplate(self):
        return "Asset Geo Publish Template"

    @property
    def propertiesPublishTemplate(self):
        return "publish_template"

    @property
    def description(self):
        return """
        <p>This plugin publishes the lookdev from the LookdevAsset nodes present in the scene.</p>
        """

    @property
    def settings(self):
        # Inherit the settings from the base publish plugin.
        base_settings = super(HoudiniAssetLookdevPublishPlugin, self).settings or {}

        # Settings specific to this class
        houdini_publish_settings = {
            "Asset Geo Publish Template": {
                "type"          : "template",
                "default"       : None,
                "description"   : "Template path for published work files. Should"
                "correspond to a template defined in "
                "templates.yml.",
            },
            "Asset MaterialX Publish Template": {
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
        return ["houdini.asset.lookdev.node"]

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
        publishGEOTemplate = settings["Asset Geo Publish Template"].value
        selectedGEOTemplate = node.parm(LookdevAssetNode.AVAILABLEPATHS_MENU_NAME).evalAsString()
        if( selectedGEOTemplate != publishGEOTemplate ):
            accepted = False
            msg = "The selected template for the geometry export is not the publish template."
            self.logger.info(msg)

        # Check if the node has the publish template selected for the MaterialX.
        materialXNode = LookdevAssetNode.getMaterialXExportNode(node)
        publishMTLXTemplate = settings["Asset MaterialX Publish Template"].value
        selectedMTLXTemplate = materialXNode.parm("availablePaths").evalAsString()
        if( selectedMTLXTemplate != publishMTLXTemplate ):
            accepted = False
            msg = "The selected template for the material x export is not the publish template."
            self.logger.info(msg)

        return {"accepted": accepted, "checked": checked}

    def validate(self, settings, item):

        # Check if the node still exists.
        node = item.properties["node"]
        if(not node):
            error = "The node does not exist anymore."
            self.logger.error(error)
            raise Exception(error)

        # Check if a geometry is defined in the node.
        geoPath = node.parm(LookdevAssetNode.EXPORTFILE_NAME).evalAsString()
        if(not geoPath):
            error = "The geometry path is not defined."
            self.logger.error(error)
            raise Exception(error)

        # Check if the node has the publish template selected for the Geometry.
        publishGEOTemplate = settings["Asset Geo Publish Template"].value
        selectedGEOTemplate = node.parm(LookdevAssetNode.AVAILABLEPATHS_MENU_NAME).evalAsString()
        if( selectedGEOTemplate != publishGEOTemplate ):
            error = "The selected template for the geometry export is not the publish template."
            self.logger.error(error)
            raise Exception(error)

        # Check if the node has the publish template selected for the MaterialX.
        materialXNode = LookdevAssetNode.getMaterialXExportNode(node)
        publishMTLXTemplate = settings["Asset MaterialX Publish Template"].value
        selectedMTLXTemplate = materialXNode.parm("availablePaths").evalAsString()
        if( selectedMTLXTemplate != publishMTLXTemplate ):
            error = "The selected template for the material x export is not the publish template."
            self.logger.error(error)
            raise Exception(error)

        # Perform the base validation.
        publihTools.hookPublishValidate(
            self,
            settings,
            item,
            self.propertiesPublishTemplate,
            isChild=False
        )

        # Override the publish type.
        item.properties["publish_type"] = "Asset Buffers"

        # Run the base class validation.
        return super(HoudiniAssetLookdevPublishPlugin, self).validate(settings, item)

    def publish(self, settings, item):

        publisher = self.parent

        # Get the path to create and publish.
        publish_path = item.properties["path"]

        # Ensure the publish folder exists.
        publish_folder = os.path.dirname(publish_path)
        self.parent.ensure_folder_exists(publish_folder)

        # Get the node.
        node = item.properties["node"]
        # Get the materialX node.
        materialXNode = LookdevAssetNode.getMaterialXExportNode(node)
        # Update the output path.
        MaterialXExportNode.setOutputPathField(materialXNode)
        # Run the render for the materialX.
        MaterialXExportNode.render(materialXNode)

        # Update the geometry path.
        LookdevAssetNode.setOutputPathField(node)
        # Get the export geometry node.
        exportGeoNode = LookdevAssetNode.getAssetInstanceExportNode(node)
        # Run the render for the geometry.
        exportGeoNode.render()

        # Get the asset name from the context.
        currentEngine = sgtk.platform.current_engine()
        currentContext = currentEngine.context
        ctxtEntity = currentContext.entity
        assetName = ctxtEntity["name"]
        item.properties["publish_name"] = assetName + '_buffers'

        # Let the base class register the geometry publish.
        super(HoudiniAssetLookdevPublishPlugin, self).publish(settings, item)





        # Also register the materialX publish.

        # Ensure the publish template is defined and valid and that we also have
        publish_template = publisher.get_template_by_name( settings["Asset MaterialX Publish Template"].value )

        # Get the materialX publish path.
        mtlxPath = materialXNode.parm("materialXFile").evalAsString()

        publish_data = {
            "tk": publisher.sgtk,
            "context": item.context,
            "comment": item.description,
            "path": publish_path,
            "name": os.path.basename(mtlxPath),
            "version_number": item.properties["publish_version"],
            "thumbnail_path": item.get_thumbnail_as_path(),
            "published_file_type": "Mtlx File",
            "dependency_paths": [],
        }
        sgtk.util.register_publish(**publish_data)

def _save_session(path):
    """
    Save the current session to the supplied path.
    """
    # We need to flip the slashes on Windows to avoid a bug in Houdini. If we don't
    # the next Save As dialog will have the filename box populated with the complete
    # file path.
    sanitized_path = six.ensure_str(path.replace("\\", "/"))
    hou.hipFile.save(file_name=sanitized_path)


def _session_path():
    """
    Return the path to the current session
    :return:
    """

    # Houdini always returns a file path, even for new sessions. We key off the
    # houdini standard of "untitled.hip" to indicate that the file has not been
    # saved.
    if hou.hipFile.name() == "untitled.hip":
        return None

    return hou.hipFile.path()


def _get_save_as_action():
    """
    Simple helper for returning a log action dict for saving the session
    """

    engine = sgtk.platform.current_engine()

    # default save callback
    callback = engine.save_as

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
