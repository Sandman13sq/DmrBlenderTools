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

class DMR_PT_3DViewPoseNavigation(bpy.types.Panel): # ------------------------------
    bl_label = "Pose Navigation"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Pose" # Name of sidebar
    
    def draw(self, context):
        active = bpy.context.active_object
        armature = SearchArmature(active)
        
        layout = self.layout
        
        if armature and armature.type == 'ARMATURE':
            layout.label(text=armature.name)
            # Toggle Pose
            row = layout.row()
            if armature.data.pose_position == 'POSE':
                row.operator('dmr.toggle_pose_parent', text='Rest Position', icon='POSE_HLT')
            else:
                row.operator('dmr.toggle_pose_parent', text='Pose Position', icon='ARMATURE_DATA')
            
            layout.template_ID(armature, "pose_library", new="poselib.new", unlink="poselib.unlink")
            
            poselib = armature.pose_library
            
            if poselib:
                # warning about poselib being in an invalid state
                if poselib.fcurves and not poselib.pose_markers:
                    layout.label(icon='ERROR', text="Error: Potentially corrupt library, run 'Sanitize' operator to fix")

                # list of poses in pose library
                row = layout.row()
                row.template_list("UI_UL_list", "pose_markers", poselib, "pose_markers",
                                  poselib.pose_markers, "active_index", rows=5)
                
                col = row.column(align=True)
                col.operator("poselib.pose_add", icon='ADD', text="")
                col.operator_context = 'EXEC_DEFAULT'  # exec not invoke, so that menu doesn't need showing

                pose_marker_active = poselib.pose_markers.active

                if pose_marker_active is not None:
                    col.operator("poselib.pose_remove", icon='REMOVE', text="")
                    col.operator(
                        "poselib.apply_pose",
                        icon='ZOOM_SELECTED',
                        text="",
                    ).pose_index = poselib.pose_markers.active_index

                col.operator("poselib.action_sanitize", icon='HELP', text="")  # XXX: put in menu?
                #col.operator("poselib.convert_old_poselib", icon='ASSET_MANAGER', text="")

                if pose_marker_active is not None:
                    col.operator("poselib.pose_move", icon='TRIA_UP', text="").direction = 'UP'
                    col.operator("poselib.pose_move", icon='TRIA_DOWN', text="").direction = 'DOWN'
            
            # Apply/Write
            if poselib != None and poselib.pose_markers != None:
                if poselib.pose_markers.active != None:
                    poseindex = poselib.pose_markers.active_index
                    poseactive = poselib.pose_markers.active
                    
                    # Selected
                    row = layout.row(align=1)
                    row.operator("poselib.apply_pose", icon='ZOOM_SELECTED', text="Apply Pose").pose_index = poseindex
                    rr = row.row(align=1)
                    rr.scale_x = 0.7
                    rr.operator("dmr.pose_apply", icon='ZOOM_SELECTED', text="All")
                    
                    # All
                    row = layout.row(align=1)
                    row.operator("dmr.pose_replace", icon='GREASEPENCIL', text="Write Pose").allbones = 0
                    rr = row.row(align=1)
                    rr.scale_x = 0.7
                    rr.operator("dmr.pose_replace", icon='GREASEPENCIL', text="All").allbones = 1
        else:
            layout.label(text='No armature selected or linked')
classlist.append(DMR_PT_3DViewPoseNavigation)

# ==========================================================================

class DMR_PT_3DViewBoneGroups(bpy.types.Panel): # ------------------------------
    bl_label = "Bone Groups"
    bl_idname = "DMR_PT_BONEGROUPS"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Armature" # Name of sidebar
    
    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'ARMATURE' and obj.mode in {'EDIT', 'POSE'}
    
    def draw(self, context):
        active = bpy.context.object
        
        layout = self.layout
        
        section = layout.column()
        ob = active
        pose = ob.pose
        group = pose.bone_groups.active

        row = layout.row()

        rows = 1
        if group:
            rows = 4
        row.template_list(
            "UI_UL_list", "bone_groups", pose,
            "bone_groups", pose.bone_groups,
            "active_index", rows=rows,
        )

        col = row.column(align=True)
        col.operator("pose.group_add", icon='ADD', text="")
        col.operator("pose.group_remove", icon='REMOVE', text="")
        col.menu("DATA_MT_bone_group_context_menu", icon='DOWNARROW_HLT', text="")
        if group:
            col.separator()
            col.operator("pose.group_move", icon='TRIA_UP', text="").direction = 'UP'
            col.operator("pose.group_move", icon='TRIA_DOWN', text="").direction = 'DOWN'

            split = layout.split()
            split.active = (ob.proxy is None)

            col = split.column()
            col.prop(group, "color_set")
            if group.color_set:
                col = split.column()
                sub = col.row(align=True)
                sub.enabled = group.is_custom_color_set  # only custom colors are editable
                sub.prop(group.colors, "normal", text="")
                sub.prop(group.colors, "select", text="")
                sub.prop(group.colors, "active", text="")

        c = layout.column()

        sub = c.row(align=True)
        sub.operator("pose.group_assign", text="Assign")
        # row.operator("pose.bone_group_remove_from", text="Remove")
        sub.operator("pose.group_unassign", text="Remove")

        sub = c.row(align=True)
        sub.operator("pose.group_select", text="Select")
        sub.operator("pose.group_deselect", text="Deselect")
        
        sub = c.row(align=True)
        sub.operator("dmr.bone_group_isolate", text="Isolate")
classlist.append(DMR_PT_3DViewBoneGroups)

# ==========================================================================

class DMR_PT_3DViewBones(bpy.types.Panel): # ------------------------------
    bl_label = "Bone"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Armature" # Name of sidebar
    
    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'ARMATURE'
    
    def draw(self, context):
        layout = self.layout
        active = context.object
        bones = active.data.bones if active.mode == 'POSE' else active.data.edit_bones
        bonelist = [b for b in bones]
        
        box = layout.column(align=1)
        box.label(text='Active Bone')
        b = bones.active
        if b:
            box.operator('dmr.bone_select_index', text=b.name, icon='BONE_DATA').index = bonelist.index(b)
            r = box.row(align=1)
            
            rr = r.row()
            rr.scale_x = 0.6
            rr.label(text='Parent: ')
            if b.parent:
                r.operator('dmr.bone_select_index', 
                    text='%s' % b.parent.name, icon='SNAP_MIDPOINT' if b.use_connect else 'CON_TRACKTO').index = bonelist.index(b.parent)
            else:
                r.label(text='<No Parent>')
            
            bb = box.box().column(align=1)
            children = b.children
            if not children:
                bb.label(text='<No Children>')
            else:
                bb.label(text='%d %s' % (len(children), 'Children' if len(children) > 1 else 'Child'))
            
            for c in children:
                bb.operator('dmr.bone_select_index', text=c.name, 
                    icon='SNAP_MIDPOINT' if c.use_connect else 'CON_TRACKTO').index = bonelist.index(c)
        
        # Bone List
        layout.template_list(
            "UI_UL_list", "armature_bones", active.data,
            "bones", active.data,
            "bone_index", rows=3,
        )
        
        r = layout.row()
        r.operator('dmr.bone_select_index', text='Select Highlighted').index = active.data.bone_index
        
        if active.mode == 'POSE':
            r = layout.row(align=1)
            r.operator('dmr.bone_select_more')
            r.operator('dmr.bone_select_less')
classlist.append(DMR_PT_3DViewBones)

# ==========================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
