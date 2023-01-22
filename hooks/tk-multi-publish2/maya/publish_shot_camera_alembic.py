
import  os
import  maya.cmds       as      cmds
import  maya.mel        as      mel
import  sgtk

from    tank_vendor     import  six

# Import the maya module of the P3D framework.
P3Dfw = sgtk.platform.current_engine().frameworks["tk-framework-P3D"].import_module("maya")
publihTools = P3Dfw.PublishTools()

HookBaseClass = sgtk.get_hook_baseclass()

class MayaShotCameraAlembicPublishPlugin(HookBaseClass):

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
        if( len(cameraShapes) != 1 ):
            errorMsg = "The group must contain only one camera."
            self.logger.error(errorMsg)
            raise Exception(errorMsg)

        publihTools.addPublishDatasToPublishItem(
            self,
            item,
            self.propertiesPublishTemplate
        )

        # Override the publish type.
        item.properties["publish_type"] = "Alembic Camera"

        # Run the base class validation
        return super(MayaShotCameraAlembicPublishPlugin, self).validate(settings, item)

    def publish(self, settings, item):

        # Get the root of the camera.
        cameraRoot = item.parent.properties.get("cameraRoot")

        # Get the camera shape.
        cameraShape = cmds.listRelatives(cameraRoot, allDescendents=True, type="camera", fullPath=True)[0]
        # Get the parent of the camera shape.
        cameraParent = cmds.listRelatives(cameraShape, parent=True, fullPath=True)[0]

        # Get the path.
        publish_path = item.properties.get("path")

        # Ensure the publish folder exists.
        publish_folder = os.path.dirname(publish_path)
        self.parent.ensure_folder_exists(publish_folder)

        # Get the scene start and end frame.
        startFrame, endFrame = publihTools.getSceneFrameRange()

        # Export the alembic.
        publihTools.exportAlembic(
            [cameraParent],
            startFrame,
            endFrame,
            publish_path,
            exportABCVersion    = 1,
            spaceType           = "world"
        )

        # Let the base class register the publish
        super(MayaShotCameraAlembicPublishPlugin, self).publish(settings, item)

    @property
    def publishTemplate(self):
        return "Publish Template"

    @property
    def propertiesPublishTemplate(self):
        return "publish_template"

    @property
    def description(self):
        return """
        <p>This plugin publish the selected cameras.
        You need to select root transform of the cameras.</p>
        """

    @property
    def settings(self):
        # inherit the settings from the base publish plugin
        base_settings = super(MayaShotCameraAlembicPublishPlugin, self).settings or {}

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
        return ["maya.shot.camera.abc"]