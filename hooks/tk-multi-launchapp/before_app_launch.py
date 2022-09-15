# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Before App Launch Hook

This hook is executed prior to application launch and is useful if you need
to set environment variables or run scripts as part of the app initialization.
"""

import os
import tank


class BeforeAppLaunch(tank.Hook):
    """
    Hook to set up the system prior to app launch.
    """

    def addToEnvironmentBegin(self, env, path):
        """ Add a path at the begin of an enviroment variable.

        :param env: (str) The name of the environment to update.
        :param path: (str) The path to add.
        """
        if(env in os.environ):
            os.environ[env] = '%s;%s' % (path, os.environ[env])
        else:
            os.environ[env] = '%s;&' % path

    def addToEnvironmentEnd(self, env, path):
        """ Add a path at the end of an enviroment variable.

        :param env: (str) The name of the environment to update.
        :param path: (str) The path to add.
        """
        if(env in os.environ):
            os.environ[env] = '%s;%s' % (os.environ[env], path)
        else:
            os.environ[env] = '&;%s' % path

    def execute(
        self, app_path, app_args, version, engine_name, software_entity=None, **kwargs
    ):
        """
        The execute function of the hook will be called prior to starting the required application

        :param app_path: (str) The path of the application executable
        :param app_args: (str) Any arguments the application may require
        :param version: (str) version of the application being run if set in the
            "versions" settings of the Launcher instance, otherwise None
        :param engine_name (str) The name of the engine associated with the
            software about to be launched.
        :param software_entity: (dict) If set, this is the Software entity that is
            associated with this launch command.
        """

        # accessing the current context (current shot, etc)
        # can be done via the parent object
        #
        # > multi_launchapp = self.parent
        # > current_entity = multi_launchapp.context.entity

        # you can set environment variables like this:
        # os.environ["MY_SETTING"] = "foo bar"
        self.logger.info("* Config Hook : Tank Multi Launch Application *")
        # self.logger.info(app_path)
        # self.logger.info(app_args)
        # self.logger.info(software_entity)
        # self.logger.info(version)
        # self.logger.info(engine_name)

        self.logger.info("* Config Hook : Launch : %s %s *" % (software_entity["code"], version))

        # Add test line.

        # Get the application launcher.
        multi_launchapp = self.parent
        # Get the current project.
        projectName     = multi_launchapp.context.project["name"]

        # Set up the OCIO config file.
        os.environ["OCIO"] = "Z:\\OpenColorIO-Configs\\aces_1.2\\config.ocio"

        # Set up the environment variable for maya.
        if(software_entity["code"] == "Maya"):

            # Add farmTools.
            self.addToEnvironmentEnd("PYTHONPATH", "Z:\\P3DTools\\productionPackages\\farmTools\\0.4.0")

            # Add Studio Library.
            self.addToEnvironmentEnd("PYTHONPATH", "Z:\\P3DTools\\productionPackages\\studiolibrary\\2.9.6.b3\\src")

            # Set up for version.
            if(version == "2022"):
                # Add Frankenstein.
                self.addToEnvironmentEnd("MAYA_MODULE_PATH", "Z:\\P3DTools\\productionPackages\\frankenstein\\0.8.1\\2022\\module")
                # Add ngSkin Tools.
                self.addToEnvironmentEnd("MAYA_MODULE_PATH", "Z:\\P3DTools\\productionPackages\\ngskintools\\2.0.33\\ngskintools2\\Contents\\module")

            elif(version == "2023"):
                # Add Frankenstein.
                self.addToEnvironmentEnd("MAYA_MODULE_PATH", "Z:\\P3DTools\\productionPackages\\frankenstein\\0.8.1\\windows\\2023\\module")
                # Add ngSkin Tools.
                self.addToEnvironmentEnd("MAYA_MODULE_PATH", "Z:\\P3DTools\\productionPackages\\ngskintools\\2.0.39\\ngskintools2\\2023\\module")
            else:
                pass
        
        elif(software_entity["code"] == "Houdini"):
            # Force the autodesk licence server.
            self.addToEnvironmentEnd('ADSKFLEX_LICENSE_FILE', '27001@lic-sp')

            if(version == "19.0.383"):
                pass
            elif(version == "19.5.303"):
                # Add the farm tools.
                self.addToEnvironmentEnd('HOUDINI_OTLSCAN_PATH', 'Z:\\P3DTools\\productionPackages\\farmTools\\0.4.0\\farmTools\\dccs\\houdini\\hda')                
                self.addToEnvironmentEnd('PYTHONPATH', 'Z:\\P3DTools\\productionPackages\\farmTools\\0.4.0')
                self.addToEnvironmentBegin('HOUDINI_MENU_PATH', 'Z:\\P3DTools\\productionPackages\\farmTools\\0.4.0\\farmTools\\dccs\\houdini\\menus')
        
                # Add P3D HDA.
                self.addToEnvironmentEnd('HOUDINI_OTLSCAN_PATH', 'Z:\\P3DTools\\productionPackages\\houdini\\otls')
                self.addToEnvironmentEnd('HOUDINI_VEX_PATH', 'Z:\\P3DTools\\productionPackages\\houdini\\vex')

                # Add P3D Hair Tools.
                self.addToEnvironmentEnd('HOUDINI_OTLSCAN_PATH', 'Z:\\P3DTools\\productionPackages\\houdiniHairTools\\hda')
                self.addToEnvironmentEnd('HOUDINI_VEX_PATH', 'Z:\\P3DTools\\productionPackages\\houdiniHairTools\\vex')

                # Add Arnold render.
                self.addToEnvironmentEnd('PATH', 'C:\\Program Files\\Autodesk\\Arnold\\htoa-6.1.3.2_r2bc6797_houdini-19.5.303\\scripts\\bin')
                self.addToEnvironmentBegin('HOUDINI_PATH', 'C:\\Program Files\\Autodesk\\Arnold\\htoa-6.1.3.2_r2bc6797_houdini-19.5.303')
        
        elif(software_entity["code"] == "Nuke"):
            self.addToEnvironmentBegin('NUKE_PATH', 'Z:\\P3DTools\\productionPackages\\nukeGizmos')
            self.addToEnvironmentBegin('PYTHONPATH', 'Z:\\P3DTools\\productionPackages\\farmTools\\0.4.0')
            self.addToEnvironmentEnd('NUKE_PATH', 'Z:\\P3DTools\\productionPackages\\farmTools\\0.4.0\\farmTools\\dccs\\nuke\\plugins')

            if(projectName == "KML"):
                self.addToEnvironmentEnd('NUKE_PATH', 'O:\\shows\\KML\\library\\compositing\\.nuke\\ProductionTools')

        elif(software_entity["code"] == "Guerilla"):
            pass
        elif(software_entity["code"] == "Painter"):
            pass
        elif(software_entity["code"] == "Photoshop"):
            pass
        elif(software_entity["code"] == "After Effects"):
            pass
        elif(software_entity["code"] == "Blender"):
            pass
        elif(software_entity["code"] == "Z Brush"):
            pass
        elif(software_entity["code"] == "Marvelous Designer"):
            pass
        elif(software_entity["code"] == "Speed Tree"):
            pass
        elif(software_entity["code"] == "Premiere Pro"):
            pass
        else:
            pass
