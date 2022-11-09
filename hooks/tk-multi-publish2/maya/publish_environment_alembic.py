
import os
import maya.cmds as cmds
import maya.mel as mel
import sgtk

from tank_vendor import six

# Import the maya module of the P3D framework.
P3Dfw = sgtk.platform.current_engine().frameworks["tk-framework-P3D"].import_module("maya")
publihTools = P3Dfw.PublishTools()

HookBaseClass = sgtk.get_hook_baseclass()

class MayaEnvironmentAlembicPublishPlugin(HookBaseClass):

    def accept(self, settings, item):

        self.logger.info("Environment Alembic Publish | accept")

        accepted = True
        # Get the publish plugin publish template.
        # This template is assgin in config.env.includes.settings.tk-multi-publish2.yml
        template_name = settings[self.publishTemplate].value
        # Check if the template is valid.
        accepted, publish_template = publihTools.checkPublishTemplate(self, template_name)
        # we've validated the publish template. add it to the item properties
        # for use in subsequent methods
        item.properties[self.propertiesPublishTemplate] = publish_template
        # because a publish template is configured, disable context change. This
        # is a temporary measure until the publisher handles context switching
        # natively.
        item.context_change_allowed = False

        return {"accepted": accepted, "checked": True}

    def validate(self, settings, item):

        self.logger.info("Environment Alembic Publish | validate")

        # Check if the environment is valid.
        mayaObject = item.parent.properties["assetObject"]
        if(not cmds.objExists(mayaObject)):
            error_msg = "The environment {} is not a valid.".format(mayaObject)
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
        # Add the publish path datas to the publish item.
        # That allow us to reuse the datas for the publish.
        publihTools.addPublishDatasToPublishItem(self, item, self.propertiesPublishTemplate)

        # run the base class validation
        return super(MayaEnvironmentAlembicPublishPlugin, self).validate(settings, item)

    def publish(self, settings, item):

        self.logger.info("Environment Publish | publish")

        publisher = self.parent

        # Get the environment.
        mayaObject = item.properties["assetObject"]

        # get the path to create and publish
        publish_path = item.properties["path"]

        # ensure the publish folder exists:
        publish_folder = os.path.dirname(publish_path)
        self.parent.ensure_folder_exists(publish_folder)

        # Get the MI meshes from the maya asset.
        meshes = mayaObject

        # Export the alembic.
        publihTools.exportAlembic(
            meshes,
            1,
            1,
            publish_path,
            exportABCVersion=2,
            spaceType="local")

        # let the base class register the publish
        super(MayaEnvironmentAlembicPublishPlugin, self).publish(settings, item)

    @property
    def publishTemplate(self):
        return "Environment Alembic Publish Template"

    @property
    def propertiesPublishTemplate(self):
        return "environment_alembic_publish_template"

    @property
    def description(self):
        return """
        <p>This plugin publish the environment for the rig pipeline step
        This will find all the root transforms which finished by _ENV.</p>
        """

    @property
    def settings(self):
        # inherit the settings from the base publish plugin
        base_settings = super(MayaEnvironmentAlembicPublishPlugin, self).settings or {}

        # settings specific to this class
        maya_publish_settings = {
            self.publishTemplate : {
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
        return ["maya.environment.alembic"]

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