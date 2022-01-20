import bpy
import sys

classlist = []

def SearchArmature(obj):
    return (obj if obj.type == 'ARMATURE' else obj.find_armature()) if obj else None

# =============================================================================

class DMR_OP_FixMirroredBoneNames(bpy.types.Operator):
    bl_label = "Fix Mirrored Bone Names"
    bl_idname = 'dmr.fix_mirrored_bone_names'
    bl_description = "Corrects selected bones' names to their mirrored counterpart based on location"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.object is not None and
                context.object.type == 'ARMATURE')
    
    def execute(self, context):
        def Dist(v1, v2):
            vv = (v2[0]-v1[0], v2[1]-v1[1], v2[2]-v1[2])
            return vv[0]*vv[0]+vv[1]*vv[1]+vv[2]*vv[2]
        def FixName(n):
            if n[-2] == '.' or n[-2] == '_' or n[-2] == '-':
                if n[-1] == 'l':
                    return n[:-1]+'r'
                if n[-1] == 'r':
                    return n[:-1]+'l'
                if n[-1] == 'L':
                    return n[:-1]+'R'
                if n[-1] == 'R':
                    return n[:-1]+'L'
        
        obj = context.object
        obj.update_from_editmode()
        
        bones = obj.data.bones
        selbones = [b for b in bones if b.select]
        
        thresh = 0.1
        
        # Check selected bones
        for b in selbones:
            bhead = b.head_local
            btail = b.tail_local
            bhead = (-bhead[0], bhead[1], bhead[2])
            btail = (-btail[0], btail[1], btail[2])
            
            htarget = None
            ttarget = None
            hdist = thresh
            tdist = thresh
            
            if (bhead[0]*bhead[0]) <= 0.001 and (btail[0]*btail[0]) <= 0.001:
                continue
            
            # Test bone against other bones
            for b2 in bones:
                if b2 == b:
                    continue
                hd = Dist(bhead, b2.head_local)
                td = Dist(btail, b2.tail_local)
                
                if hd <= hdist:
                    htarget = b2
                    hdist = hd
                if td <= tdist:
                    ttarget = b2
                    tdist = td
            
            # Hits for both head and tail
            if htarget and ttarget:
                if htarget != ttarget: # Head and tail are not equal
                    #print(b.name, [ttarget.name], FixName(ttarget.name))
                    n = FixName(ttarget.name)
                    if n:
                        b.name = n
                else:
                    #print(b.name, [htarget.name, ttarget.name], FixName(htarget.name))
                    n = FixName(htarget.name)
                    if n:
                        b.name = n
                        
        return {'FINISHED'}
classlist.append(DMR_OP_FixMirroredBoneNames)

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
