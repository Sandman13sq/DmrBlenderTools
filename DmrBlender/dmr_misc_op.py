import bpy
import os

classlist = []

# =============================================================================

class DMR_OP_Reset3DCursor(bpy.types.Operator):
    bl_label = "Reset 3D Cursor"
    bl_idname = 'dmr.reset_3d_cursor'
    bl_description = 'Resets 3D cursor to (0, 0, 0)'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.scene.cursor.location = (0.0, 0.0, 0.0)
        return {'FINISHED'}
classlist.append(DMR_OP_Reset3DCursor)

# =============================================================================

class DMR_OP_Reset3DCursorX(bpy.types.Operator):
    bl_label = "Zero 3D Cursor X"
    bl_idname = 'dmr.reset_3d_cursor_x'
    bl_description = 'Resets x coordinate of 3D Cursor'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.scene.cursor.location[0] = 0.0
        return {'FINISHED'}
classlist.append(DMR_OP_Reset3DCursorX)

# =============================================================================

class DMR_OP_ToggleEditModeWeights(bpy.types.Operator):
    bl_label = "Toggle Edit Mode Weights"
    bl_idname = 'dmr.toggle_editmode_weights'
    bl_description = 'Toggles Weight Display for Edit Mode'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        bpy.context.scene.tool_settings.vertex_group_user = 'ALL'
        bpy.context.space_data.overlay.show_weight = not bpy.context.space_data.overlay.show_weight
        
        return {'FINISHED'}
classlist.append(DMR_OP_ToggleEditModeWeights)

# =============================================================================

class DMR_OP_TogglePoseAll(bpy.types.Operator):
    bl_label = "Toggle Pose Mode"
    bl_idname = 'dmr.toggle_pose_all'
    bl_description = 'Toggles Pose Mode for all armatures'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        checked = []
        
        for o in context.scene.objects:
            if o.type == 'ARMATURE':
                if o.data in checked:
                    continue
                checked.append(o.data)
                
                armature = o.data
                if armature.pose_position == 'REST':
                    armature.pose_position = 'POSE'
                else:
                    armature.pose_position = 'REST'
        return {'FINISHED'}
classlist.append(DMR_OP_TogglePoseAll)

# =============================================================================

class DMR_OP_TogglePoseParent(bpy.types.Operator):
    bl_label = "Toggle Pose Mode Parent"
    bl_idname = 'dmr.toggle_pose_parent'
    bl_description = "Toggles Pose Mode for current armature or active object's parent armature"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        active = bpy.context.active_object
        armature = None
        
        # Find Armature (of active or active's parent)
        if active:
            if active.type == 'ARMATURE': armature = active
            elif active.parent:
                if active.parent.type == 'ARMATURE': armature = active.parent
            elif active.type in ['MESH']:
                if active.modifiers:
                    for m in active.modifiers:
                        if m.type == 'ARMATURE':
                            if m.object and m.object.type == 'ARMATURE':
                                armature = m.object
        
        if armature:
            if armature.data.pose_position == 'REST':
                armature.data.pose_position = 'POSE'
            else:
                armature.data.pose_position = 'REST'
        return {'FINISHED'}
classlist.append(DMR_OP_TogglePoseParent)

# =============================================================================

class DMR_OP_ToggleAnimation(bpy.types.Operator):
    bl_label = "Play/Pause Animation"
    bl_idname = 'dmr.play_anim'
    bl_description = 'Toggles animation playback'
    
    def execute(self, context):
        bpy.ops.screen.animation_play()
        return {'FINISHED'}
classlist.append(DMR_OP_ToggleAnimation)

# =============================================================================

class DMR_OP_ImageReloadAll(bpy.types.Operator):
    bl_label = "Reload All Images"
    bl_idname = 'dmr.image_reload'
    bl_description = 'Reloads all images from files'
    
    def execute(self, context):
        for image in bpy.data.images:
            image.reload()
        
        return {'FINISHED'}
classlist.append(DMR_OP_ImageReloadAll)

# =============================================================================

class DMR_OP_QuickAutoSmooth(bpy.types.Operator):
    bl_label = "Quick Auto Smooth"
    bl_idname = 'dmr.quick_auto_smooth'
    bl_description = "Turns on auto smooth and sets angle to 180 degrees for selected objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.object is not None)
    
    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                obj.data.use_auto_smooth = 1
                obj.data.auto_smooth_angle = 3.14159
                for p in obj.data.polygons:
                    p.use_smooth = 1
                        
        return {'FINISHED'}
classlist.append(DMR_OP_QuickAutoSmooth)

# =============================================================================

class DMR_OP_ToggleMirror(bpy.types.Operator):
    bl_label = "Toggle Mirror Modifier"
    bl_idname = 'dmr.toggle_mirror_modifier'
    bl_description = "Toggles viewport visibility for all mirror modifiers"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.object is not None)
    
    def execute(self, context):
        for obj in bpy.data.objects:
            if obj.hide_viewport:
                continue
            if obj.type == 'MESH':
                if obj.modifiers:
                    for m in obj.modifiers:
                        if m.type == 'MIRROR':
                            m.show_viewport = not m.show_viewport
                    
                        
        return {'FINISHED'}
classlist.append(DMR_OP_ToggleMirror)

# =============================================================================

class DMR_OP_RenameNodeInput(bpy.types.Operator):
    bl_label = "Rename Node Input (May not save correctly)"
    bl_idname = 'dmr.rename_node_input'
    bl_description = 'Changes name of node input. (NOTE: may not keep changes after reloading file)'
    bl_options = {'REGISTER', 'UNDO'}
    
    ioindex : bpy.props.EnumProperty(
        name="Target Input",
        description="Name of input to rename",
        items=lambda s, context: [
            ( (str(i), '[%d]: %s' % (i, io.name), 'Rename input %d "%s"' % (i, io.name)) )
            for i, io in enumerate(context.active_node.inputs)
        ])
    
    newname : bpy.props.StringProperty(
        name="New Name", description="New name of input", default='New Name')
    
    def invoke(self, context, event):
        if context.active_node == None:
            self.report({'WARNING'}, 'No active node')
            return {'FINISHED'}
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        [x for x in context.active_node.inputs][int(self.ioindex)].name = self.newname
        return {'FINISHED'}
classlist.append(DMR_OP_RenameNodeInput)

# =============================================================================

class DMR_OP_RenameNodeOutput(bpy.types.Operator):
    bl_label = "Rename Node Output (May not save correctly)"
    bl_idname = 'dmr.rename_node_output'
    bl_description = 'Changes name of node output. (NOTE: may not keep changes after reloading file)'
    bl_options = {'REGISTER', 'UNDO'}
    
    ioindex : bpy.props.EnumProperty(
        name="Target Output",
        description="Name of output to rename",
        items=lambda s, context: [
            ( (str(i), '[%d]: %s' % (i, io.name), 'Rename output %d "%s"' % (i, io.name)) )
            for i, io in enumerate(context.active_node.outputs)
        ])
    
    newname : bpy.props.StringProperty(
        name="New Name", description="New name of output", default='New Name')
    
    def invoke(self, context, event):
        if context.active_node == None:
            self.report({'WARNING'}, 'No active node')
            return {'FINISHED'}
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        [x for x in context.active_node.outputs][int(self.ioindex)].name = self.newname
        return {'FINISHED'}
classlist.append(DMR_OP_RenameNodeOutput)

# =============================================================================

class DMR_OP_ToggleSubSurfOptimalDisplay(bpy.types.Operator):
    bl_label = "Toggle Optimal Display"
    bl_idname = 'dmr.toggle_sss_optimal_display'
    bl_description = "Toggles optimal display for objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.object is not None)
    
    def execute(self, context):
        for obj in bpy.data.objects:
            if obj.hide_viewport:
                continue
            if obj.type == 'MESH':
                if obj.modifiers:
                    for m in obj.modifiers:
                        if m.type == 'SUBSURF':
                            m.show_only_control_edges = not m.show_only_control_edges
        return {'FINISHED'}
classlist.append(DMR_OP_ToggleSubSurfOptimalDisplay)

# =============================================================================

class DMR_OP_FixFileOutputNames(bpy.types.Operator):
    bl_label = "Fix Filename Output"
    bl_idname = 'dmr.fix_filename_output'
    bl_description = "Removes frame count from files exported from File Output Node"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        nodes = scene.node_tree.nodes
        
        framenumber = str(scene.frame_current)
        framenumber = '0'*len(framenumber)+framenumber
        
        for nd in nodes:
            if nd.type == 'OUTPUT_FILE':
                basepath = bpy.path.abspath(nd.base_path)
                for slot in nd.file_slots:
                    ext = slot.format.file_format.lower()
                    fpath = basepath+slot.path+framenumber+'.'+ext
                    
                    if os.path.isfile(fpath):
                        newpath = fpath.replace(framenumber, '')
                        if os.path.isfile(newpath):
                            os.remove(newpath)
                        os.rename(fpath, newpath)
        return {'FINISHED'}
classlist.append(DMR_OP_FixFileOutputNames)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
