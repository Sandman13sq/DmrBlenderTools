import bpy

classlist = []

# =============================================================================

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

# =============================================================================

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

# =============================================================================

class DMR_OP_CleanWeights(bpy.types.Operator):
    bl_label = "Clean Weights from Selected"
    bl_idname = 'dmr.clean_weights_from_selected'
    bl_description = 'Cleans weights from selected objects'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        lastobjectmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
        count = 0
        
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                vertexGroups = obj.vertex_groups
                
                # Remove Groups
                for v in obj.data.vertices:
                    if v.select:
                        for g in v.groups:
                            # Pop vertex from group
                            if g.weight == 0:
                                vertexGroups[g.group].remove([v.index])
                                count += 1
        
        self.report({'INFO'}, "Cleaned %s weights" % count)
        
        bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
            
        return {'FINISHED'}
classlist.append(DMR_OP_CleanWeights)

# =============================================================================

class DMR_OP_RemoveEmptyVertexGroups(bpy.types.Operator):
    bl_label = "Remove Empty Vertex Groups"
    bl_idname = 'dmr.remove_empty_vertex_groups'
    bl_description = 'Removes Vertex Groups with no weight data'
    bl_options = {'REGISTER', 'UNDO'}
    
    removeZero : bpy.props.BoolProperty(
        name = "Ignore Zero Weights", default = True,
        description = 'Ignore weights of 0 when checking if groups are empty'
        )
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "removeZero")
    
    def execute(self, context):
        for selectedObject in context.selected_objects:
            if selectedObject.type != 'MESH':
                continue
                
            lastobjectmode = bpy.context.active_object.mode
            bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
            
            vertexGroups = selectedObject.vertex_groups
            targetGroups = [v for v in vertexGroups]
            
            # Find and pop groups with vertex data
            for v in selectedObject.data.vertices:
                for g in v.groups:
                    realGroup = vertexGroups[g.group]
                    if realGroup in targetGroups:
                        if g.weight > 0 or not self.removeZero:
                            targetGroups.remove(realGroup)
                    
                if len(targetGroups) == 0:
                    break
            
            # Remove Empty Groups
            count = len(targetGroups)
            if count == 0:
                self.report({'INFO'}, "No Empty Groups Found")
            else:
                for g in targetGroups:
                    vertexGroups.remove(g)
                self.report({'INFO'}, "Found and removed %d empty group(s)" % count)
            
            bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
            
        return {'FINISHED'}
classlist.append(DMR_OP_RemoveEmptyVertexGroups)

# =============================================================================

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
        
        vgroups = obj.vertex_groups
        groupnames = [x for x in vgroups.keys()]
        lsuffixes = ['_l', '.l']
        rsuffixes = ['_r', '.r']
        
        activegroupname = vgroups[vgroups.active_index]
        
        # Check if any mirror groups exists
        for vg in vgroups:
            try:
                name = vg.name # Weird missing byte errer here sometimes
            except:
                continue
            
            if name[-2:] in lsuffixes:
                othername = name[0:-1] + 'r'
                if othername in groupnames:
                    groupnames.remove(othername)
                    if vgroups[othername].lock_weight:
                        continue
                    vgroups.active_index = vgroups[othername].index
                    bpy.ops.object.vertex_group_remove(all=False, all_unlocked=False)
        
        if activegroupname in groupnames:
            vgroups.active_index = vgroups[activegroupname].index
        bpy.ops.object.mode_set(mode = lastmode)
        
        return {'FINISHED'}
classlist.append(DMR_OP_RemoveRightVertexGroups)

# =============================================================================

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

# =============================================================================

class DMR_OP_AddMissingRightVertexGroups(bpy.types.Operator):
    bl_label = "Add Missing Mirror Groups"
    bl_idname = 'dmr.add_missing_right_vertex_groups'
    bl_description = "Creates groups for those with a mirror name if they don't exist already"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        leftmirrorsuffix = ['_l', '_L', '.l', '.L']
        rightmirrorsuffix = ['_r', '_R', '.r', '.R']
        
        hits = 0
        
        lastmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            
            groupkeys = obj.vertex_groups.keys()
            index = len( groupkeys )
            
            for vg in obj.vertex_groups:
                newname = ""
                
                if vg.name[-2:] in leftmirrorsuffix:
                    newname = vg.name[:-1] + "r"
                elif vg.name[-2:] in rightmirrorsuffix:
                    newname = vg.name[:-1] + "l"
                    
                if newname in groupkeys:
                    continue
                
                if newname != "":
                    obj.vertex_groups.new(name=newname)
                    index += 1
                    print("%s -> %s" % (vg.name, newname))
                    hits += 1
        
        bpy.ops.object.mode_set(mode = lastmode)
        
        if hits == 0:
            self.report({'INFO'}, "No missing groups found")
        else:
            self.report({'INFO'}, "%d missing mirror groups added" % hits)
        
        return {'FINISHED'}
classlist.append(DMR_OP_AddMissingRightVertexGroups)

# =============================================================================

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

# =============================================================================

class DMR_OT_FixVertexGroupSides(bpy.types.Operator):
    bl_label = "Fix Vertex Group Sides"
    bl_idname = 'dmr.fix_vertex_group_sides'
    bl_description = 'Sets the side suffix (.l, .r) for selected vertices'
    bl_options = {'REGISTER', 'UNDO'}
    
    method : bpy.props.EnumProperty(
        name='Fix Method',
        description='Method to change vertex groups',
        items = (
            ('FLIP', 'Flip Sides', 'Flips mirrored vertex group sides'),
            ('LEFT', 'Force Left', 'Forces vertex groups to the left side'),
            ('RIGHT', 'Force Right', 'Forces vertex groups to the right side'),
            ),
        default='FLIP'
        )
    
    def execute(self, context):
        lastobjectmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
        count = 0
        
        method = self.method
        
        oppositestr = {
            '.l': '.r', 
            '.r': '.l',
            '.L': '.R',
            '.R': '.L'
        }
        
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                vgroups = obj.vertex_groups
                
                # Find groups to fix
                if method == 'FLIP': # All groups with a mirror suffix
                    targetgroups = {
                        vg.index: vg for vg in vgroups if sum([vg.name[-2:]==s for s in oppositestr.keys()])
                    }
                elif method == 'RIGHT': # Groups that end with an L
                    targetgroups = {
                        vg.index: vg for vg in vgroups if (vg.name[-1].lower()=='l' and sum([vg.name[-2:]==s for s in oppositestr.keys()]))
                    }
                elif method == 'LEFT': # Groups that end with an R
                    targetgroups = {
                        vg.index: vg for vg in vgroups if (vg.name[-1].lower()=='r' and sum([vg.name[-2:]==s for s in oppositestr.keys()]))
                    }
                
                for x in targetgroups.items():
                    print([x[0], x[1].name])
                
                for v in [v for v in obj.data.vertices if v.select]:
                    checkedvges = []
                    for vge in v.groups:
                        if vge in checkedvges:
                            continue
                        
                        # Group is a mirror group
                        if vge.group in targetgroups.keys():
                            g1 = vgroups[vge.group]
                            g2 = vgroups[g1.name[:-2]+oppositestr[g1.name[-2:]]]
                            w1 = vge.weight
                            
                            checkedvges.append(vge)
                            count += 1
                            
                            # Flip sides
                            if method == 'FLIP':
                                # Vertex has entry with opposite group
                                vge2 = ([vge for vge in v.groups if vge.group == g2.index]+[None])[0]
                                if vge2 != None:
                                    w2 = vge2.weight
                                    g1.add([v.index], w2, 'REPLACE')
                                    g2.add([v.index], w1, 'REPLACE')
                                    checkedvges.append(vge2)
                                # Vertex only has one side
                                else:
                                    g1.remove([v.index])
                                    g2.add([v.index], w1, 'REPLACE')
                                
                                print([g1.name, g2.name])
                            # Force Right/Left
                            elif method == 'RIGHT' or method == 'LEFT':
                                g1.remove([v.index])
                                g2.add([v.index], w1, 'REPLACE')
        
        self.report({'INFO'}, "Fixed %s weights" % count)
        
        bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
            
        return {'FINISHED'}
classlist.append(DMR_OT_FixVertexGroupSides)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
