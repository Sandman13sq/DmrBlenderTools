bl_info = {
    'name': 'Dmr Animate',
    'author': 'Dreamer13sq',
    'category': 'All',
    'version': (0, 1),
    'blender': (2, 90, 0)
}

if "bpy" in locals():
    import importlib
    importlib.reload(dmr_animate_op)
    importlib.reload(dmr_animate_panel)

import bpy
from . import dmr_animate_op
from . import dmr_animate_panel

classlist = (
    dmr_animate_op.DMRANIM_OP_SetUpVCLayers,
    dmr_animate_op.DMRANIM_OP_MakeControl,
    dmr_animate_op.DMRANIM_OP_QuickOutline,
    dmr_animate_op.DMRANIM_OP_RemoveOutline,
    dmr_animate_op.DMRANIM_OP_ToggleAlt,
    dmr_animate_op.DMRANIM_OP_SetMaterialOutputByName,
    
    dmr_animate_panel.DMR_PT_VCMaterialPanel,
)

def register():
    print('> Loading DmrAnimate...')
    
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()

