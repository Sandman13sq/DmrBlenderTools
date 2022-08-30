import bpy
import bmesh
import mathutils

classlist = []

def SearchArmature(obj):
    return (obj if obj.type == 'ARMATURE' else obj.find_armature()) if obj else None

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

class DMR_OP_PoseApply(bpy.types.Operator):
    bl_label = "Apply Pose"
    bl_idname = 'dmr.pose_apply'
    bl_description = 'Applies pose in pose library to current armature pose'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        oldactive = context.active_object
        lastmode = oldactive.mode
        
        target = SearchArmature(oldactive)
        
        poselib = target.pose_library
        poseindex = poselib.pose_markers.active_index
        marker = poselib.pose_markers[poseindex]
        
        for obj in context.selected_objects[:] + [target]:
            if obj.type != 'ARMATURE':
                continue
            
            targethidden = obj.hide_get()
            obj.hide_set(False)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode = 'POSE')
            
            bones = obj.data.bones
            selected = [b for b in bones if b.select]
            hidden = [b for b in bones if b.hide]
            for b in hidden:
                b.hide = False
            
            bpy.ops.pose.select_all(action='SELECT')
            bpy.ops.poselib.apply_pose(pose_index=poseindex)
            bpy.ops.pose.select_all(action='DESELECT')
            
            for b in selected:
                b.select = True
            for b in hidden:
                b.hide = True
            target.hide_set(targethidden)
        
        bpy.context.view_layer.objects.active = oldactive
        bpy.ops.object.mode_set(mode = lastmode)
        
        self.report({'INFO'}, 'Pose read from "%s"' % marker.name)
        
        return {'FINISHED'}
classlist.append(DMR_OP_PoseApply)

# =============================================================================

class DMR_OP_PoseReplace(bpy.types.Operator):
    bl_label = "Replace Pose"
    bl_idname = 'dmr.pose_replace'
    bl_description = 'Overwrites pose in pose library with current armature pose'
    bl_options = {'REGISTER', 'UNDO'}
    
    allbones : bpy.props.BoolProperty(
        name='All Bones', default=0,
        description='Replace pose for all bones'
        )
    
    def execute(self, context):
        oldactive = context.active_object
        lastmode = oldactive.mode
        
        armobj = SearchArmature(context.object)
        context.view_layer.objects.active = armobj
        bpy.ops.object.mode_set(mode = 'POSE')
        poselib = armobj.pose_library
        poseindex = poselib.pose_markers.active_index
        marker = poselib.pose_markers[poseindex]
        
        for obj in context.selected_objects:
            if obj.type != 'ARMATURE':
                continue
            
            # All bones
            if self.allbones:
                bones = obj.data.bones
                selected = [b for b in bones if b.select]
                hidden = [b for b in bones if b.hide]
                
                for b in hidden: 
                    b.hide = False
                
                bpy.ops.pose.select_all(action='SELECT')
                bpy.ops.poselib.pose_add(frame = marker.frame, name = marker.name)
                bpy.ops.pose.select_all(action='DESELECT')
                
                for b in selected: 
                    b.select = True
                for b in hidden: 
                    b.hide = True
            # Selected Only
            else:
                bpy.ops.poselib.pose_add(frame = marker.frame, name = marker.name)
        
        bpy.ops.object.mode_set(mode=lastmode)
        context.view_layer.objects.active = oldactive
        
        poselib.pose_markers.active_index = poseindex
        
        self.report({'INFO'}, 'Pose written to "%s"' % marker.name)
        
        return {'FINISHED'}
classlist.append(DMR_OP_PoseReplace)

# =============================================================================

class DMR_OP_PoseBoneToView(bpy.types.Operator):
    bl_label = "Align Bone to View"
    bl_idname = 'dmr.pose_bone_to_view'
    bl_description = "Sets Pose bone's location and rotation to Viewport's"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE'
    
    def execute(self, context):
        depsgraph = context.evaluated_depsgraph_get()
        scene = context.scene
        
        ray = scene.ray_cast(depsgraph, (1, 1, 1), (-1,-1,-1) )
        
        object = context.object
        bones = object.data.bones
        pbones = object.pose.bones
        bone = [x for x in bones if x.select]
        
        if len(bone) == 0:
            self.report({'WARNING'}, 'No bones selected')
            return {'FINISHED'}
        
        pbone = pbones[bone[0].name]
        
        rdata = context.region_data
        rot = rdata.view_rotation.copy()
        loc = rdata.view_location.copy()
        
        pbone.matrix = mathutils.Matrix.Translation(loc)
        pbone.rotation_quaternion = rot
        
        bpy.ops.transform.translate(value=(0, 0, rdata.view_distance), 
            orient_type='LOCAL', 
            orient_matrix_type='LOCAL', 
            constraint_axis=(False, False, True), 
            )
        
        return {'FINISHED'}
classlist.append(DMR_OP_PoseBoneToView)

# =============================================================================

class DMR_OP_BoneSelectMore(bpy.types.Operator):
    bl_label = "Select More Bones"
    bl_idname = 'dmr.bone_select_more'
    bl_description = "Selects more connected child bones"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE'
    
    def execute(self, context):
        active = bpy.context.view_layer.objects.active
        if active:
            lastobjectmode = bpy.context.active_object.mode
            bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
            bones = [b for b in active.data.bones if b.select]
            for b in bones:
                for c in b.children:
                    if c.use_connect:
                        c.select = True
            bpy.ops.object.mode_set(mode = lastobjectmode)
                        
        return {'FINISHED'}
classlist.append(DMR_OP_BoneSelectMore)

# =============================================================================

class DMR_OP_BoneSelectMoreParent(bpy.types.Operator):
    bl_label = "Select More Parent Bones"
    bl_idname = 'dmr.bone_select_more_parent'
    bl_description = "Selects more connected parent bones"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE'
    
    def execute(self, context):
        active = bpy.context.view_layer.objects.active
        if active:
            lastobjectmode = bpy.context.active_object.mode
            bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
            bones = [b for b in active.data.bones if b.select]
            newselect = []
            for b in bones:
                if b.parent and b.use_connect:
                    newselect.append(b.parent)
            for b in newselect:
                b.select = True
            bpy.ops.object.mode_set(mode = lastobjectmode)
                        
        return {'FINISHED'}
classlist.append(DMR_OP_BoneSelectMoreParent)

# =============================================================================

class DMR_OP_BoneSelectLess(bpy.types.Operator):
    bl_label = "Select Less Bones"
    bl_idname = 'dmr.bone_select_less'
    bl_description = "Selects less connected child bones"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE'
    
    def execute(self, context):
        def FindEndofChain(b):
            if b.children:
                for c in b.children:
                    if c.select:
                        return FindEndofChain(c)
            return b
        
        active = bpy.context.view_layer.objects.active
        if active:
            lastobjectmode = bpy.context.active_object.mode
            bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
            bones = [b for b in active.data.bones if b.select]
            endbones = []
            
            for b in bones:
                endbones.append(FindEndofChain(b))
            for b in endbones:
                b.select = False
            bpy.ops.object.mode_set(mode = lastobjectmode)
                        
        return {'FINISHED'}
classlist.append(DMR_OP_BoneSelectLess)

# =============================================================================

class DMR_OP_BoneSelectLessParent(bpy.types.Operator):
    bl_label = "Select Less Parent Bones"
    bl_idname = 'dmr.bone_select_less_parent'
    bl_description = "Selects less connected parent bones"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE'
    
    def execute(self, context):
        active = bpy.context.view_layer.objects.active
        if active:
            lastobjectmode = bpy.context.active_object.mode
            bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
            bones = [b for b in active.data.bones if b.select]
            endbones = []
            
            for b in bones:
                if b.use_connect:
                    if b.parent:
                        if not b.parent.select:
                            endbones.append(b)
                    else:
                        endbones.append(b)
                else:
                    endbones.append(b)
            for b in endbones:
                b.select = False
            bpy.ops.object.mode_set(mode = lastobjectmode)
                        
        return {'FINISHED'}
classlist.append(DMR_OP_BoneSelectLessParent)

# =============================================================================

class DMR_OP_BoneSelectNoKeyframes(bpy.types.Operator):
    bl_label = "Select Bones Without Keyframes"
    bl_idname = 'dmr.bone_select_no_keyframe'
    bl_description = "Selects bones without keyframes"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return (
            context.object 
            and context.object.type == 'ARMATURE' 
            and context.object.mode == 'POSE'
            )
    
    def execute(self, context):
        object = context.object
        bones = object.data.bones
        pbones = object.pose.bones
        
        if not object.animation_data:
            self.report({'WARNING'}, "Object has no active action.")
            return {'FINISHED'}
        action = object.animation_data.action
        
        fcurvepaths = [fc.data_path for fc in action.fcurves if len(fc.keyframe_points) > 0]
        targetbones = set([b for b in bones if not sum([1 for path in fcurvepaths if b.name in path])])
        
        for b in targetbones:
            if not b.hide:
                b.select = True
                        
        return {'FINISHED'}
classlist.append(DMR_OP_BoneSelectNoKeyframes)

# =============================================================================

def GetBoneGroups(self, context):
    lastobjectmode = bpy.context.active_object.mode
    bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
    
    items = [tuple("Active (%s)" % c.object.pose.bone_groups.active.name)*3] + [
        (g.name, g.name, g.name) for g in c.object.pose.bone_groups
    ]
    
    bpy.ops.object.mode_set(mode = lastobjectmode)
    return items

class DMR_OP_BoneGroupIsolate(bpy.types.Operator):
    bl_label = "Isolate Bone Group"
    bl_idname = 'dmr.bone_group_isolate'
    bl_description = "Hides all bones not in bone group. Unhides if only those in group are shown"
    bl_options = {'REGISTER', 'UNDO'}
    
    group_name : bpy.props.StringProperty(name="Bone Group Name")
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE'
    
    def execute(self, context):
        active = bpy.context.view_layer.objects.active
        if active:
            lastobjectmode = bpy.context.active_object.mode
            bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
            
            if self.group_name in active.pose.bone_groups.keys(): 
                bonegroup = active.pose.bone_groups[self.group_name]
                bones = [active.data.bones[pb.name] for pb in active.pose.bones if pb.bone_group != bonegroup]
                groupbones = [active.data.bones[pb.name] for pb in active.pose.bones if pb.bone_group == bonegroup]
            else:
                bones = [active.data.bones[pb.name] for pb in active.pose.bones if pb.bone_group != None]
                groupbones = [active.data.bones[pb.name] for pb in active.pose.bones if pb.bone_group == None]
                
            if len([b for b in bones if not b.hide]) > 0:
                for b in bones:
                    b.hide = True
            else:
                for b in [b for b in active.data.bones if b not in groupbones]:
                    b.hide = False
            for b in groupbones:
                b.hide = False
            bpy.ops.object.mode_set(mode = lastobjectmode)
                        
        return {'FINISHED'}
classlist.append(DMR_OP_BoneGroupIsolate)

# =============================================================================

class DMR_OP_BoneGroupHide(bpy.types.Operator):
    bl_label = "Hide Bone Group"
    bl_idname = 'dmr.bone_group_hide'
    bl_description = "Hides all bones in bone group. Unhides if only those in group are hidden"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE'
    
    def execute(self, context):
        active = bpy.context.view_layer.objects.active
        if active:
            lastobjectmode = bpy.context.active_object.mode
            bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
            
            bonegroup = active.pose.bone_groups.active
            bones = [active.data.bones[pb.name] for pb in active.pose.bones if pb.bone_group != bonegroup]
            groupbones = [active.data.bones[pb.name] for pb in active.pose.bones if pb.bone_group == bonegroup]
            
            # All hidden
            if len([b for b in groupbones if b.hide]) == len(groupbones):
                for b in groupbones:
                    b.hide = False
            # Some/None hidden
            else:
                for b in groupbones:
                    b.hide = True
            bpy.ops.object.mode_set(mode = lastobjectmode)
                        
        return {'FINISHED'}
classlist.append(DMR_OP_BoneGroupHide)

# =============================================================================

class DMR_OP_BoneGroupIsolate_Active(bpy.types.Operator):
    bl_label = "Isolate Active Bone's Group"
    bl_idname = 'dmr.bone_group_isolate_active'
    bl_description = "Isolates active bone's group"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        obj = context.object
        return obj and obj.type == 'ARMATURE' and obj.mode == 'POSE' and obj.data.bones.active
    
    def execute(self, context):
        obj = context.object
        obj.pose.bone_groups.active = obj.pose.bones[obj.data.bones.active.name].bone_group
        bpy.ops.dmr.bone_group_isolate(group_name=obj.pose.bone_groups.active.name if obj.pose.bone_groups.active else "")
        return {'FINISHED'}
    
classlist.append(DMR_OP_BoneGroupIsolate_Active)

# =============================================================================

addon_keymaps = []
def register():
    for c in classlist:
        bpy.utils.register_class(c)
    
    bpy.types.Armature.bone_index = bpy.props.IntProperty()
    
    # Add hotkeys
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(DMR_OP_BoneSelectMore.bl_idname, type='NUMPAD_PLUS', value='PRESS', ctrl=True, shift=False)
        kmi = km.keymap_items.new(DMR_OP_BoneSelectLess.bl_idname, type='NUMPAD_MINUS', value='PRESS', ctrl=True, shift=False)
        kmi = km.keymap_items.new(DMR_OP_BoneSelectMoreParent.bl_idname, type='NUMPAD_PLUS', value='PRESS', ctrl=True, shift=True)
        kmi = km.keymap_items.new(DMR_OP_BoneSelectLessParent.bl_idname, type='NUMPAD_MINUS', value='PRESS', ctrl=True, shift=True)
        kmi = km.keymap_items.new(DMR_OP_BoneGroupIsolate_Active.bl_idname, type='H', value='PRESS', ctrl=True, shift=True)
        addon_keymaps.append((km, kmi))

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)
    
    # Remove hotkeys
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

if __name__ == "__main__":
    register()
