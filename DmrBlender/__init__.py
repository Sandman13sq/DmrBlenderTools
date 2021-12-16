#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#  All rights reserved.
#  ***** GPL LICENSE BLOCK *****

# <pep8 compliant>

bl_info = {
    'name': 'Dmr Blender Tools',
    'author': 'Dreamer13sq',
    }

# can use importlib.reload here instead 
import bpy
#from . import utilities, dmr_hotmenu, dmr_misc_op, dmr_pose_op, dmr_sculpt_op, dmr_shapekey_op, dmr_vcolor_op, dmr_vertex_op, dmr_vgroup_op, dmr_pose_panel, dmr_shapekey_panel, dmr_vcolor_panel, dmr_vgroup_panel;

modulesNames = [
    'utilities',
    'dmr_hotmenu',
    
    'dmr_misc_op',
    'dmr_pose_op',
    'dmr_sculpt_op',
    'dmr_shapekey_op',
    'dmr_vcolor_op',
    'dmr_vertex_op',
    'dmr_vgroup_op',
    
    'dmr_pose_panel',
    'dmr_shapekey_panel',
    'dmr_vcolor_panel',
    'dmr_vgroup_panel',
]

import sys
import importlib

print('> Loading %s...' % bl_info['name']);
 
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
 
def register():
    for currentModuleName in modulesFullNames.values():
        if currentModuleName in sys.modules:
            if hasattr(sys.modules[currentModuleName], 'register'):
                sys.modules[currentModuleName].register()
 
def unregister():
    for currentModuleName in modulesFullNames.values():
        if currentModuleName in sys.modules:
            if hasattr(sys.modules[currentModuleName], 'unregister'):
                sys.modules[currentModuleName].unregister()
 
if __name__ == "__main__":
    register()

print(modulesNames)