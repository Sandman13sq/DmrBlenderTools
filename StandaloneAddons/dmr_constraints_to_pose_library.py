import bpy

class DMR_OP_ConstraintsToPoseLibrary(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "dmr.constraints_to_pose_library"
    bl_label = "Constraints to Pose Library"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        obj = context.object
        poselib = obj.pose_library
        markers = poselib.pose_markers
        activeindex = markers.active_index
        m = markers[activeindex]
        frame = m.frame
        print([activeindex, m.name, m.frame])
        
        lastaction = obj.animation_data.action
        obj.animation_data.action = poselib
        
        for c in [c for b in obj.pose.bones for c in b.constraints]:
            print([c, c.influence])
            c.keyframe_insert('influence', frame = m.frame)
        obj.animation_data.action = lastaction
        
        return {'FINISHED'}

class DMR_OP_ConstraintsFromPoseLibrary(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "dmr.constraints_from_pose_library"
    bl_label = "Constraints from Pose Library"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        obj = context.object
        poselib = obj.pose_library
        markers = poselib.pose_markers
        activeindex = markers.active_index
        m = markers[activeindex]
        frame = m.frame
        print([activeindex, m.name, m.frame])
        
        for c in [c for b in obj.pose.bones for c in b.constraints]:
            fc = ([fc for fc in poselib.fcurves if fc.data_path == c.path_from_id('influence')]+[None])[0]
            if fc:
                c.influence = fc.evaluate(frame)
        
        return {'FINISHED'}

# Register and add to the "object" menu (required to also use F3 search "Simple Object Operator" for quick access)
def register():
    bpy.utils.register_class(DMR_OP_ConstraintsToPoseLibrary)
    bpy.utils.register_class(DMR_OP_ConstraintsFromPoseLibrary)

def unregister():
    bpy.utils.unregister_class(DMR_OP_ConstraintsToPoseLibrary)
    bpy.utils.unregister_class(DMR_OP_ConstraintsFromPoseLibrary)

if __name__ == "__main__":
    register()
