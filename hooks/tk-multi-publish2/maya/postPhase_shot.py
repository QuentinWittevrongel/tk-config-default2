import sgtk

from maya import cmds

HookBaseClass = sgtk.get_hook_baseclass()


class PostPhaseShotHook(HookBaseClass):


    def post_validate(self, publish_tree):
        self.logger.debug("Executing post shot validate hook method...")

        # Execute the base class method.
        super(PostPhaseShotHook, self).post_validate(publish_tree)

    def post_publish(self, publish_tree):
        self.logger.debug("Executing post shot publish hook method...")

        # Check if the scene has unsaved changes.
        if(cmds.file(q=True, modified=True)):
            # Reload the scene.
            path = cmds.file(query=True, sn=True)
            cmds.file(path, force=True, open=True)

        # Execute the base class method.
        super(PostPhaseShotHook, self).post_publish(publish_tree)

    def post_finalize(self, publish_tree):
        self.logger.debug("Executing post shot finalize hook method...")

        # Execute the base class method.
        super(PostPhaseShotHook, self).post_finalize(publish_tree)
