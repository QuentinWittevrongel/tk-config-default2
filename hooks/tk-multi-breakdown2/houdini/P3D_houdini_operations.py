# Copyright (c) 2021 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import os
import sgtk
import hou

# Import the adam pipe nodes.
import adamPipe

from adamScripts import DigitalAssetsManager

HookBaseClass = sgtk.get_hook_baseclass()


class BreakdownSceneOperations(HookBaseClass):
    """
    Breakdown operations for Houdini.

    This implementation handles detection of :
    - alembic node paths.
    - materialX node paths.
    """

    def getNodes(self, category, nodeTypeName, filenameParameter):
        ''' Get all the nodes of a given type in the current file.

        Args:
            category            (:class:`hou.NodeTypeCategory()`)   : The category of the node type.
            nodeTypeName        (str)                               : The name of the node type.
            filenameParameter   (str)                               : The name of the parameter that contains
                                                                    the file path.

        Returns:
            list(dict)                                              : A list of dictionaries containing the node name
                                                                    and path.
        '''
        items = []
        # Get a list of all nodes in the file.
        nodesObjects = hou.nodeType(category, nodeTypeName)
        if(not nodesObjects):
            return items
        # Get the instances of the node type.
        nodes = nodesObjects.instances()
        # Return an item for each node found. The breakdown app will check
        # the paths of each looking for a template match and a newer version.
        for node in nodes:

            # Skip if the node is inside a locked network.
            if(node.isInsideLockedHDA()):
                continue

            # Get the file path parameter.
            parm = node.parm(filenameParameter)
            # Check if the parameter is referenced.
            if(parm.getReferencedParm() != parm):
                continue

            # Get the file path registered in the node.
            path = os.path.normpath(parm.evalAsString())

            extra_data = {
                "parm"         : filenameParameter,
            }

            items.append(
                {
                    "node_name"     : node.path(),
                    "node_type"     : nodeTypeName,
                    "path"          : path,
                    "extra_data"    : extra_data,
                }
            )

        # Return the list of items.
        return items

    def scan_scene(self):
        """
        The scan scene method is executed once at startup and its purpose is
        to analyze the current scene and return a list of references that are
        to be potentially operated on.

        The return data structure is a list of dictionaries. Each scene reference
        that is returned should be represented by a dictionary with three keys:

        - "node_name": The name of the 'node' that is to be operated on. Most DCCs have
          a concept of a node, path or some other way to address a particular
          object in the scene.
        - "node_type": The object type that this is. This is later passed to the
          update method so that it knows how to handle the object.
        - "path": Path on disk to the referenced object.
        - "extra_data": Optional key to pass some extra data to the update method
          in case we'd like to access them when updating the nodes.

        Toolkit will scan the list of items, see if any of the objects matches
        a published file and try to determine if there is a more recent version
        available. Any such versions are then displayed in the UI as out of date.
        """

        items = []

        # Get all the ADAM Pipeline nodes in the current file.

        # Scene Description Loader nodes.
        items.extend(self.getNodes(
            hou.objNodeTypeCategory(),
            "sceneDescriptionLoader::2.0",
            "filePath"
        ))

        # Scene Animation Loader nodes.
        items.extend(self.getNodes(
            hou.objNodeTypeCategory(),
            "sceneAnimation::2.0",
            "filePath"
        ))

        # Asset Deformed Loader nodes both for the geo and the materialX.
        items.extend(self.getNodes(
            hou.objNodeTypeCategory(),
            "assetDeformedLoader::1.0",
            "geometryFilePath"
        ))
        items.extend(self.getNodes(
            hou.objNodeTypeCategory(),
            "assetDeformedLoader::1.0",
            "materialXFilePath"
        ))

        # Asset Animation Loader nodes both for the geo and the materialX.
        items.extend(self.getNodes(
            hou.objNodeTypeCategory(),
            "assetAnimationLoader::2.0",
            "geometryFilePath"
        ))
        items.extend(self.getNodes(
            hou.objNodeTypeCategory(),
            "assetAnimationLoader::2.0",
            "materialXFilePath"
        ))

        # Get the alembic archives.
        items.extend(self.getNodes(
            hou.objNodeTypeCategory(),
            "alembicarchive",
            "fileName"
        ))

        # Get all the loaded HDA published.
        # Get the engine.
        engine = sgtk.platform.current_engine()
        # Define a list of templates to look for.
        templateNames = ['houdini_sequence_digitalAsset_publish']
        # Get the templates.
        templates = []
        for templateName in templateNames:
            templates.append( engine.get_template_by_name(templateName) )
        
        # Get all the nodes inside the OBJ context.
        nodes = hou.node('/obj').allSubChildren(recurse_in_locked_nodes=False)
        # Loop over the nodes.
        for node in nodes:
            # Check if the node is an HDA.
            definition = node.type().definition()
            if(not definition):
                continue
            
            # Get the library path of the node.
            libraryPath = definition.libraryFilePath()
            # Check if one of the template is validated.
            for template in templates:
                if(template.validate(libraryPath)):

                    # Add the node to the list.
                    items.append({
                        "node_name"     : node.path(),
                        "node_type"     : "HDA",
                        "path"          : libraryPath,
                        "extra_data"    : {},
                    })
                    break


        # # Get all the alembic nodes in the current file.
        # items.extend(self.getNodes(
        #     hou.sopNodeTypeCategory(),
        #     "alembic",
        #     "fileName"
        # ))

        # # Get all the materialX nodes in the current file.
        # items.extend(self.getNodes(
        #     hou.ropNodeTypeCategory(),
        #     "arnold::materialx",
        #     "filename"
        # ))

        # Return the list of items.
        return items

    def update(self, item):
        """
        Perform replacements given a number of scene items passed from the app.

        Once a selection has been performed in the main UI and the user clicks
        the update button, this method is called.

        :param item: Dictionary on the same form as was generated by the scan_scene hook above.
                     The path key now holds the path that the node should be updated *to* rather than the current path.
        """
        # Extract data from the item.
        nodePath    = item["node_name"]
        nodeType    = item["node_type"]
        path        = item["path"]

        extraData   = item["extra_data"]
        parm        = extraData.get("parm", None)

        # Get the node.
        node = hou.node(nodePath)
        if(not node):
            self.logger.error("Node '{}' not found.".format(nodePath))
            return

        # Format the path.
        path = os.path.normpath(path).replace("\\", "/")

        # Update the HDA.
        if(nodeType == "HDA"):
            self.logger.debug(
                "Updating HDA node '{}' to: {}".format(nodePath, path)
            )
            DigitalAssetsManager.updateHDA(node, path)
            

        # Update the node.
        elif(nodeType == "ADAM::sceneDescriptionLoader::2.0"):
            self.logger.debug(
                "Updating Scene Description Loader node '{}' to: {}".format(nodePath, path)
            )
            adamPipe.SceneDescriptionLoaderNode.updateFilePath(node, path)
        

        elif(nodeType == "sceneAnimation::2.0"):
            self.logger.debug(
                "Updating Scene Animation Loader node '{}' to: {}".format(nodePath, path)
            )
            adamPipe.SceneAnimationNode.updateFilePath(node, path)
        

        elif(nodeType == "assetDeformedLoader::1.0"):
            self.logger.debug(
                "Updating Asset Deformed Loader node '{}' to: {}".format(nodePath, path)
            )
            if(parm == "geometryFilePath"):
                adamPipe.AssetDeformedLoaderNode.updateGeometryFilePath(node, path)
            elif(parm == "materialXFilePath"):
                adamPipe.AssetDeformedLoaderNode.updateMaterialXFilePath(node, path)
        

        elif(nodeType == "assetAnimationLoader::2.0"):
            self.logger.debug(
                "Updating Asset Animation Loader node '{}' to: {}".format(nodePath, path)
            )
            if(parm == "geometryFilePath"):
                adamPipe.AssetAnimationLoaderNode.updateGeometryFilePath(node, path)
            elif(parm == "materialXFilePath"):
                adamPipe.AssetAnimationLoaderNode.updateMaterialXFilePath(node, path)

        elif(nodeType == "alembicarchive"):
            self.logger.debug(
                "Updating Alembic Archive node '{}' to: {}".format(nodePath, path)
            )
            node.parm(parm).set(path)
            # Press the button to update the hierarchy.
            node.parm("buildHierarchy").pressButton()

        # if(node_type == "alembic"):
        #     alembic_node = hou.node(node_name)
        #     self.logger.debug(
        #         "Updating alembic node '{}' to: {}".format(node_name, path)
        #     )
        #     alembic_node.parm("fileName").set(path)
        
        # elif(node_type == "arnold::materialx"):
        #     materialx_node = hou.node(node_name)
        #     self.logger.debug(
        #         "Updating materialX node '{}' to: {}".format(node_name, path)
        #     )
        #     materialx_node.parm("filename").set(path)
