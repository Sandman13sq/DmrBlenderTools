bl_info = {
    'name': 'Dmr Animate',
    'author': 'Dreamer13sq',
    'category': 'All',
    'version': (0, 1),
    'blender': (3, 0, 0)
}

import bpy

modulesNames = [
    'utilities',
    'dmr_hotmenu',
    
    'dmr_op_action',
    'dmr_op_animate',
    
    'dmr_panel_action',
    'dmr_panel_animate',
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
    for currentModuleName in reversed(modulesFullNames.values()):
        if currentModuleName in sys.modules:
            if hasattr(sys.modules[currentModuleName], 'unregister'):
                sys.modules[currentModuleName].unregister()
 
if __name__ == "__main__":
    register()
