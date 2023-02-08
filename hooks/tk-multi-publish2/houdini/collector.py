# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import hou
import sgtk
import re

# try:
#     from    adamPipe.lookdevAssetNode       import LookdevAssetNode
# except:
#     pass

HookBaseClass = sgtk.get_hook_baseclass()

# A dict of dicts organized by category, type and output file parm
_HOUDINI_OUTPUTS = {
    # rops
    hou.ropNodeTypeCategory(): {
        "alembic": "filename",  # alembic cache
        "comp": "copoutput",  # composite
        "ifd": "vm_picture",  # mantra render node
        "opengl": "picture",  # opengl render
        "wren": "wr_picture",  # wren wireframe
    },
}


class HoudiniSessionCollector(HookBaseClass):
    """
    Collector that operates on the current houdini session. Should inherit from
    the basic collector hook.
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

        # grab any base class settings
        collector_settings = super(HoudiniSessionCollector, self).settings or {}

        # settings specific to this collector
        houdini_session_settings = {
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

        # update the base settings with these settings
        collector_settings.update(houdini_session_settings)

        return collector_settings

    def process_current_session(self, settings, parent_item):
        """
        Analyzes the current Houdini session and parents a subtree of items
        under the parent_item passed in.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        """
        return
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

        # Collect all the files for review.
        # self.collect_review(parent_item, currentContext)

        # Configure the publish with the context.
        if(ctxtEntity["type"] == "Asset"):

            if(ctxtStep["name"] == "Shading"):
                # Collect the data for a Shading Publish.
                self.collect_for_shd_publish(settings, parent_item)

            else:
                # Use the generic collector.
                self.generic_collector(settings, parent_item)

        elif(ctxtEntity["type"] == "Sequence"):

            if(ctxtStep["name"] == "Set Dress (Seq)"):
                # Collect the data for a Shading Publish.
                # self.collect_for_seqSetDressing_publish(settings, parent_item)
                pass

            if(ctxtStep["name"] == "Lighting (Seq)"):
                # Collect the data for a Shading Publish.
                self.collect_for_seqLighting_publish(settings, parent_item)

            else:
                # Use the generic collector.
                self.generic_collector(settings, parent_item)

        elif(ctxtEntity["type"] == "Shot"):

            # Use the generic sollector.
            self.generic_collector(settings, parent_item)
        
        else:
            # Use the generic collector.
            self.generic_collector(settings, parent_item)



# COLLECT BY STEP FUNCTIONS.

    def collect_for_shd_publish(self, settings, parent_item):
        ''' Create the publish items for the shading step.

        Args:
            setting         (dict)      : Configured settings for this collector
            parent_item     (sgItemUI)  : Root item instance
        '''
        # Create the parent item.
        item = self.collect_current_houdini_session(settings, parent_item)

        # Collect the ADAM Material X export nodes.
        self.collect_adam_materialx_export_nodes(item)

        # Collect the ADAM Lookdev asset nodes.
        self.collect_adam_lookdev_asset_nodes(item)

    def collect_for_seqSetDressing_publish(self, settings, parent_item):
        ''' Create the publish items for the sequence setdressing step.

        Args:
            setting         (dict)      : Configured settings for this collector
            parent_item     (sgItemUI)  : Root item instance
        '''
        # Create the parent item.
        item = self.collect_current_houdini_session(settings, parent_item)

        # Collect the nodes.
        self.collect_selectedHDA_nodes(item)

    def collect_for_seqLighting_publish(self, settings, parent_item):
        ''' Create the publish items for the sequence lighting step.

        Args:
            setting         (dict)      : Configured settings for this collector
            parent_item     (sgItemUI)  : Root item instance
        '''
        # Create the parent item.
        item = self.collect_current_houdini_session(settings, parent_item)

        # Collect the nodes.
        self.collect_selectedHDA_nodes(item)

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
        self.logger.debug("Entity root defined for Houdini.")

        # Get the path to the review folder.
        reviewFolder = os.path.join(entityRoot, 'review')
        # Check if the folder exists.
        if(not os.path.exists(reviewFolder)):
            self.logger.debug("No review folder found.")
            return

        # Get the current scene name.
        sceneName       = os.path.splitext( os.path.split(hou.hipFile.name())[1] )[0]
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
                    "houdini.playblast.review", "Review", file
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

# DEFAULT COLLECT FUNCTIONS.

    def collect_current_houdini_session(self, settings, parent_item):
        """
        Creates an item that represents the current houdini session.

        :param dict settings: Configured settings for this collector
        :param parent_item: Parent Item instance

        :returns: Item of type houdini.session
        """

        publisher = self.parent

        # get the path to the current file
        path = hou.hipFile.path()

        # determine the display name for the item
        if path:
            file_info = publisher.util.get_file_path_components(path)
            display_name = file_info["filename"]
        else:
            display_name = "Current Houdini Session"

        # create the session item for the publish hierarchy
        session_item = parent_item.create_item(
            "houdini.session", "Houdini File", display_name
        )

        # get the icon path to display for this item
        icon_path = os.path.join(self.disk_location, os.pardir, "icons", "houdini.png")
        session_item.set_icon_from_path(icon_path)

        # if a work template is defined, add it to the item properties so that
        # it can be used by attached publish plugins
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
            self.logger.debug("Work template defined for Houdini collection.")

        self.logger.info("Collected current Houdini session")
        return session_item

    def generic_collector(self, settings, parent_item):
        ''' Generic collector for all steps.

        Args:
            setting         (dict)      : Configured settings for this collector
            parent_item     (sgItemUI)  : Root item instance
        '''
        # Create the parent item.
        item = self.collect_current_houdini_session(settings, parent_item)

        # Collect the shotgrid alembic nodes.
        self.collect_tk_alembicnodes(item)

    def collect_node_outputs(self, parent_item):
        """
        Creates items for known output nodes

        :param parent_item: Parent Item instance
        """

        for node_category in _HOUDINI_OUTPUTS:
            for node_type in _HOUDINI_OUTPUTS[node_category]:

                if node_type == "alembic" and self._alembic_nodes_collected:
                    self.logger.debug(
                        "Skipping regular alembic node collection since tk "
                        "alembic nodes were collected. "
                    )
                    continue

                if node_type == "ifd" and self._mantra_nodes_collected:
                    self.logger.debug(
                        "Skipping regular mantra node collection since tk "
                        "mantra nodes were collected. "
                    )
                    continue

                path_parm_name = _HOUDINI_OUTPUTS[node_category][node_type]

                # get all the nodes for the category and type
                nodes = hou.nodeType(node_category, node_type).instances()

                # iterate over each node
                for node in nodes:

                    # get the evaluated path parm value
                    path = node.parm(path_parm_name).eval()

                    # ensure the output path exists
                    if not os.path.exists(path):
                        continue

                    self.logger.info(
                        "Processing %s node: %s" % (node_type, node.path())
                    )

                    # allow the base class to collect and create the item. it
                    # should know how to handle the output path
                    item = super(HoudiniSessionCollector, self)._collect_file(
                        parent_item, path, frame_sequence=True
                    )

                    # the item has been created. update the display name to
                    # include the node path to make it clear to the user how it
                    # was collected within the current session.
                    item.name = "%s (%s)" % (item.name, node.path())

    def collect_tk_alembicnodes(self, parent_item):
        """
        Checks for an installed `tk-houdini-alembicnode` app. If installed, will
        search for instances of the node in the current session and create an
        item for each one with an output on disk.

        :param parent_item: The item to parent new items to.
        """

        publisher = self.parent
        engine = publisher.engine

        alembicnode_app = engine.apps.get("tk-houdini-alembicnode")
        if not alembicnode_app:
            self.logger.debug(
                "The tk-houdini-alembicnode app is not installed. "
                "Will not attempt to collect those nodes."
            )
            return

        try:
            tk_alembic_nodes = alembicnode_app.get_nodes()
        except AttributeError:
            self.logger.warning(
                "Unable to query the session for tk-houdini-alembicnode "
                "instances. It looks like perhaps an older version of the "
                "app is in use which does not support querying the nodes. "
                "Consider updating the app to allow publishing their outputs."
            )
            return

        # retrieve the work file template defined by the app. we'll set this
        # on the collected alembicnode items for use during publishing.
        work_template = alembicnode_app.get_work_file_template()

        for node in tk_alembic_nodes:

            out_path = alembicnode_app.get_output_path(node)

            if not os.path.exists(out_path):
                continue

            self.logger.info("Processing sgtk_alembic node: %s" % (node.path(),))

            # allow the base class to collect and create the item. it
            # should know how to handle the output path
            item = super(HoudiniSessionCollector, self)._collect_file(
                parent_item, out_path
            )

            # the item has been created. update the display name to
            # include the node path to make it clear to the user how it
            # was collected within the current session.
            item.name = "%s (%s)" % (item.name, node.path())

            if work_template:
                item.properties["work_template"] = work_template

            self._alembic_nodes_collected = True

    def collect_tk_mantranodes(self, parent_item):
        """
        Checks for an installed `tk-houdini-mantranode` app. If installed, will
        search for instances of the node in the current session and create an
        item for each one with an output on disk.

        :param parent_item: The item to parent new items to.
        """

        publisher = self.parent
        engine = publisher.engine

        mantranode_app = engine.apps.get("tk-houdini-mantranode")
        if not mantranode_app:
            self.logger.debug(
                "The tk-houdini-mantranode app is not installed. "
                "Will not attempt to collect those nodes."
            )
            return

        try:
            tk_mantra_nodes = mantranode_app.get_nodes()
        except AttributeError:
            self.logger.warning(
                "Unable to query the session for tk-houdini-mantranode "
                "instances. It looks like perhaps an older version of the "
                "app is in use which does not support querying the nodes. "
                "Consider updating the app to allow publishing their outputs."
            )
            return

        # retrieve the work file template defined by the app. we'll set this
        # on the collected alembicnode items for use during publishing.
        work_template = mantranode_app.get_work_file_template()

        for node in tk_mantra_nodes:

            out_path = mantranode_app.get_output_path(node)

            if not os.path.exists(out_path):
                continue

            self.logger.info("Processing sgtk_mantra node: %s" % (node.path(),))

            # allow the base class to collect and create the item. it
            # should know how to handle the output path
            item = super(HoudiniSessionCollector, self)._collect_file(
                parent_item, out_path, frame_sequence=True
            )

            # the item has been created. update the display name to
            # include the node path to make it clear to the user how it
            # was collected within the current session.
            item.name = "%s (%s)" % (item.name, node.path())

            if work_template:
                item.properties["work_template"] = work_template

            self._mantra_nodes_collected = True

    def collect_adam_materialx_export_nodes(self, parent_item):
        ''' Collects Adam materialX export nodes.

        Args:
            parent_item     (sgItemUI)  : Root item instance
        
        Returns:
            list(sgItemUI)              : List of collected items
        '''
        # Get all the Adam materialX export nodes
        rootNode = hou.node('/out')
        nodes = [node for node in rootNode.allNodes() if node.type().nameComponents()[2] == 'materialXExport']

        # Loop through all the Adam materialX export nodes
        itemCreated = []
        for node in nodes:

            self.logger.info("Processing materialX export node: {}".format(node.path()))

            # Get the node name.
            node_name = node.name()

            # Create the item.
            item = parent_item.create_item(
                "houdini.asset.materialX",
                "Material X",
                node_name
            )

            # Add the node to the item properties.
            item.properties['node'] = node

            # Set the icon.
            iconPath = os.path.join(self.disk_location, os.pardir, "icons", "MaterialX.png")
            item.set_icon_from_path(iconPath)

            # Add the item to the list.
            itemCreated.append(item)
        
        return itemCreated

    def collect_adam_lookdev_asset_nodes(self, parent_item):
        ''' Collects Adam lookdevAsset export nodes.

        Args:
            parent_item     (sgItemUI)  : Root item instance
        
        Returns:
            list(sgItemUI)              : List of collected items
        '''

        # # Create a parent node.
        # nodesItem = parent_item.create_item(
        #     "houdini.asset.lookdev",
        #     "Lookdev Assets",
        #     "Lookdev Assets"
        # )
        # # Set the icon.
        # iconPath = os.path.join(self.disk_location, os.pardir, "icons", "houdini.png")
        # nodesItem.set_icon_from_path(iconPath)

        # # Get all the nodes
        # rootNode = hou.node('/obj')
        # nodes = [node for node in rootNode.allNodes() if node.type().nameComponents()[2] == 'lookdevAsset']

        # # Loop through all the Adam materialX export nodes
        # for node in nodes:

        #     self.logger.info("Processing lookdev asset node: {}".format(node.path()))

        #     # Get the node name.
        #     node_name = node.name()

        #     # Create the item.
        #     nodeItem = parent_item.create_item(
        #         "houdini.asset.lookdev.node",
        #         "Lookdev",
        #         node_name
        #     )

        #     # Add the node to the item properties.
        #     nodeItem.properties['node'] = node

        #     # Set the icon.
        #     iconPath = os.path.join(self.disk_location, os.pardir, "icons", "houdini.png")
        #     nodeItem.set_icon_from_path(iconPath)
        
        #     # Get the toggleExportMtlx parameter.
        #     toggleExportMtlx = node.parm('toggleExportMtlx').evalAsInt()

        #     # If the toggleExportMtlx is on, create the materialX item.
        #     if (toggleExportMtlx):
        #         # Create the item for the materialX.
        #         item = nodeItem.create_item(
        #             "houdini.asset.materialX",
        #             "Material X",
        #             node_name
        #         )
        #         # Add the node to the item properties.
        #         item.properties['node'] = LookdevAssetNode.getMaterialXExportNode(node)
        #         # Set the icon.
        #         iconPath = os.path.join(self.disk_location, os.pardir, "icons", "MaterialX.png")
        #         item.set_icon_from_path(iconPath)

        #     # Get the toggleExportGeometry parameter.
        #     toggleExportGeometry = node.parm('toggleExportGeometry').evalAsInt()

        #     # If the toggleExportGeometry is on, create the geometry item.
        #     if (toggleExportGeometry):
        #         # Create one item per resolution.
        #         resolutions = LookdevAssetNode.getResolutions(node)
        #         for index, resolution in enumerate(resolutions):
        #             # Create the item.
        #             item = nodeItem.create_item(
        #                 "houdini.asset.lookdev.buffers",
        #                 "Buffers",
        #                 resolution
        #             )
        #             item.properties['node']             = node
        #             item.properties['resolution']       = resolution
        #             item.properties['operatorPath']     = resolutions[resolution]
        #             item.properties['resolutionIndex']  = index

        #             # Set the icon.
        #             iconPath = os.path.join(self.disk_location, os.pardir, "icons", "houdini.png")
        #             item.set_icon_from_path(iconPath)



        return nodesItem

    def collect_selectedHDA_nodes(self, parent_item):
        ''' Collects the selected HDA nodes.

        Args:
            parent_item     (sgItemUI)  : Root item instance
        
        Returns:
            sgItemUI                    : the item.
        '''

        # Create a parent node.
        nodesItem = parent_item.create_item(
            "houdini.selection.hda",
            "Digital Assets",
            "Digital Assets"
        )
        # Set the icon.
        iconPath = os.path.join(self.disk_location, os.pardir, "icons", "houdini.png")
        nodesItem.set_icon_from_path(iconPath)

        return nodesItem

        # Get all the selected nodes.
        selectedNodes = hou.selectedNodes()

        # Loop through all the nodes
        for node in selectedNodes:

            self.logger.info("Processing selected nodes: {}".format(node.path()))

            # Get the node name.
            node_name = node.name()

            # Create the item.
            nodeItem = parent_item.create_item(
                "houdini.selection.hda.node",
                "Digital Asset",
                node_name
            )

            # Add the node to the item properties.
            nodeItem.properties['node'] = node

            # Set the icon.
            iconPath = os.path.join(self.disk_location, os.pardir, "icons", "houdini.png")
            nodeItem.set_icon_from_path(iconPath)

        return nodesItem

