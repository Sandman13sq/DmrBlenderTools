import bpy
import sys

classlist = []

def SearchArmature(startingobject):
    o = startingobject
    if o:
        if o.type == 'ARMATURE':
            return o
        if o.parent and o.parent.type == 'ARMATURE':
            return o.parent
        try:
            return [m for m in o.modifiers if (m.type == 'ARMATURE' and m.object)][-1].object
        except:
            return None
    return None

# =============================================================================

class DMR_OP_FixRightBoneNames(bpy.types.Operator):
    bl_label = "Fix Right Bone Names"
    bl_idname = 'dmr.fix_right_bone_names'
    bl_description = "Corrects newly created right side bones' names to their left counterpart"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.object is not None and
                context.object.type == 'ARMATURE')
    
    def execute(self, context):
        active = bpy.context.view_layer.objects.active
        if active:
            lastobjectmode = bpy.context.active_object.mode
            bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
            
            bones = active.data.bones
            thresh = 0.01
            leftbones = [b for b in bones if b.head_local[0] >= thresh]
            rightbones = [b for b in bones if b.head_local[0] <= -thresh]
            for b in rightbones:
                loc = b.head_local.copy()
                loc[0] *= -1
                currdist = 100
                currbone = None
                for b2 in leftbones:
                    b2dist = (b2.head_local - loc).length
                    if b2dist < currdist:
                        currbone = b2
                        currdist = b2dist
                if currbone != None:
                    b.name = currbone.name[:-1] + 'r'
            bpy.ops.object.mode_set(mode = lastobjectmode)
                        
        return {'FINISHED'}
classlist.append(DMR_OP_FixRightBoneNames)

# =============================================================================

class DMR_OP_BoneNamesByPosition(bpy.types.Operator):
    bl_idname = "dmr.bone_names_by_position"
    bl_label = "Bone Names by Position"
    bl_description = "Set bone names by order in armature or order in parent-child chain"
    bl_options = {'REGISTER', 'UNDO'}
    
    basename: bpy.props.StringProperty(
        name='Format Name', default = 'link_%s',
        description='String used to insert interative name into. "\%" character is necessary'
    )
    
    locationtype: bpy.props.EnumProperty(
        name="Location Method",
        description="Method to sort bone names",
        items = (
            ('armature', 'Default', 'Sort using armature hierarchy'),
            ('x', 'X Location', 'Sort using X'),
            ('y', 'Y Location', 'Sort using Y'),
            ('z', 'Z Location', 'Sort using Z'),
        ),
        default='armature',
    )
    
    bonesuffix: bpy.props.EnumProperty(
        name="Bone Suffix",
        description="String to append to the end of bone name",
        items = (
            ('upper', 'Uppercase', 'Suffix = "A", "B", "C", ...'),
            ('lower', 'Lowercase', 'Suffix = "a", "b", "c", ...'),
            ('zero', 'From 0', 'Suffix = "0", "1", "2", ...'),
            ('one', 'From 1', 'Suffix = "1", "2", "3", ...'),
        ),
        default='zero',
    )
    
    reversedsort: bpy.props.BoolProperty(
        name="Reverse Sort",
        description="Reverse order of location method",
        default=False,
    )
    
    @classmethod
    def poll(cls, context):
        return (context.object is not None and
                context.object.type == 'ARMATURE')
    
    def execute(self, context):
        if '%s' not in self.basename:
            return {'FINISHED'}
        
        object = context.object
        bones = object.data.bones
        
        lastobjectmode = object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        targetbones = [b for b in bones if b.select]
        
        # Sort bones
        ltype = self.locationtype
        if ltype == 'x':
            targetbones.sort(key = lambda b: b.head_local[0])
        elif ltype == 'y':
            targetbones.sort(key = lambda b: b.head_local[1])
        elif ltype == 'z':
            targetbones.sort(key = lambda b: b.head_local[2])
        
        if self.reversedsort:
            targetbones.reversed()
        
        # Generate suffixes
        suffixmode = self.bonesuffix
        if suffixmode == 'upper':
            suffixlist = list('ABCDEFG')
        elif suffixmode == 'lower':
            suffixlist = list('abcdefg')
        elif suffixmode == 'zero':
            suffixlist = range(0, 10)
        elif suffixmode == 'one':
            suffixlist = range(1, 10)
        
        oldnames = [b.name for b in targetbones]
        newnames = [(self.basename % suffixlist[i]) for i in range(0, len(targetbones))]
        
        for i, b in enumerate(targetbones):
            b.name = '__temp%s__' % i
        
        for i, b in enumerate(targetbones):
            print("%s -> %s" % (oldnames[i], newnames[i]))
            b.name = newnames[i]
        print()
        
        bpy.ops.object.mode_set(mode = lastobjectmode)
        
        return {'FINISHED'}
classlist.append(DMR_OP_BoneNamesByPosition)

# =============================================================================

class DMR_OP_BoneSelectIndex(bpy.types.Operator):
    bl_label = "Select Bone by Index"
    bl_idname = 'dmr.bone_select_index'
    bl_description = "Selects bone by index"
    bl_options = {'REGISTER', 'UNDO'}
    
    index : bpy.props.IntProperty(
        name = 'Bone Index', default = 0,
        description = 'Index of bone to select'
    )
    
    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'ARMATURE' and obj.mode in {'EDIT', 'POSE'}
    
    def execute(self, context):
        active = context.object
        active.update_from_editmode()
        
        if active.mode == 'EDIT':
            bones = active.data.edit_bones
            bones.active = bones[self.index]
        
        bones = active.data.bones
        bones[self.index].select = True
        bones.active = bones[self.index]
        active.update_from_editmode()
                        
        return {'FINISHED'}
classlist.append(DMR_OP_BoneSelectIndex)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
