bl_info = {
    'name': 'DmrBlender Tools',
    'description': 'A collection of operators and panels to speed up efficiency in Blender.',
    'author': 'Dreamer13sq',
    'version': (1, 0),
    'blender': (3, 0, 0),
    'category': 'All',
    'version': (0, 1),
    'support': 'COMMUNITY',
    'doc_url': 'https://github.com/Dreamer13sq/DmrBlenderTools/wiki'
}

# can use importlib.reload here instead 
import bpy
#from . import utilities, dmr_hotmenu, dmr_misc_op, dmr_pose_op, dmr_sculpt_op, dmr_shapekey_op, dmr_vcolor_op, dmr_vertex_op, dmr_vgroup_op, dmr_pose_panel, dmr_shapekey_panel, dmr_vcolor_panel, dmr_vgroup_panel

modulesNames = [
    'utilities',
    'dmr_hotmenu',
    
    'dmr_op_misc',
    'dmr_op_armature',
    'dmr_op_sculpt',
    'dmr_op_shapekey',
    'dmr_op_vcolor',
    'dmr_op_vgroup',
    'dmr_op_uv',
    'dmr_op_object',
    'dmr_op_pose',
    'dmr_op_image',
    'dmr_op_action',
    
    'dmr_panel_armature',
    'dmr_panel_shapekey',
    'dmr_panel_vcolor',
    'dmr_panel_vgroup',
    'dmr_panel_uv',
    'dmr_panel_action',
]

import sys
import importlib

print('> Loading %s...' % bl_info['name'])
 
modulesFullNames = {}
for currentModuleName in modulesNames:
    if 'DEBUG_MODE' in sys.argv:
        modulesFullNames[currentModuleName] = ('{}'.format(currentModuleName))
    else:
        modulesFullNames[currentModuleName] = ('{}.{}'.format(__name__, currentModuleName))

for i in [0, 0]:
    for currentModuleFullName in modulesFullNames.values():
        if currentModuleFullName in sys.modules:
            importlib.reload(sys.modules[currentModuleFullName])
        else:
            globals()[currentModuleFullName] = importlib.import_module(currentModuleFullName)
            setattr(globals()[currentModuleFullName], 'modulesNames', modulesFullNames)

# =============================================================================

def register():
    for currentModuleName in modulesFullNames.values():
        if currentModuleName in sys.modules:
            if hasattr(sys.modules[currentModuleName], 'register'):
                sys.modules[currentModuleName].register()
 
def unregister():
    for currentModuleName in list(modulesFullNames.values())[::-1]:
        if currentModuleName in sys.modules:
            if hasattr(sys.modules[currentModuleName], 'unregister'):
                sys.modules[currentModuleName].unregister()
 
if __name__ == "__main__":
    register()
