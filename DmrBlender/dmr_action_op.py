import bpy

classlist = [];

# =============================================================================

class DMR_OP_PlaybackRangeFromAction(bpy.types.Operator):
    bl_label = "Playback Range from Action"
    bl_idname = 'dmr.playback_range_from_action'
    bl_description = "Sets playback range to range of keyframes for action"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.object is not None)
    
    def execute(self, context):
        obj = context.object
        if obj:
            if obj.animation_data:
                action = obj.animation_data.action
                framerange = action.frame_range
                context.scene.frame_start = framerange[0]+1
                context.scene.frame_end = framerange[1]-1
                        
        return {'FINISHED'}
classlist.append(DMR_OP_PlaybackRangeFromAction)

# =============================================================================

class DMR_OP_ActionWriteFrameRange(bpy.types.Operator):
    bl_label = "Store Frame Range"
    bl_idname = 'dmr.frame_range_store'
    bl_description = 'Saves frame range in action custom properties';
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        action = context.object.animation_data.action
        action["frame_start"] = scene.frame_start
        action["frame_end"] = scene.frame_end
        return {'FINISHED'}

classlist.append(DMR_OP_ActionWriteFrameRange);

# =============================================================================

class DMR_OP_ActionRestoreFrameRange(bpy.types.Operator):
    bl_label = "Apply Frame Range"
    bl_idname = 'dmr.frame_range_restore'
    bl_description = 'Applies frame range stored in action';
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        action = context.object.animation_data.action
        scene.frame_start = action['frame_start']
        scene.frame_end = action['frame_end']
        return {'FINISHED'}

classlist.append(DMR_OP_ActionRestoreFrameRange);

# =============================================================================

class DMR_OP_ObjectSyncAction(bpy.types.Operator):
    bl_label = "Sync Action to Active Object"
    bl_idname = 'dmr.object_sync_action'
    bl_description = 'Sets action of all objects to match active';
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        object = context.object
        if object:
            if object.animation_data.action:
                action = object.animation_data.action
                for obj in [x for x in bpy.data.objects if x.type in {'MESH', 'ARMATURE'}]:
                    try:
                        obj.animation_data.action = action;
                    except:
                        continue
        return {'FINISHED'}

classlist.append(DMR_OP_ObjectSyncAction);

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
