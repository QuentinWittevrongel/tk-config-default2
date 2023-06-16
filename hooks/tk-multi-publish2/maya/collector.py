# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import  glob
import  os
import  re
from    maya                import  cmds, utils
import  maya.mel            as      mel
import  sgtk
import  tempfile
from    sgtk.platform.qt    import  QtCore, QtGui

HookBaseClass = sgtk.get_hook_baseclass()

# Import the maya module of the P3D framework.
P3Dfw = sgtk.platform.current_engine().frameworks["tk-framework-P3D"].import_module("maya")

class MayaSessionCollector(HookBaseClass):
    """
    Collector that operates on the maya session. Should inherit from the basic
    collector hook.
    """

    @property
    def settings(self):
        """
        Dictionary defining the settings that this collector expects to receive
        through the settings parameter in the process_current_session and
        process_file methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """
        return {
            "Work Template": {
                "type": "template",
                "default": None,
                "description": "Template path for artist work files. Should "
                "correspond to a template defined in "
                "templates.yml. If configured, is made available"
                "to publish plugins via the collected item's "
                "properties. ",
            },
        }

    def process_current_session(self, settings, parent_item):
        """
        Analyzes the current session open in Maya and parents a subtree of
        items under the parent_item passed in.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance

        """
        # Get the current engine.
        currentEngine = sgtk.platform.current_engine()
        # Get the current context.
        currentContext = currentEngine.context
        # Get the context project.
        ctxtProject = currentContext.project
        # Get the context step.
        ctxtStep = currentContext.step
        # Get the context entity.
        ctxtEntity = currentContext.entity
        # Get the context task.
        ctxtTask = currentContext.task
        # Get the context user.
        ctxtUser = currentContext.user

        if(ctxtEntity["type"] == "Asset"):

            # Collect all the playblasts for review.
            self.collect_review(parent_item, currentContext)

            # Create an item representing the scene.
            sceneItem = self.collect_scene(settings, parent_item)

            # Set the P3D publish pipeline.
            if(ctxtStep["name"] == "Model" or
                ctxtStep["name"] == "UV"):

                # Collect the data for a Model Publish.
                self.collect_for_model_publish(settings, sceneItem)

            elif(ctxtStep["name"] == "Rig"):

                if(ctxtTask["name"] == "Scene Description"):
                    self.collect_for_env_publish(settings, sceneItem)
                
                else:
                    self.collect_for_rig_publish(settings, sceneItem)

            # elif(ctxtStep["name"] == "Shading"):
            #     self.collect_for_shd_publish(settings, parent_item)

        elif(ctxtEntity["type"] == "Sequence"):

            # Create an item representing the scene.
            sceneItem = self.collect_scene(settings, parent_item)

            if(ctxtStep["name"] == "Set Dress (Seq)"):
                self.collect_for_sequence_setDress_publish(settings, sceneItem)

        elif(ctxtEntity["type"] == "Shot"):

            # Create an item representing the scene.
            sceneItem = self.collect_scene(settings, parent_item)

            if(ctxtStep["name"] == "Animation"):
                self.collect_for_shot_animation_publish(settings, sceneItem)

        elif(ctxtEntity["type"] == "CustomEntity03"):

            self.collect_selection(settings, sceneItem)

        else:

            # create an item representing the current maya session
            item = self.collect_current_maya_session(settings, parent_item)
            project_root = item.properties["project_root"]

            # look at the render layers to find rendered images on disk
            self.collect_rendered_images(item)

            # if we can determine a project root, collect other files to publish
            if project_root:

                self.logger.info(
                    "Current Maya project is: %s." % (project_root,),
                    extra={
                        "action_button": {
                            "label": "Change Project",
                            "tooltip": "Change to a different Maya project",
                            "callback": lambda: mel.eval('setProject ""'),
                        }
                    },
                )

                self.collect_playblasts(item, project_root)
                self.collect_alembic_caches(item, project_root)
            else:

                self.logger.info(
                    "Could not determine the current Maya project.",
                    extra={
                        "action_button": {
                            "label": "Set Project",
                            "tooltip": "Set the Maya project",
                            "callback": lambda: mel.eval('setProject ""'),
                        }
                    },
                )

            if cmds.ls(geometry=True, noIntermediate=True):
                self._collect_session_geometry(item)

# COLLECT BY STEP FUNCTIONS.

    def collect_for_model_publish(self, settings, parent_item):
        ''' Create an item representing the current selection for the MDL pipeline step.

        Args:
            setting         (dict)      : Configured settings for this collector
            parent_item     (sgItemUI)  : Root item instance
        '''
        # Get the selection.
        mSelection = cmds.ls(sl=True, long=True, type="transform")

        # Loop over the selection and check the end tag.
        for transform in mSelection:

            # Check the end tag and create the corresponding item.
            if(self.check_end_tag(transform, 'RIG')):
                # Create the asset publish item.
                self.collect_asset(settings, parent_item, transform)

            # elif(self.check_end_tag(transform, 'SCULPT')):
            #     # Create the sculpt publish item.
            #     self.collect_sculpt(settings, parent_item, transform)

            else:
                # Create a default publish item.
                pass

    def collect_for_rig_publish(self, settings, parent_item):
        ''' Create an item representing the current selection for the RIG pipeline step.

        Args:
            setting         (dict)      : Configured settings for this collector
            parent_item     (sgItemUI)  : Root item instance
        '''
        # Get the selection.
        mSelection = cmds.ls(sl=True, long=True, type="transform")

        # Loop over the selection and check the end tag.
        for transform in mSelection:
            # Check the end tag and create the corresponding item.
            if(self.check_end_tag(transform, 'RIG')):
                # Create the asset publish item.
                self.collect_asset_rig(settings, parent_item, transform)

    def collect_for_shd_publish(self, settings, parent_item):
        ''' Create an item represents the current selected asset shd.

        Args:
            setting         (dict)      : Configured settings for this collector
            parent_item     (sgItemUI)  : Root item instance
        '''
        # Get the current maya selection.
        mSelection = cmds.ls(sl=True, type="transform")

        # Check if the current selection is not empty.
        if(len(mSelection) > 0):

            # Create an item for each selected asset.
            for asset in mSelection:
                
                # Create the main rig item.
                mainItem = self.collect_mayaAsset(
                    settings,
                    parent_item,
                    asset,
                    "Asset Shading Master",
                    "maya.asset"
                )
                # Create the child rig item.
                mtlxIcon = os.path.join(self.disk_location, os.pardir, "icons", "materialX.png")

                shdLoItem = mainItem.create_item("maya.asset.materialXLO", "Asset MaterialX LO", asset)
                shdLoItem.set_icon_from_path(mtlxIcon)
                shdMiItem = mainItem.create_item("maya.asset.materialXMI", "Asset MaterialX MI", asset)
                shdMiItem.set_icon_from_path(mtlxIcon)
                shdHiItem = mainItem.create_item("maya.asset.materialXHI", "Asset MaterialX HI", asset)
                shdHiItem.set_icon_from_path(mtlxIcon) 

    def collect_for_env_publish(self, settings, parent_item):
        ''' Create an item represents the environments.

        Args:
            setting         (dict)      : Configured settings for this collector
            parent_item     (sgItemUI)  : Root item instance
        '''
        # Get the selection.
        mSelection = cmds.ls(sl=True, long=True, type="transform")

        # Loop over the selection and check the end tag.
        for transform in mSelection:
            # Check the end tag and create the corresponding item.
            if(self.check_end_tag(transform, 'ENV')):
                # Create the asset publish item.
                self.collect_environment(settings, parent_item, transform)

    def collect_for_shot_animation_publish(self, settings, parent_item):
        ''' Create the items to publish animation alembic.

        Args:
            setting         (dict)      : Configured settings for this collector
            parent_item     (sgItemUI)  : Root item instance
        '''
        publisher = self.parent

        # Get the current maya selection.
        mSelection = cmds.ls(sl=True, type="transform")

        # Loop over the selection and check the end tag.
        for transform in mSelection:
            # Check the end tag and create the corresponding item.
            if(self.check_end_tag(transform, 'ENV')):
                self.collect_animation_environment(settings, parent_item, transform)
            
            # Check the end tag and create the corresponding item.
            if(self.check_end_tag(transform, 'RIG')):
                self.collect_animation_asset(settings, parent_item, transform)

            # Check the end tag and create the corresponding item.
            if(self.check_end_tag(transform, 'CAMBUF')):
                self.collect_animation_camera(settings, parent_item, transform)

    def collect_for_sequence_setDress_publish(self, settings, parent_item):
        ''' Create the items to publish the set dressing.

        Args:
            setting         (dict)      : Configured settings for this collector
            parent_item     (sgItemUI)  : Root item instance
        '''
        publisher = self.parent

        # Get the selection.
        mSelection = cmds.ls(sl=True, long=True, type="transform")

        # Loop over the selection and check the end tag.
        for transform in mSelection:
            # Check the end tag and create the corresponding item.
            if(self.check_end_tag(transform, 'CAMBUF')):
                # Create the publish item.
                self.collect_camera(settings, parent_item, transform)

# COLLECT BY ELEMENT FUNCTIONS.

    def collect_scene(self, settings, parent_item):
        ''' Create an item representing the scene.

        Args:
            setting     (dict)  : Configured settings for this collector.
            parent_item ()      : Parent Item instance.

        Returns:
            item                : The new ui item.
        '''
        publisher = self.parent

        # Get the file name.
        fileName = cmds.file(q=True, sn=True)

        # Create the item.
        item = parent_item.create_item("maya.workscene", "Maya Scene", os.path.split(fileName)[-1])

        # Get the icon path to display for this item
        icon_path = os.path.join(self.disk_location, os.pardir, "icons", "maya.png")
        item.set_icon_from_path(icon_path)

        # Add the project root to the item properties.
        project_root = cmds.workspace(q=True, rootDirectory=True)
        item.properties["project_root"] = project_root

        # If a work template is defined, add it to the item properties so
        # that it can be used by attached publish plugins.
        work_template_setting = settings.get("Work Template")
        if(work_template_setting):

            work_template = publisher.engine.get_template_by_name(
                work_template_setting.value
            )

            # Store the template on the item for use by publish plugins.
            item.properties["work_template"] = work_template
            self.logger.debug("Work template defined for Maya collection.")

        # Returns the item.
        return item

    def collect_mayaAsset(self, settings, parent_item, assetRoot, itemName, itemType):
        """ Collect an asset.

        Args:
            settings    (dict) :    Configured settings for this collector.
            parent_item ():         Parent Item instance.
            assetRoot   (str):      The asset root name.

        Returns:
            item : The new ui item.
        """
        publisher = self.parent

        # Create the ui item for the asset.
        assetItem = parent_item.create_item(itemType, itemName, assetRoot)

        # Get the icon path to display for this item
        icon_path = os.path.join(self.disk_location, os.pardir, "icons", "maya.png")
        assetItem.set_icon_from_path(icon_path)

        # Add the asset project root to the item properties.
        project_root = cmds.workspace(q=True, rootDirectory=True)
        assetItem.properties["project_root"] = project_root

        # Create the asset object an add it to the item properties.
        # That allow to share the MayaAsset Class with the publish plugin.
        mayaAsset = P3Dfw.MayaAsset(assetRoot=assetRoot)
        assetItem.properties["assetObject"] = mayaAsset

        # if a work template is defined, add it to the item properties so
        # that it can be used by attached publish plugins
        work_template_setting = settings.get("Work Template")
        if work_template_setting:

            work_template = publisher.engine.get_template_by_name(
                work_template_setting.value
            )

            # store the template on the item for use by publish plugins. we
            # can't evaluate the fields here because there's no guarantee the
            # current session path won't change once the item has been created.
            # the attached publish plugins will need to resolve the fields at
            # execution time.
            assetItem.properties["work_template"] = work_template
            self.logger.debug("Work template defined for Maya collection.")

        return assetItem

    def collect_mayaEnvironment(self, settings, parent_item, environmentRoot, itemName, itemType):
        """ Collect an environment.

        Args:
            settings        (dict)  :    Configured settings for this collector.
            parent_item     ()      :    Parent Item instance.
            environmentRoot (str)   :    The environment root name.

        Returns:
            item                    : The new ui item.
        """
        # Get the publisher.
        publisher = self.parent

        # Create the ui item for the environment.
        environmentItem = parent_item.create_item(itemType, itemName, environmentRoot)

        # Get the icon path to display for this item
        icon_path = os.path.join(self.disk_location, os.pardir, "icons", "maya.png")
        environmentItem.set_icon_from_path(icon_path)

        # Add the asset project root to the item properties.
        project_root = cmds.workspace(q=True, rootDirectory=True)
        environmentItem.properties["project_root"] = project_root

        # Create the environment object an add it to the item properties.
        mayaObject = P3Dfw.MayaEnvironment(root=environmentRoot)
        environmentItem.properties["mayaObject"] = mayaObject

        # if a work template is defined, add it to the item properties so
        # that it can be used by attached publish plugins
        work_template_setting = settings.get("Work Template")
        if(work_template_setting):

            work_template = publisher.engine.get_template_by_name(
                work_template_setting.value
            )

            # store the template on the item for use by publish plugins. we
            # can't evaluate the fields here because there's no guarantee the
            # current session path won't change once the item has been created.
            # the attached publish plugins will need to resolve the fields at
            # execution time.
            environmentItem.properties["work_template"] = work_template
            self.logger.debug("Work template defined for Maya collection.")
        
        return environmentItem

    def collect_mayaObject(self, settings, parent_item, mayaObject, itemName, itemType):
        """ Collect a maya object.

        Args:
            settings        (dict)                  :    Configured settings for this collector.
            parent_item     ()                      :    Parent Item instance.
            mayaObject      (:class:`MayaObject`)   :    The maya object linked.

        Returns:
            item                                    : The new ui item.
        """
        # Get the publisher.
        publisher = self.parent

        # Create the ui item for the object.
        objectItem = parent_item.create_item(itemType, itemName, mayaObject.fullname)

        # Get the icon path to display for this item
        icon_path = os.path.join(self.disk_location, os.pardir, "icons", "geometry.png")
        objectItem.set_icon_from_path(icon_path)

        # Add the maya object to the item properties.
        objectItem.properties["mayaObject"] = mayaObject
        
        return objectItem

    def collect_asset(self, settings, parent_item, assetRoot):
        """ Collect an asset.

        Args:
            settings    (dict)              : Configured settings for this collector.
            parent_item ()                  : Parent Item instance.
            assetRoot   (str)               : The asset root name.

        Returns:
            item                            : The new ui item.
        """
        # Create the Maya object for the asset.
        mayaObject = P3Dfw.MayaAsset(assetRoot=assetRoot)

        # Create the main item.
        mainItem = self.collect_mayaObject(
            settings,
            parent_item,
            mayaObject,
            "Maya Asset",
            "maya.asset"
        )

        # Create the item ui for the maya ascii export.
        self.create_item_maya(
            mainItem,
            'maya.asset.ma',
            'Maya Ascii',
            'Maya Ascii'
        )

        # Return the main asset item.
        return mainItem

    def collect_sculpt(self, settings, parent_item, sculptRoot):
        """ Collect an asset.

        Args:
            settings    (dict)              : Configured settings for this collector.
            parent_item ()                  : Parent Item instance.
            sculptRoot  (str)               : The sculpt root name.

        Returns:
            item                            : The new ui item.
        """
        # Get the publisher.
        publisher = self.parent

        # Create the ui item for the sculpt.
        abcIconPath     = os.path.join(self.disk_location, os.pardir, "icons", "alembic.png")
        abcAssetItem    = parent_item.create_item("maya.asset.alembicSCULPT", "Alembic Sculpt", "{} Sculpt".format(sculptRoot))
        abcAssetItem.set_icon_from_path(abcIconPath)

        # Add the asset project root to the item properties.
        project_root = cmds.workspace(q=True, rootDirectory=True)
        abcAssetItem.properties["project_root"] = project_root

        # Store the sculpt root in the item properties.
        abcAssetItem.properties["assetObject"] = sculptRoot

        # If a work template is defined, add it to the item properties so
        # that it can be used by attached publish plugins.
        work_template_setting = settings.get("Work Template")
        if (work_template_setting):

            work_template = publisher.engine.get_template_by_name(
                work_template_setting.value
            )

            # Store the template on the item for use by publish plugins. We
            # can't evaluate the fields here because there's no guarantee the
            # current session path won't change once the item has been created.
            # The attached publish plugins will need to resolve the fields at
            # execution time.
            abcAssetItem.properties["work_template"] = work_template
            self.logger.debug("Work template defined for Maya collection.")

        # Return the main item.
        return abcAssetItem

    def collect_asset_rig(self, settings, parent_item, assetRoot):
        """ Collect an for the rig.

        Args:
            settings    (dict)              : Configured settings for this collector.
            parent_item ()                  : Parent Item instance.
            assetRoot   (str)               : The asset root name.
            ma          (str,   optional)   : Set the export type for the maya file.
                                            Can be single, lod or none.
                                            Default to single.
            abc         (str,   optional)   : Set the export type for the alembic file.
                                            Can be single, lod or none.
                                            Default to lod.

        Returns:
            item                            : The new ui item.
        """
        # Create the Maya object for the asset.
        mayaObject = P3Dfw.MayaAsset(assetRoot=assetRoot)

        # Create the main rig item.
        mainItem = self.collect_mayaObject(
            settings,
            parent_item,
            mayaObject,
            "Maya Asset",
            "maya.asset.rig"
        )

        # Create an item for each resolution.
        for resolution in ["high", "mid", "low"]:

            # Check if the resolution is available.
            if(resolution == 'high' and not mayaObject.meshesHI):
                continue
            
            if(resolution == 'mid' and not mayaObject.meshesMI):
                continue

            if(resolution == 'low' and not mayaObject.meshesLO):
                continue

            resolutionItem = mainItem.create_item(
                "maya.asset.rig.{}".format(resolution),
                "{} Resolution".format(resolution.capitalize()),
                "{} Rig {}".format(mayaObject.fullname, resolution.capitalize())
            )

            # Create the item ui for the maya ascii export.
            self.create_item_maya(
                resolutionItem,
                "maya.asset.rig.{}.ma".format(resolution),
                'Maya Ascii',
                'Maya Ascii {}'.format(resolution.capitalize())
            )

            # Create the item ui for the alembic export.
            self.create_item_alembic(
                resolutionItem,
                "maya.asset.{}.abc".format(resolution),
                'Alembic',
                'Alembic {}'.format(resolution.capitalize())
            )

    def collect_environment(self, settings, parent_item, environmentRoot):
        """ Collect an environment.

        Args:
            settings            (dict)  : Configured settings for this collector.
            parent_item         ()      : Parent Item instance.
            environmentRoot     (str)   : The environment root name.

        Returns:
            item                        : The new ui item.
        """

        # Create the Maya object for the environment.
        mayaObject = P3Dfw.MayaEnvironment(root=environmentRoot)

        # Create the main item.
        mainItem = self.collect_mayaObject(
            settings,
            parent_item,
            mayaObject,
            "Maya Environment",
            "maya.environment"
        )

        # Create the item ui for the maya ascii export.
        self.create_item_maya(
            mainItem,
            'maya.environment.ma',
            'Maya Ascii',
            'Maya Ascii'
        )

        # Get the animation.
        animatedAssets, deformedAssets = mayaObject.getAnimation()
        # Get the assets.
        assets = mayaObject.getAssets()
        # Gte the assets list without the deformedAssets.
        notDeformedAssets = [asset for asset in assets if asset not in deformedAssets]

        # Create the item for the not deformed assets.
        alembicEnvironment = self.create_item_alembic(
            mainItem,
            "maya.environment.abc",
            "Alembic",
            "Alembic"
        )
        # Add the environment to the item properties.
        alembicEnvironment.properties["assets"] = notDeformedAssets

        # Create an item to act has a parent for the deformed assets.
        deformedAssetsItem = self.create_item(
            mainItem,
            "maya.environmentDeformed",
            "Deformed Assets",
            "Deformed Assets",
            "geometry.png"
        )
        # Add the environment to the item properties.
        deformedAssetsItem.properties["environmentObject"] = mayaObject

        # Loop over the deformed assets.
        for deformedAsset in deformedAssets:
            # Create the item for the deformed asset.
            self.collect_deformedAsset(settings, deformedAssetsItem, deformedAsset)

        # Return the environment item.
        return mainItem

    def collect_deformedAsset(self, settings, parent_item, deformedAsset):
        """ Collect a deformed asset.

        Args:
            settings            (dict)  : Configured settings for this collector.
            parent_item         ()      : Parent Item instance.
            deformedAsset       (str)   : The deformed asset.

        Returns:
            item                        : The new ui item.
        """
        # # Create the main item.
        # mainItem = parent_item.create_item(
        #     "maya.environmentDeformed",
        #     "Deformed Asset",
        #     deformedAsset.fullname.split('|')[-1].split(':')[0]
        # )

        # Create the item ui for the alembic export.
        item = self.create_item_alembic(
            parent_item,
            'maya.environmentDeformed.abc',
            'Alembic',
            deformedAsset.fullname.split('|')[-1].split(':')[0]
        )
        # Add the deformed asset to the item properties.
        item.properties["mayaObject"] = deformedAsset

        self.logger.info("Deformed asset: {}".format(deformedAsset.fullname))

        return item

    def collect_camera(self, settings, parent_item, cameraRoot):
        """ Collect a camera.

        Args:
            settings    (dict)              : Configured settings for this collector.
            parent_item ()                  : Parent Item instance.
            cameraRoot  (str)               : The camera root name.

        Returns:
            item                            : The new ui item.
        """
        publisher = self.parent

        # Create an item for the camera.
        cameraItem = parent_item.create_item('maya.camera', 'Camera', cameraRoot)

        # Get the icon path to display for this item.
        iconPath = os.path.join(self.disk_location, os.pardir, "icons", "camera.png")
        cameraItem.set_icon_from_path(iconPath)

        # Add the camera root to the item properties.
        cameraItem.properties["cameraRoot"] = cameraRoot

        # Add the project root to the item properties.
        project_root = cmds.workspace(q=True, rootDirectory=True)
        cameraItem.properties["project_root"] = project_root

        # If a work template is defined, add it to the item properties so
        # that it can be used by attached publish plugins.
        work_template_setting = settings.get("Work Template")
        if(work_template_setting):

            work_template = publisher.engine.get_template_by_name(
                work_template_setting.value
            )

            # Store the template on the item for use by publish plugins.
            cameraItem.properties["work_template"] = work_template
            self.logger.debug("Work template defined for Maya collection.")


        # Get the camera shapes in the depedencies.
        cameraShapes = cmds.listRelatives(cameraRoot, allDescendents=True, type="camera", fullPath=True)
        self.logger.debug(cameraShapes)
        if(cameraShapes):
            camera = cameraShapes[0]
            cameraName = cameraRoot.split("|")[-1]

            # Get the temporary directory.
            tempDir = tempfile.gettempdir()
            # Get the temporary file.
            temporaryFilePath = os.path.join(tempDir, 'screenCapture_{}'.format(cameraName))

            # Get the current viewport.
            viewport = cmds.playblast(activeEditor=True).split('|')[-1]

            # Get the current camera of the viewport.
            currentCamera = cmds.modelPanel(viewport, query=True, camera=True)

            # Set the camera.
            cmds.modelPanel(viewport, edit=True, camera=camera)

            # Playblast the camera at the temporary file location.
            utils.executeInMainThreadWithResult(
                lambda : 
                cmds.playblast(
                    viewer          = False,
                    format          = "image",
                    filename        = temporaryFilePath,
                    clearCache      = True,
                    showOrnaments   = False,
                    percent         = 100,
                    compression     = "png",
                    quality         = 100,
                    widthHeight     = [512, 512],
                    offScreen       = True,
                    startTime       = 1001,
                    endTime         = 1001,
                    forceOverwrite  = True,
                    editorPanelName = viewport
                )
            )
            # Get the playblast file.
            playBlastFile = temporaryFilePath + '.1001.png'

            # Set the camera back to the original camera.
            cmds.modelPanel(viewport, edit=True, camera=currentCamera)

            # Set the thumbnail path.
            cameraItem.set_thumbnail_from_path(playBlastFile)

            # Add the playblast file to the item properties.
            cameraItem.properties["playBlastFile"] = playBlastFile



        # Create the item for the maya ascii export.
        self.create_item_camera_maya(cameraItem, cameraRoot)

        # Create the item for the alembic export.
        self.create_item_camera_alembic(cameraItem, cameraRoot)

        # Return the camera item.
        return cameraItem

    def collect_selection(self, settings, parent_item):
        """ Collect a selection.

        Args:
            settings    (dict)              : Configured settings for this collector.
            parent_item ()                  : Parent Item instance.

        Returns:
            item                            : The new ui item.
        """
        publisher = self.parent

        selection = cmds.ls(selection=True, long=True)
        if(not selection):
            return None

        # Create an item.
        item = parent_item.create_item(
            'maya.selection',
            'Selection', 
            selection[0]
        )

        # Get the icon path to display for this item.
        iconPath = os.path.join(self.disk_location, os.pardir, "icons", "geometry.png")
        item.set_icon_from_path(iconPath)

        # Create the item for the maya ascii export.
        self.create_item_maya(
            item,
            "maya.selection.ma",
            "Maya Ascii",
            selection[0],
        )

        # Create the item for the alembic export.
        self.create_item_alembic(
            item,
            "maya.selection.abc",
            "Alembic",
            selection[0],
        )

        # Return the item.
        return item

# COLLECT ANIMATIONS.

    def collect_animation_environment(self, settings, parent_item, environmentRoot):
        """ Collect an environment.

        Args:
            settings            (dict)  : Configured settings for this collector.
            parent_item         ()      : Parent Item instance.
            environmentRoot     (str)   : The environment root name.

        Returns:
            item                        : The new ui item.
        """
        # Create the Maya object for the environment.
        mayaObject = P3Dfw.MayaEnvironment(root=environmentRoot)

        # Create the main item.
        mainItem = self.collect_mayaObject(
            settings,
            parent_item,
            mayaObject,
            "Maya Environment",
            "maya.shot.environment"
        )

        # Get the animation.
        animatedAssets, deformedAssets = mayaObject.getAnimation()

        # Create the item for the animated assets.
        self.collect_animation_animatedAssets(settings, mainItem, animatedAssets)
 
        # Create an item to act has a parent for the deformed assets.
        deformedAssetsItem = self.create_item(
            mainItem,
            "maya.shot.environmentDeformed",
            "Deformed Assets",
            "Deformed Assets",
            "geometry.png"
        )
        # Add the environment to the item properties.
        deformedAssetsItem.properties["environmentObject"] = mayaObject

        # Loop over the deformed assets.
        for deformedAsset in deformedAssets:
            # Create the item for the deformed asset.
            self.collect_animation_deformedAsset(settings, deformedAssetsItem, deformedAsset)

        # Return the environment item.
        return mainItem

    def collect_animation_animatedAssets(self, settings, parent_item, animatedAssets):
        """ Collect the animated assets.

        Args:
            settings            (dict)  : Configured settings for this collector.
            parent_item         ()      : Parent Item instance.
            animatedAssets      (list)  : The animated assets.

        Returns:
            item                        : The new ui item.
        """
        # Create an item for the type.

        # Create an item to act has a parent for the animated assets.
        mainItem = parent_item.create_item(
            "maya.shot.environmentAnimated",
            "Animated Instances",
            "Animated Instances"
        )
        # Add the animated assets to the item properties.
        mainItem.properties["animatedAssets"] = animatedAssets

        self.logger.debug("Collecting animated assets: {}".format(animatedAssets))

        # Create the item ui for the alembic export.
        self.create_item_alembic(
            mainItem,
            'maya.shot.environmentAnimated.abc',
            'Alembic Environment',
            'Alembic Environment'
        )

        return mainItem

    def collect_animation_deformedAsset(self, settings, parent_item, deformedAsset):
        """ Collect a deformed asset.

        Args:
            settings            (dict)  : Configured settings for this collector.
            parent_item         ()      : Parent Item instance.
            deformedAsset       (str)   : The deformed asset.

        Returns:
            item                        : The new ui item.
        """
        # Create the main item.
        mainItem = parent_item.create_item(
            "maya.shot.environmentDeformed",
            "Deformed Asset",
            deformedAsset.fullname.split('|')[-1].split(':')[-2]
        )
        # Add the deformed asset to the item properties.
        mainItem.properties["mayaObject"] = deformedAsset

        # Create the item ui for the alembic export.
        self.create_item_alembic(
            mainItem,
            'maya.shot.environmentDeformed.abc',
            'Alembic',
            deformedAsset.fullname.split('|')[-1].split(':')[-2]
        )

        return mainItem


    def collect_animation_asset(self, settings, parent_item, assetRoot):
        """ Collect an asset.

        Args:
            settings            (dict)  : Configured settings for this collector.
            parent_item         ()      : Parent Item instance.
            assetRoot           (str)   : The asset root name.

        Returns:
            item                        : The new ui item.
        """
        # Create the Maya object for the asset.
        mayaObject = P3Dfw.MayaAsset(assetRoot=assetRoot)

        # Create the main item.
        mainItem = self.collect_mayaObject(
            settings,
            parent_item,
            mayaObject,
            "Asset",
            "maya.shot.assetInstance"
        )

        # Create the item ui for the alembic export.
        self.create_item_alembic(
            mainItem,
            'maya.shot.assetInstance.abc',
            'Alembic Asset',
            mayaObject.fullname.split('|')[-1].split(':')[0]
        )

        # Check if the asset is referenced and extract the path.
        refPath = mayaObject.referencePath
        if(refPath):
            # Get the asset rig publish template.
            template = self.parent.engine.get_template_by_name('maya_asset_rig_publish')
            # Check if the path matches the template.
            fields = template.validate_and_get_fields(refPath)
            if(fields):
                # Get the asset field.
                assetField = fields.get('Asset')
                # Create special publish for Yuri.
                if(assetField == "yuri"):
                    # Create the item ui for the local alembic export.
                    self.create_item(
                        mainItem,
                        'maya.shot.assetInstance.local.abc',
                        'Alembic Local',
                        mayaObject.fullname.split('|')[-1].split(':')[0],
                        'alembic.png'
                    )
                    # Create the item ui for the spline alembic export.
                    self.create_item(
                        mainItem,
                        'maya.shot.assetInstance.spline.abc',
                        'Alembic Spline',
                        mayaObject.fullname.split('|')[-1].split(':')[0],
                        'alembic.png'
                    )

        # Return the asset item.
        return mainItem

    def collect_animation_camera(self, settings, parent_item, cameraRoot):
        """ Collect a camera.

        Args:
            settings    (dict)              : Configured settings for this collector.
            parent_item ()                  : Parent Item instance.
            cameraRoot  (str)               : The camera root name.

        Returns:
            item                            : The new ui item.
        """
        publisher = self.parent

        # Create an item for the camera.
        cameraItem = parent_item.create_item('maya.shot.camera', 'Camera', cameraRoot)

        # Get the icon path to display for this item.
        iconPath = os.path.join(self.disk_location, os.pardir, "icons", "camera.png")
        cameraItem.set_icon_from_path(iconPath)

        # Add the camera root to the item properties.
        cameraItem.properties["cameraRoot"] = cameraRoot

        # Add the project root to the item properties.
        project_root = cmds.workspace(q=True, rootDirectory=True)
        cameraItem.properties["project_root"] = project_root

        # If a work template is defined, add it to the item properties so
        # that it can be used by attached publish plugins.
        work_template_setting = settings.get("Work Template")
        if(work_template_setting):

            work_template = publisher.engine.get_template_by_name(
                work_template_setting.value
            )

            # Store the template on the item for use by publish plugins.
            cameraItem.properties["work_template"] = work_template
            self.logger.debug("Work template defined for Maya collection.")




        # Create the item ui for the alembic export.
        self.create_item_alembic(
            cameraItem,
            'maya.shot.camera.abc',
            'Alembic Camera',
            cameraRoot
        )


        # Return the camera item.
        return cameraItem

# CREATE ASSET ITEM FUNCTIONS.

    def create_item_asset_maya(self, parent_item, assetRoot):
        """ Create an item to export the asset as maya ascii.

        Args:
            parent_item ():         Parent Item instance.
            assetRoot   (str):      The asset root name.

        Returns:
            item : The new ui item.
        """
        # Create the item ui for the maya export.
        mayaIconPath    = os.path.join(self.disk_location, os.pardir, "icons", "maya.png")
        maAssetItem     = parent_item.create_item("maya.asset", "Maya Asset", assetRoot)
        maAssetItem.set_icon_from_path(mayaIconPath)

        return maAssetItem

    def create_item_asset_alembic(self, parent_item, assetRoot):
        """ Create an item to export the asset as alembic.

        Args:
            parent_item ():         Parent Item instance.
            assetRoot   (str):      The asset root name.

        Returns:
            item : The new ui item.
        """
        # Create the item ui for the alembic export.
        abcIconPath     = os.path.join(self.disk_location, os.pardir, "icons", "alembic.png")
        abcAssetItem    = parent_item.create_item("maya.asset.alembic", "Alembic Mesh", "%s Meshes" % assetRoot)
        abcAssetItem.set_icon_from_path(abcIconPath)

        return abcAssetItem

    def create_item_asset_alembicLOD(self, parent_item, assetRoot):
        """ Create an item to export the asset LODs as alembic.

        Args:
            parent_item ():         Parent Item instance.
            assetRoot   (str):      The asset root name.

        Returns:
            item : The new ui items.
        """
        # Create the item ui for the alembic export.
        abcIconPath         = os.path.join(self.disk_location, os.pardir, "icons", "alembic.png")

        abcAssetLOItem      = parent_item.create_item("maya.asset.low.abc", "Alembic Low Resolution", "%s Low Meshes" % assetRoot)
        abcAssetLOItem.set_icon_from_path(abcIconPath)
        abcAssetMIItem      = parent_item.create_item("maya.asset.mid.abc", "Alembic Middle Resolution", "%s Mid Meshes" % assetRoot)
        abcAssetMIItem.set_icon_from_path(abcIconPath)
        abcAssetHIItem      = parent_item.create_item("maya.asset.high.abc", "Alembic High Resolution", "%s High Meshes" % assetRoot)
        abcAssetHIItem.set_icon_from_path(abcIconPath)
        # abcAssetTechItem   = parent_item.create_item("maya.asset.alembicTech", "Alembic Technical", "%s Technical Meshes" % assetRoot)
        # abcAssetTechItem.set_icon_from_path(abcIconPath)

        return (abcAssetLOItem, abcAssetMIItem, abcAssetHIItem)

# CREATE CAMERA ITEM FUNCTIONS.

    def create_item_camera_maya(self, parent_item, cameraRoot):
        """ Create an item to export the camera as maya ascii.

        Args:
            parent_item (sgItemUI)  :   Parent Item instance.
            assetRoot   (str)       :   The asset root name.

        Returns:
            item                    : The new ui item.
        """
        item    = parent_item.create_item("maya.camera.ma", "Maya Camera", cameraRoot)
        icon    = os.path.join(self.disk_location, os.pardir, "icons", "maya.png")
        item.set_icon_from_path(icon)

        return item

    def create_item_camera_alembic(self, parent_item, cameraRoot):
        """ Create an item to export the camera as alembic.

        Args:
            parent_item (sgItemUI)  :   Parent Item instance.
            assetRoot   (str)       :   The asset root name.

        Returns:
            item                    : The new ui item.
        """
        item    = parent_item.create_item("maya.camera.abc", "Alembic Camera", cameraRoot)
        icon    = os.path.join(self.disk_location, os.pardir, "icons", "alembic.png")
        item.set_icon_from_path(icon)

        return item

# CREATE REVIEW ITEM FUNCTIONS.

    def collect_review(self, parent_item, context):
        """
        Creates items for review.

        :param parent_item: Parent Item instance
        """
        print("SGTK | Collector | Collect the session's review.")


        # Get the entity root using the context.
        entityRootLocations = context.entity_locations
        # Check if a entity root location exists.
        if(not entityRootLocations):
            self.logger.debug("No entity root location found.")
            return

        # Normalize the path.
        entityRoot = os.path.normpath(entityRootLocations[0])
        self.logger.debug("Entity root defined for Maya.")

        # Get the path to the review folder.
        reviewFolder = os.path.join(entityRoot, 'review')
        # Check if the folder exists.
        if(not os.path.exists(reviewFolder)):
            self.logger.debug("No review folder found.")
            return

        # Get the current scene name.
        sceneName       = os.path.splitext(cmds.file(query=True, sceneName=True, shortName=True))[0]
        # Split the scene name and the version number.
        sceneNameSplit  = sceneName.split('.v')

        # Check if the file name is valide.
        if(len(sceneNameSplit) != 2):
            self.logger.warning("Scene name is not valid.")
            return

        sceneName       = sceneNameSplit[0]
        sceneversion    = sceneNameSplit[1]

        # Use regex to find the correct file.
        reExpr = "^({})(|[_].*)([.]v{})$".format(sceneName, sceneversion)

        # Loop over all the files in the review folder.
        for file in os.listdir(reviewFolder):
            # Get the info of the item.
            itemInfo = self._get_item_info(file)
            # Skip if it is neither a video nor an image.
            if(itemInfo["item_type"] not in ["file.image", "file.video"]):
                continue

            # Get the file name without extension.
            fileName        = os.path.splitext(file)[0]

            # Check if the file name matches the regex.
            if(re.search(reExpr, fileName)):
                # create the review item for the publish hierarchy
                review_item = parent_item.create_item(
                    "maya.playblast.review", "Review", file
                )

                # Get the icon path to display for this item.
                icon_path = os.path.join(self.disk_location, os.pardir, "icons", "review.png")
                #review_item.set_icon_from_path(icon_path)
                review_item.set_icon_from_path(itemInfo["icon_path"])

                # Get the path to the file.
                filePath = os.path.join(reviewFolder, file)

                # Add the path to the item properties
                review_item.properties["path"] = filePath

                # if the supplied path is an image, use the path as the thumbnail.
                if(itemInfo["item_type"].startswith("file.image")):
                    review_item.set_thumbnail_from_path(filePath)
                    # disable thumbnail creation since we get it for free
                    review_item.thumbnail_enabled = False

# DEFAULT ITEMS FUNCTIONS.

    def create_item(self, parent_item, itemType, itemTypeName, itemName, iconName):
        """
        Create an item to publish the transform as maya ascii.

        Args:
            parent_item     ()      : Parent Item instance.
            itemType        (str)   : The type of the item.
            itemTypeName    (str)   : The name of the item type.
            itemName        (str)   : The name of the item.
            iconName        (str)   : The name of the icon.
        
        Returns:
            item                    : The new ui item.
        """
        item    = parent_item.create_item(itemType, itemTypeName, itemName)
        icon    = os.path.join(self.disk_location, os.pardir, "icons", iconName)
        item.set_icon_from_path(icon)

        return item

    def create_item_maya(self, parent_item, itemType, itemTypeName, itemName):
        """
        Create an item to publish the transform as maya ascii.

        Args:
            parent_item     ()      : Parent Item instance.
            itemType        (str)   : The type of the item.
            itemTypeName    (str)   : The name of the item type.
            itemName        (str)   : The name of the item.
        
        Returns:
            item                    : The new ui item.
        """        
        return self.create_item(parent_item, itemType, itemTypeName, itemName, "maya.png")

    def create_item_alembic(self, parent_item, itemType, itemTypeName, itemName):
        """
        Create an item to publish the transform as alembic.

        Args:
            parent_item     ()      : Parent Item instance.
            itemType        (str)   : The type of the item.
            itemTypeName    (str)   : The name of the item type.
            itemName        (str)   : The name of the item.
        
        Returns:
            item                    : The new ui item.
        """

        return self.create_item(parent_item, itemType, itemTypeName, itemName, "alembic.png")

# DEFAULT COLLECT FUNCTIONS.

    def collect_current_maya_session(self, settings, parent_item):
        """
        Creates an item that represents the current maya session.

        :param parent_item: Parent Item instance

        :returns: Item of type maya.session
        """

        print("SGTK | Collector | Get the maya current session infos.")

        publisher = self.parent

        # get the path to the current file
        path = cmds.file(query=True, sn=True)

        # determine the display name for the item
        if path:
            file_info = publisher.util.get_file_path_components(path)
            display_name = file_info["filename"]
        else:
            display_name = "Current Maya Session"

        # create the session item for the publish hierarchy
        session_item = parent_item.create_item(
            "maya.session", "Maya Session", display_name
        )

        # get the icon path to display for this item
        icon_path = os.path.join(self.disk_location, os.pardir, "icons", "maya.png")
        session_item.set_icon_from_path(icon_path)

        # discover the project root which helps in discovery of other
        # publishable items
        project_root = cmds.workspace(q=True, rootDirectory=True)
        session_item.properties["project_root"] = project_root

        # if a work template is defined, add it to the item properties so
        # that it can be used by attached publish plugins
        work_template_setting = settings.get("Work Template")
        if work_template_setting:

            work_template = publisher.engine.get_template_by_name(
                work_template_setting.value
            )

            # store the template on the item for use by publish plugins. we
            # can't evaluate the fields here because there's no guarantee the
            # current session path won't change once the item has been created.
            # the attached publish plugins will need to resolve the fields at
            # execution time.
            session_item.properties["work_template"] = work_template
            self.logger.debug("Work template defined for Maya collection.")

        self.logger.info("Collected current Maya scene")

        return session_item

    def collect_alembic_caches(self, parent_item, project_root):
        """
        Creates items for alembic caches

        Looks for a 'project_root' property on the parent item, and if such
        exists, look for alembic caches in a 'cache/alembic' subfolder.

        :param parent_item: Parent Item instance
        :param str project_root: The maya project root to search for alembics
        """

        print("SGTK | Collector | Collect the session's alembic.")


        # ensure the alembic cache dir exists
        cache_dir = os.path.join(project_root, "cache", "alembic")
        if not os.path.exists(cache_dir):
            return

        self.logger.info(
            "Processing alembic cache folder: %s" % (cache_dir,),
            extra={"action_show_folder": {"path": cache_dir}},
        )

        # look for alembic files in the cache folder
        for filename in os.listdir(cache_dir):
            cache_path = os.path.join(cache_dir, filename)

            # do some early pre-processing to ensure the file is of the right
            # type. use the base class item info method to see what the item
            # type would be.
            item_info = self._get_item_info(filename)
            if item_info["item_type"] != "file.alembic":
                continue

            # allow the base class to collect and create the item. it knows how
            # to handle alembic files
            super(MayaSessionCollector, self)._collect_file(parent_item, cache_path)

    def _collect_session_geometry(self, parent_item):
        """
        Creates items for session geometry to be exported.

        :param parent_item: Parent Item instance
        """
        print("SGTK | Collector | Collect the session's geometries.")

        geo_item = parent_item.create_item(
            "maya.session.geometry", "Geometry", "All Session Geometry"
        )

        # get the icon path to display for this item
        icon_path = os.path.join(self.disk_location, os.pardir, "icons", "geometry.png")

        geo_item.set_icon_from_path(icon_path)

    def collect_playblasts(self, parent_item, project_root):
        """
        Creates items for quicktime playblasts.

        Looks for a 'project_root' property on the parent item, and if such
        exists, look for movie files in a 'movies' subfolder.

        :param parent_item: Parent Item instance
        :param str project_root: The maya project root to search for playblasts
        """
        print("SGTK | Collector | Collect the session's playblasts.")


        movie_dir_name = None

        # try to query the file rule folder name for movies. This will give
        # us the directory name set for the project where movies will be
        # written
        if "movie" in cmds.workspace(fileRuleList=True):
            # this could return an empty string
            movie_dir_name = cmds.workspace(fileRuleEntry="movie")

        if not movie_dir_name:
            # fall back to the default
            movie_dir_name = "movies"

        # ensure the movies dir exists
        movies_dir = os.path.join(project_root, movie_dir_name)
        if not os.path.exists(movies_dir):
            return

        self.logger.info(
            "Processing movies folder: %s" % (movies_dir,),
            extra={"action_show_folder": {"path": movies_dir}},
        )

        # look for movie files in the movies folder
        for filename in os.listdir(movies_dir):

            # do some early pre-processing to ensure the file is of the right
            # type. use the base class item info method to see what the item
            # type would be.
            item_info = self._get_item_info(filename)
            if item_info["item_type"] != "file.video":
                continue

            movie_path = os.path.join(movies_dir, filename)

            # allow the base class to collect and create the item. it knows how
            # to handle movie files
            item = super(MayaSessionCollector, self)._collect_file(
                parent_item, movie_path
            )

            # the item has been created. update the display name to include
            # the an indication of what it is and why it was collected
            item.name = "%s (%s)" % (item.name, "playblast")

    def collect_rendered_images(self, parent_item):
        """
        Creates items for any rendered images that can be identified by
        render layers in the file.

        :param parent_item: Parent Item instance
        :return:
        """
        print("SGTK | Collector | Collect the session's rendered images.")

        # iterate over defined render layers and query the render settings for
        # information about a potential render
        for layer in cmds.ls(type="renderLayer"):

            self.logger.info("Processing render layer: %s" % (layer,))

            # use the render settings api to get a path where the frame number
            # spec is replaced with a '*' which we can use to glob
            (frame_glob,) = cmds.renderSettings(
                genericFrameImageName="*", fullPath=True, layer=layer
            )

            # see if there are any files on disk that match this pattern
            rendered_paths = glob.glob(frame_glob)

            if rendered_paths:
                # we only need one path to publish, so take the first one and
                # let the base class collector handle it
                item = super(MayaSessionCollector, self)._collect_file(
                    parent_item, rendered_paths[0], frame_sequence=True
                )

                # the item has been created. update the display name to include
                # the an indication of what it is and why it was collected
                item.name = "%s (Render Layer: %s)" % (item.name, layer)

# CHECKING FUNCTIONS.

    def check_end_tag(self, object, tag):
        """
        Check if the object ends with the tag.

        Args:
            tag (str): The tag to check.
        """
        return object.endswith('_{}'.format(tag))
