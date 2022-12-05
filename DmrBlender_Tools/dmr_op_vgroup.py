import bpy

classlist = []

# =============================================================================
# OPERATORS
# =============================================================================

class DMR_OT_AddVertexGroup(bpy.types.Operator):
    """Adds vertex group to object with name parameter"""
    bl_idname = "dmr.vertex_group_new"
    bl_label = "Add Vertex Group to Object"
    bl_options = {'REGISTER', 'UNDO'}
    
    group_name : bpy.props.StringProperty(name="Name", default="New Group")
    active_only : bpy.props.BoolProperty(name="Active Object Only", default=True)
    assign_selected : bpy.props.BoolProperty(name="Assign Selected Vertices", default=False)
    weight : bpy.props.FloatProperty(name="Weight", default=1.0)
    
    @classmethod
    def poll(self, context):
        return context.active_object is not None
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'group_name')
        layout.prop(self, 'active_only')
        layout.prop(self, 'assign_selected')
        r = layout.row()
        r.active=self.assign_selected
        r.prop(self, 'weight')
    
    def execute(self, context):
        mode = context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        for obj in [context.object] if self.active_only else [x for x in context.selected_objects]:
            vgroups = obj.vertex_groups
            if self.group_name not in vgroups.keys():
                vg = vgroups.new()
                vg.name = self.group_name
            vg = vgroups[self.group_name]
            
            if self.assign_selected:
                vg.add([v.index for v in obj.data.vertices if v.select], self.weight, 'REPLACE')
        
        bpy.ops.object.mode_set(mode=mode)
        return {'FINISHED'}
classlist.append(DMR_OT_AddVertexGroup)

# ---------------------------------------------------------------------------

class DMR_OT_RemoveVerticesFromVertexGroup(bpy.types.Operator):
    """Remove from vertex group"""
    bl_idname = "dmr.vertex_group_remove_vertices"
    bl_label = "Remove Selected Vertices From Group"
    bl_options = {'REGISTER', 'UNDO'}
    
    group_name : bpy.props.StringProperty(name="Name", default="New Group")
    active_only : bpy.props.BoolProperty(name="Active Object Only", default=True)
    
    @classmethod
    def poll(self, context):
        return context.active_object is not None
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'group_name')
        layout.prop(self, 'active_only')
    
    def execute(self, context):
        mode = context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        for obj in [context.object] if self.active_only else [x for x in context.selected_objects]:
            vgroups = obj.vertex_groups
            if self.group_name in vgroups.keys():
                vg = vgroups[self.group_name]
                vg.remove([v.index for v in obj.data.vertices if v.select])
        
        bpy.ops.object.mode_set(mode=mode)
        return {'FINISHED'}
classlist.append(DMR_OT_RemoveVerticesFromVertexGroup)

# ---------------------------------------------------------------------------

class DMR_OP_SelectByWeight(bpy.types.Operator):
    bl_label = "Select by Weight"
    bl_idname = 'dmr.select_by_weight'
    bl_description = 'Selects vertices in active vertex group by weight threshold'
    bl_options = {'REGISTER', 'UNDO'}
    
    threshold : bpy.props.FloatProperty(
        name = "Weight Threshold", 
        description = "Weight value to use for comparison",
        default = 0.7, precision = 4, min = 0.0, max = 1.0)
    
    compmode : bpy.props.BoolProperty(
        name = "Select Less Than", 
        description = "Select vertices less than the threshold",
        default = False)
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "threshold")
        layout.prop(self, "compmode")
    
    def execute(self, context):
        object = bpy.context.active_object
        vgroupindex = object.vertex_groups.active.index
        
        compmode = 0
        threshold = self.threshold
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        # Greater Than
        if compmode == 0:
            for v in object.data.vertices:
                for vge in v.groups:
                    if vge.group == vgroupindex:
                        if vge.weight >= threshold:
                            v.select = True
                        break
        # Less Than
        else:
            for v in object.data.vertices:
                for vge in v.groups:
                    if vge.group == vgroupindex:
                        if vge.weight <= threshold:
                            v.select = True
                        break
        
        bpy.ops.object.mode_set(mode = 'EDIT')
        
        return {'FINISHED'}
classlist.append(DMR_OP_SelectByWeight)

# ---------------------------------------------------------------------------

class DMR_OP_ClearWeights(bpy.types.Operator):
    bl_label = "Clear Groups From Selected"
    bl_idname = 'dmr.clear_weights_from_selected'
    bl_description = 'Clears all vertex groups from selected vertices'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selectedObject = context.active_object
        if selectedObject.type == 'MESH':
            lastobjectmode = bpy.context.active_object.mode
            bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
            
            vertexgroups = selectedObject.vertex_groups
            
            # Remove Groups
            for v in selectedObject.data.vertices:
                if v.select:
                    for vge in v.groups:
                        if not vertexgroups[vge.group].lock_weight:
                            vertexgroups[vge.group].remove([v.index]);
                
            bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
            
        return {'FINISHED'}
classlist.append(DMR_OP_ClearWeights)

# ---------------------------------------------------------------------------

class DMR_OP_RemoveUnusedVertexGroups(bpy.types.Operator):
    bl_label = "Remove Empty Vertex Groups"
    bl_idname = 'dmr.remove_unused_vertex_groups'
    bl_description = 'Removes Vertex Groups with no weight data'
    bl_options = {'REGISTER', 'UNDO'}
    
    remove_zero : bpy.props.BoolProperty(
        name = "Ignore Zero Weights", default = True,
        description = 'Ignore weights of 0 when checking if groups are empty'
        )
    
    keep_sides : bpy.props.BoolProperty(
        name = "Keep Mirrored Groups", default = True,
        description = 'Keeps mirror group if one side is used.'
        )
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "remove_zero")
        layout.prop(self, "keep_sides")
    
    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
                
            lastobjectmode = bpy.context.active_object.mode
            bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
            
            vgroups = obj.vertex_groups
            
            usedgroups = [
                vge.group
                for v in obj.data.vertices
                for vge in v.groups if (
                    (not self.remove_zero or vge.weight > 0.0)
                )
            ]
            usedgroups += [vg.index for vg in vgroups if vg.lock_weight]
            
            for m in obj.modifiers:
                try:
                    if m.vertex_group in vgroups.keys():
                        usedgroups.append(vgroups[m.vertex_group].index)
                except:
                    []
            
            usedgroups = list(set(usedgroups))
            if self.keep_sides:
                basenames = [
                    vg.name[:-4] if sum([1 for c in vg.name[-3:] if c in "0123456789"]) == 3 else vg.name
                    for vg in vgroups
                ]
                
                usedgroups += [
                    vg2
                    for vg1 in usedgroups if (basenames[vg1][-2] in "-._" and basenames[vg1][-1].upper() in "LR")
                    for vg2 in usedgroups if (vg2 != vg1 and basenames[vg2][:-1] == basenames[vg1][:-1] and basenames[vg2][-1].upper() in "LR")
                ]
            
            usedgroups = tuple(set(usedgroups))
            unusedgroupnames = [vg.name for vg in vgroups if vg.index not in usedgroups]
            
            hits = [vgroups.remove(vgroups[vgname]) for vgname in unusedgroupnames]
            
            if len(hits) == 0:
                self.report({'INFO'}, "No Empty Groups Found")
            else:
                self.report({'INFO'}, "Found and removed %d empty group(s)" % len(hits))
            
            bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
            
        return {'FINISHED'}
classlist.append(DMR_OP_RemoveUnusedVertexGroups)

# ---------------------------------------------------------------------------

class DMR_OP_RemoveRightVertexGroups(bpy.types.Operator):
    bl_label = "Remove Right Vertex Groups"
    bl_idname = 'dmr.remove_right_vertex_groups'
    bl_description = 'Removes vertex groups with the right mirror prefix'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.info({'WARNING'}, 'No object selected')
            return {'FINISHED'}
        
        lastmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        rsuffixes = [x+y for x in "._-" for y in "rR"]
        [
            obj.vertex_groups.remove(vg)
            for vg in obj.vertex_groups if (not vg.lock_weight and vg.name[-2:] in rsuffixes)
        ]
        
        bpy.ops.object.mode_set(mode = lastmode)
        
        return {'FINISHED'}
classlist.append(DMR_OP_RemoveRightVertexGroups)

# ---------------------------------------------------------------------------

class DMR_OP_RemoveFromSelectedBones(bpy.types.Operator):
    bl_label = "Remove From Selected Bones"
    bl_idname = 'dmr.remove_from_selected_bones'
    bl_description = "Removes selected vertices from selected bones' groups.\n(Both a mesh and armature must be selected)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod 
    def poll(self, context):
        active = context.active_object
        if active:
            if active.type == 'MESH':
                if active.mode == 'EDIT' or active.mode == 'WEIGHT_PAINT':
                    return 1
        return None
    
    def execute(self, context):
        lastobjectmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
        
        armature = [x for x in context.selected_objects if x.type == 'ARMATURE']
        
        if len(armature) == 0:
            self.report({'WARNING'}, 'No armature selected')
            bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
            return {'FINISHED'}
        
        # Find bone names
        armature = armature[0]
        selectedbones = []
        for b in armature.data.bones:
            if b.select:
                print(b.name)
                selectedbones.append(b.name)
        
        # Find selected vertices
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                targetgroups = {x.index: x for x in obj.vertex_groups if x.name in selectedbones}
                verts = [x for x in obj.data.vertices if x.select]
                
                # Pop vertex from selected bone groups
                for v in verts:
                    for vge in v.groups:
                        if vge.group in targetgroups.keys():
                            targetgroups[vge.group].remove( [v.index] )
        
        bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
        return {'FINISHED'}
classlist.append(DMR_OP_RemoveFromSelectedBones)

# ---------------------------------------------------------------------------

class DMR_OP_AddMissingRightVertexGroups(bpy.types.Operator):
    bl_label = "Add Missing Mirror Groups"
    bl_idname = 'dmr.add_missing_right_vertex_groups'
    bl_description = "Creates groups for those with a mirror name if they don't exist already"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        hits = 0
        
        lastmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            
            lsuffixes = [x+y for y in "Ll" for x in "._-"]
            rsuffixes = [x+y for y in "Rl" for x in "._-"]
            
            vgroups = tuple(obj.vertex_groups)
            for vg in vgroups:
                for suffix in lsuffixes:
                    if suffix in vg.name:
                        nextname = vg.name.replace(suffix, suffix[:-1]+({"l": 'r', "L": "R"}[suffix[-1]]) )
                        
                        if nextname not in obj.vertex_groups.keys():
                            print((vg.name, nextname))
                            
                            obj.vertex_groups.new( name=nextname )
                            hits += 1
                        break
        
        bpy.ops.object.mode_set(mode = lastmode)
        
        if hits == 0:
            self.report({'INFO'}, "No missing groups found")
        else:
            self.report({'INFO'}, "%d missing mirror groups added" % hits)
        
        return {'FINISHED'}
classlist.append(DMR_OP_AddMissingRightVertexGroups)

# ---------------------------------------------------------------------------

class DMR_OP_MoveVertexGroupToEnd(bpy.types.Operator):
    bl_label = "Move Vertex Group to End"
    bl_idname = 'dmr.vgroup_movetoend'
    bl_description = 'Moves active vertex group to end of vertex group list'
    bl_options = {'REGISTER', 'UNDO'}
    
    bottom : bpy.props.BoolProperty(
        name="Bottom of List", default = 0,
        description='Move vertex group to bottom of list instead of top'
        )
    
    @classmethod
    def poll(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                return obj.vertex_groups
        return None
    
    def execute(self, context):
        for selectedObject in context.selected_objects:
            if selectedObject.type != 'MESH':
                continue
                
            lastobjectmode = bpy.context.active_object.mode
            bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
            
            vgroups = selectedObject.vertex_groups
            if self.bottom:
                for i in range(0, vgroups.active.index):
                    bpy.ops.object.vertex_group_move(direction='DOWN')
            else:
                for i in range(0, vgroups.active.index):
                    bpy.ops.object.vertex_group_move(direction='UP')
            
            bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
            
        return {'FINISHED'}
classlist.append(DMR_OP_MoveVertexGroupToEnd)

# ---------------------------------------------------------------------------

class DMR_OT_SetWeightByVertexStep(bpy.types.Operator):
    """Sets weight for each vertex by stepping from selected vertex"""
    bl_idname = "dmr.set_weight_by_step"
    bl_label = "Set Weight by Step"
    bl_options = {'REGISTER', 'UNDO'}
    
    count : bpy.props.IntProperty(name="Step Count", min=0, default = 5)
    weight_start : bpy.props.FloatProperty(name="Weight Start", min=0, max=1, default=1.0)
    weight_end : bpy.props.FloatProperty(name="Weight End", min=0, max=1, default=0.0)
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def execute(self, context):
        obj = context.object
        mode = obj.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        vertices = tuple(obj.data.vertices)
        edges = tuple(obj.data.edges)
        
        vgroup = obj.vertex_groups.active
        
        wstart = self.weight_start
        wend = self.weight_end
        wdist = wend-wstart
        
        n = self.count
        vertexindices = [v.index for v in vertices if v.select]
        vgroup.add(vertexindices, wstart, 'REPLACE')
        
        for iteration in range(0, n):
            nextverts = [vi for e in edges if (e.vertices[0] in vertexindices or e.vertices[1] in vertexindices) for vi in e.vertices]
            newverts = [vi for vi in nextverts if vi not in vertexindices]
            
            amt = ( max(0, iteration/(n-1)) )
            weight = amt * wdist + wstart
            vgroup.add(newverts, weight, 'REPLACE')
            vertexindices += newverts
        
        bpy.ops.object.mode_set(mode=mode)
        return {'FINISHED'}
classlist.append(DMR_OT_SetWeightByVertexStep)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
