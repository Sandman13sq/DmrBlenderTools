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

class DMR_OP_ActionScaleLocation(bpy.types.Operator):
    bl_label = "Scale Action Locations"
    bl_idname = 'dmr.action_scale_location'
    bl_description = "Scale action location keyframes by value. Use when rescaling an entire model by an amount"
    bl_options = {'REGISTER', 'UNDO'}
    
    action : bpy.props.StringProperty(name="Action Name")
    scale : bpy.props.FloatProperty(name="Scale", default=1.0)
    
    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, 'action', bpy.data, 'actions')
        layout.prop(self, 'scale')
    
    def execute(self, context):
        if not self.action in bpy.data.actions.keys():
            #self.report({'WARNING'}, "No action exists with name \"%s\"" % self.action)
            return {'FINISHED'}
        
        action = bpy.data.actions[self.action]
        scale = self.scale
        
        for fc in action.fcurves:
            if ".location" in fc.data_path:
                for k in fc.keyframe_points:
                    k.co_ui[1] *= scale
        
        self.report({'INFO'}, "Action \"%s\" scaled by %s" % (self.action, self.scale))
        
        return {'FINISHED'}
classlist.append(DMR_OP_ActionScaleLocation)

# =============================================================================

class DMR_OP_ActionScaleTime(bpy.types.Operator):
    bl_label = "Scale Action Time"
    bl_idname = 'dmr.action_scale_time'
    bl_description = "Scale action keyframes and frame start and end by value"
    bl_options = {'REGISTER', 'UNDO'}
    
    action : bpy.props.StringProperty(name="Action Name")
    scale : bpy.props.FloatProperty(name="Scale", default=1.0)
    
    def invoke(self, context, event):
        obj = context.object
        if obj and obj.animation_data and obj.animation_data.action:
            action = obj.animation_data.action
            self.action = action.name
        
        return self.execute(context)
    
    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, 'action', bpy.data, 'actions')
        layout.prop(self, 'scale')
    
    def execute(self, context):
        if not self.action in bpy.data.actions.keys():
            #self.report({'WARNING'}, "No action exists with name \"%s\"" % self.action)
            return {'FINISHED'}
        
        action = bpy.data.actions[self.action]
        scale = self.scale
        
        for fc in action.fcurves:
            for k in fc.keyframe_points:
                k.co_ui[0] = (k.co_ui[0] - action.frame_start) * scale + action.frame_start
        
        action.frame_end = (action.frame_end-action.frame_start) * scale + action.frame_start
        
        self.report({'INFO'}, "Action \"%s\" scaled by %s" % (self.action, self.scale))
        
        return {'FINISHED'}
classlist.append(DMR_OP_ActionScaleTime)

# =============================================================================

class DMR_OP_ActionScaleResize(bpy.types.Operator):
    bl_label = "Action Resize"
    bl_idname = 'dmr.action_resize'
    bl_description = "Adjust frame_start and frame_end of an action while maintaining keyframe relative positions"
    bl_options = {'REGISTER', 'UNDO'}
    
    action : bpy.props.StringProperty(name="Action Name")
    frame_start : bpy.props.FloatProperty(name="Frame Start", default=1.0)
    frame_end : bpy.props.FloatProperty(name="Frame End", default=1.0)
    round_frames : bpy.props.BoolProperty(name="Round Frames", default=True)
    
    def invoke(self, context, event):
        obj = context.object
        if obj and obj.animation_data and obj.animation_data.action:
            action = obj.animation_data.action
            self.action = action.name
            
            if not action.use_frame_range:
                action.use_frame_range = True
            
            if action.frame_start == 0 and action.frame_end == 0:
                action.frame_start = context.scene.frame_start
                action.frame_end = context.scene.frame_end
            
            self.frame_start = action.frame_start
            self.frame_end = action.frame_end
        
        return self.execute(context)
    
    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, 'action', bpy.data, 'actions')
        r = layout.row()
        r.prop(self, 'frame_start')
        r.prop(self, 'frame_end')
    
    def execute(self, context):
        if not self.action in bpy.data.actions.keys():
            return {'FINISHED'}
        
        action = bpy.data.actions[self.action]
        lastrange = [action.frame_start, action.frame_end]
        
        d1 = action.frame_end-action.frame_start
        d2 = self.frame_end-self.frame_start
        
        if d1 > 0:
            scale = d2/d1
            f1 = action.frame_start
            
            if self.round_frames:
                for fc in action.fcurves:
                    for k in fc.keyframe_points:
                        k.co_ui[0] = round( (k.co_ui[0]-action.frame_start) * scale + self.frame_start )
            else:
                for fc in action.fcurves:
                    for k in fc.keyframe_points:
                        k.co_ui[0] = (k.co_ui[0]-action.frame_start) * scale + self.frame_start
            
            action.frame_end = (action.frame_end-action.frame_start) * scale + self.frame_start
            action.frame_start = self.frame_start
            
            self.report({'INFO'}, "Action \"%s\" resized from {0} to {1}".format(
                lastrange, [self.frame_start, self.frame_end]))
        
        return {'FINISHED'}
classlist.append(DMR_OP_ActionScaleResize)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in classlist[::-1]:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
