import  os
import  hou
import  sgtk

from    tank_vendor import six

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
        <p>This plugin publishes the materialX from the MaterialXExport nodes present in the scene.</p>
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

        # Check if the node has the publish template selected.
        selectedTemplate = node.parm('availablePaths').evalAsString()
        if( selectedTemplate != item.properties.get(self.propertiesPublishTemplate).name ):
            accepted = False
            msg = "The selected template is not the publish template."
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

        # Perform the base publish.
        publihTools.hookPublishMaterialXPublish(
            self,
            settings,
            item,
            isChild=False
        )

        # Let the base class register the publish.
        super(HoudiniAssetMaterialXPublishPlugin, self).publish(settings, item)


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
