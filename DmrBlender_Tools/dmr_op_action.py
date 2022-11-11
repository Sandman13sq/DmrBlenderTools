import bpy
import sys

classlist = []

def SearchArmature(obj):
    return (obj if obj.type == 'ARMATURE' else obj.find_armature()) if obj else None

# =============================================================================

class DMR_OP_AddKeyframesForUnkeyedBones(bpy.types.Operator):
    bl_label = "Insert Keyframes for Unkeyed Bones"
    bl_idname = 'dmr.keyframe_unkeyed_bones'
    bl_description = "Inserts keyframes for all bones in keying set without keyframes for current action"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.object is not None and context.object.type == 'ARMATURE')
    
    def execute(self, context):
        kset = context.scene.keying_sets.active
        armobj = context.object
        
        action = armobj.animation_data.action
        fcurvepaths = tuple(fc.data_path for fc in action.fcurves)
        
        hits = []
        for p in tuple(p.data_path for p in kset.paths):
            if p not in fcurvepaths:
                prop = armobj.path_resolve(p)
                if prop:
                    armobj.keyframe_insert(p)
                    hits.append(p)
        print(len(hits))
        
        self.report({'INFO'}, "%d New Keyframes" % len(hits))
        
        return {'FINISHED'}
classlist.append(DMR_OP_AddKeyframesForUnkeyedBones)

# =============================================================================

class DMR_OP_AddActionChannelsToKeyingSet(bpy.types.Operator):
    bl_label = "Add Action Channels To Keying Set"
    bl_idname = 'dmr.add_action_channels_to_keying_set'
    bl_description = "Creates keying set entries using action channels"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        armobj = context.object
        kset = context.scene.keying_sets.active
        action = armobj.animation_data.action
        
        hits = []
        for fc in action.fcurves:
            data_path = fc.data_path
            if data_path not in kset.paths.keys():
                hits.append( kset.paths.add(armobj, data_path) )
        
        self.report({'INFO'}, "%d New Paths" % len(hits))
        
        return {'FINISHED'}
classlist.append(DMR_OP_AddActionChannelsToKeyingSet)

# =============================================================================

class DMR_OP_AddSelectedBonesToKeyingSet(bpy.types.Operator):
    bl_label = "Add Selected Bones To Keying Set"
    bl_idname = 'dmr.add_selected_bones_to_keying_set'
    bl_description = "Creates keying set entries using selected bones"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        armobj = context.object
        kset = context.scene.keying_sets.active
        action = armobj.animation_data.action
        
        hits = []
        for pb in armobj.pose.bones:
            if pb.bone.select:
                propnames = ['location', 'scale']
                if pb.rotation_mode == 'QUATERNION':
                    propnames.append('rotation_quaternion')
                else:
                    propnames.append('rotation_euler')
                
                for prop in propnames:
                    data_path = pb.path_from_id(prop)
                    if data_path not in kset.paths.keys():
                        hits.append( kset.paths.add(armobj, data_path) )
        
        self.report({'INFO'}, "%d New Paths" % len(hits))
        
        return {'FINISHED'}
classlist.append(DMR_OP_AddSelectedBonesToKeyingSet)

# =============================================================================

class DMR_OP_GroupActionChannelsByPathName(bpy.types.Operator):
    bl_label = "Group Channels By Path Name"
    bl_idname = 'dmr.group_channels_by_path'
    bl_description = "Groups all channels by their path"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    
    def execute(self, context):
        action = context.object.animation_data.action
        
        addedgroups = 0
        addedbones = 0
        
        actiongroups = action.groups
        for fc in action.fcurves:
            datapath = fc.data_path
            idname = datapath[datapath.rfind('"', 0, datapath.rfind('"')-1)+1:datapath.rfind('"')]
            if idname not in actiongroups.keys():
                actiongroups.new(idname)
                addedgroups += 1
            if fc.group != actiongroups[idname]:
                fc.group = actiongroups[idname]
                addedbones += 1
        
        self.report({'INFO'}, "%d New Groups, %d Changed Groups" % (addedgroups, addedbones))
        
        return {'FINISHED'}
classlist.append(DMR_OP_GroupActionChannelsByPathName)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
