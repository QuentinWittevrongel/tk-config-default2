
import os
import maya.cmds as cmds
import maya.mel as mel
import sgtk

from tank_vendor import six

# Import the maya module of the P3D framework.
P3Dfw = sgtk.platform.current_engine().frameworks["tk-framework-P3D"].import_module("maya")
publihTools = P3Dfw.PublishTools()

HookBaseClass = sgtk.get_hook_baseclass()

class MayaSelectionAlembicPublishPlugin(HookBaseClass):

    def accept(self, settings, item):

        return publihTools.hookPublishAccept(
            self,
            settings,
            item,
            self.publishTemplate,
            self.propertiesPublishTemplate
        )
    def validate(self, settings, item):

        # Get the selection from the item.
        selection = item.parent.properties.get("selection")

        # Check if the selection still exists.
        for obj in selection:
            if(not cmds.objExists(obj)):
                errorMsg = "The object {} does not exist.".format(obj)
                self.logger.error(errorMsg)
                raise Exception(errorMsg)

        publihTools.addPublishDatasToPublishItem(
            self,
            item,
            self.propertiesPublishTemplate
        )

        # run the base class validation
        return super(MayaSelectionAlembicPublishPlugin, self).validate(settings, item)

    def publish(self, settings, item):

        # Get the selection from the item.
        selection = item.parent.properties.get("selection")

        # Get the path.
        publish_path = item.properties.get("path")

        # Ensure the publish folder exists.
        publish_folder = os.path.dirname(publish_path)
        self.parent.ensure_folder_exists(publish_folder)

        # Export the alembic.
        publihTools.exportAlembic(
            selection,
            1,
            1,
            publish_path,
            exportABCVersion    = 2,
            spaceType           = "local"
        )

        # Let the base class register the publish
        super(MayaSelectionAlembicPublishPlugin, self).publish(settings, item)

    @property
    def publishTemplate(self):
        return "Selection Alembic Publish Template"

    @property
    def propertiesPublishTemplate(self):
        return "selection_alembic_publish_template"

    @property
    def description(self):
        return """
        <p>This plugin publish the selected assets for the model pipeline step
        You need to select root transform of the asset.</p>
        """

    @property
    def settings(self):
        # inherit the settings from the base publish plugin
        base_settings = super(MayaSelectionAlembicPublishPlugin, self).settings or {}

        # settings specific to this class
        maya_publish_settings = {
            self.publishTemplate: {
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
        return ["maya.selection.abc"]

def _session_path():
    """
    Return the path to the current session
    :return:
    """
    path = cmds.file(query=True, sn=True)

    if path is not None:
        path = six.ensure_str(path)

    return path


def _get_save_as_action():
    """
    Simple helper for returning a log action dict for saving the session
    """

    engine = sgtk.platform.current_engine()

    # default save callback
    callback = cmds.SaveScene

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