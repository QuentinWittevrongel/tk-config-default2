
import  os
import  maya.cmds       as      cmds
import  maya.mel        as      mel
import  sgtk

from    tank_vendor     import  six

# Import the maya module of the P3D framework.
P3Dfw = sgtk.platform.current_engine().frameworks["tk-framework-P3D"].import_module("maya")
publihTools = P3Dfw.PublishTools()

HookBaseClass = sgtk.get_hook_baseclass()

class MayaCameraAlembicPublishPlugin(HookBaseClass):

    def accept(self, settings, item):

        return publihTools.hookPublishAccept(
            self,
            settings,
            item,
            self.publishTemplate,
            self.propertiesPublishTemplate
        )

    def validate(self, settings, item):

        # Get the root of the camera.
        cameraRoot = item.parent.properties.get("cameraRoot")
        # Check if the camera root exists.
        if(not cmds.objExists(cameraRoot)):
            errorMsg = "The camera {} does not exist.".format(cameraRoot)
            self.logger.error(errorMsg)
            raise Exception(errorMsg)

        # Get the number of camera in the camera depedencies.
        cameraShapes = cmds.listRelatives(cameraRoot, allDescendents=True, type="camera", fullPath=True)
        if( len(cameraShapes) == 0 ):
            errorMsg = "The group must contain at least one camera."
            self.logger.error(errorMsg)
            raise Exception(errorMsg)

        # Get the parent of the camera shape.
        cameraParents = cmds.listRelatives(cameraShapes, parent=True, fullPath=True)
        for cameraParent in cameraParents:
            # Check if the frameRange attribute exists.
            if(not cmds.attributeQuery("frameRange", node=cameraParent, exists=True)):
                errorMsg = "The camera {} does not have a frameRange attribute.".format(cameraParent)
                self.logger.error(errorMsg)
                raise Exception(errorMsg)

        # Get the sequence qnd shot name from the camera root name.
        cameraRootShort     = cameraRoot.split("|")[-1].split(":")[-1]
        cameraRootSplit     = cameraRootShort.split("_")
        sequenceName        = cameraRootSplit[0]
        shotName            = cameraRootSplit[1]

        publihTools.addPublishDatasToPublishItem(
            self,
            item,
            self.propertiesPublishTemplate,
            addFields   = {
                'Sequence'  : sequenceName,
                'Shot'      : shotName
            }
        )

        # Run the base class validation
        return super(MayaCameraAlembicPublishPlugin, self).validate(settings, item)

    def publish(self, settings, item):

        # Get the root of the camera.
        cameraRoot = item.parent.properties.get("cameraRoot")

        # Get the camera shapes.
        cameraShapes = cmds.listRelatives(cameraRoot, allDescendents=True, type="camera", fullPath=True)
        # Get the parent of the camera shape.
        cameraParents = cmds.listRelatives(cameraShapes, parent=True, fullPath=True)

        # Get the path.
        publish_path = item.properties.get("path")

        # Ensure the publish folder exists.
        publish_folder = os.path.dirname(publish_path)
        self.parent.ensure_folder_exists(publish_folder)

        # Get the framerange attribute of the camera.
        maxFrameRange = 0
        for cameraParent in cameraParents:
            maxFrameRange = max(maxFrameRange, cmds.getAttr(cameraParent + ".frameRange"))

        # Export the alembic.
        publihTools.exportAlembic(
            cameraParents,
            1001 - 24,
            1001 + maxFrameRange - 1 + 24,
            publish_path,
            exportABCVersion    = 1,
            spaceType           = "world"
        )

        # Let the base class register the publish
        super(MayaCameraAlembicPublishPlugin, self).publish(settings, item)

    def finalize(self, settings, item):

        # Get the playblast file.
        publish_path = item.parent.properties.get("playBlastFile")
        # Delete the playblast file if exists.
        if(publish_path and os.path.exists(publish_path)):
            os.remove(publish_path)

        # Run the base class finalize
        super(MayaCameraAlembicPublishPlugin, self).finalize(settings, item)

    @property
    def publishTemplate(self):
        return "Camera Alembic Publish Template"

    @property
    def propertiesPublishTemplate(self):
        return "camera_alembic_publish_template"

    @property
    def description(self):
        return """
        <p>This plugin publish the selected cameras.
        You need to select root transform of the cameras.</p>
        """

    @property
    def settings(self):
        # inherit the settings from the base publish plugin
        base_settings = super(MayaCameraAlembicPublishPlugin, self).settings or {}

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
        return ["maya.camera.abc"]

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