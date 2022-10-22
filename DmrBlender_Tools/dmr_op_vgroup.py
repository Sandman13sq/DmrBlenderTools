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

class DMR_OP_RemoveEmptyVertexGroups(bpy.types.Operator):
    bl_label = "Remove Empty Vertex Groups"
    bl_idname = 'dmr.remove_empty_vertex_groups'
    bl_description = 'Removes Vertex Groups with no weight data'
    bl_options = {'REGISTER', 'UNDO'}
    
    remove_zero : bpy.props.BoolProperty(
        name = "Ignore Zero Weights", default = True,
        description = 'Ignore weights of 0 when checking if groups are empty'
        )
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "remove_zero")
    
    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
                
            lastobjectmode = bpy.context.active_object.mode
            bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
            
            usedgroups = [
                vge.group
                for v in obj.data.vertices
                for vge in v.groups if (
                    (not self.remove_zero or vge.weight > 0.0)
                )
            ]
            usedgroups += [vg.index for vg in obj.vertex_groups if vg.lock_weight]
            usedgroups = tuple(set(usedgroups))
            
            hits = [
                obj.vertex_groups.remove(vg)
                for vg in list(obj.vertex_groups)[::-1] if vg.index not in usedgroups
            ]
            
            if len(hits) == 0:
                self.report({'INFO'}, "No Empty Groups Found")
            else:
                self.report({'INFO'}, "Found and removed %d empty group(s)" % len(hits))
            
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
        
        rsuffixes = [x+y for x in "._-" for y in "rR"]
        [
            obj.vertex_groups.remove(vg)
            for vg in obj.vertex_groups if (not vg.lock_weight and vg.name[-2:] in rsuffixes)
        ]
        
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
            
            lsuffixes = [x+y for x in "._-" for y in "lL"]
            rsuffixes = [x+y for x in "._-" for y in "rR"]
            
            hits = [
                obj.vertex_groups.new( name=vg.name[:-1]+({"l": 'r', "L": "R"}[vg.name[-1]]) )
                for vg in obj.vertex_groups if (vg.name[-2:] in lsuffixes and vg.name[:-1]+({"l": 'r', "L": "R"}[vg.name[-1]]) not in obj.vertex_groups.keys())
            ]
        
        bpy.ops.object.mode_set(mode = lastmode)
        
        if len(hits) == 0:
            self.report({'INFO'}, "No missing groups found")
        else:
            self.report({'INFO'}, "%d missing mirror groups added" % len(hits))
        
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
    bl_description = 'Sets the side suffix (.l, .r) of vertex groups for selected vertices'
    bl_options = {'REGISTER', 'UNDO'}
    
    method : bpy.props.EnumProperty(
        name='Fix Method',
        description='Method to change vertex groups',
        items = (
            ('FLIP', 'Flip Sides', 'Flips mirrored vertex group sides'),
            ('LEFT', 'Force Left', 'Forces vertex groups to the left side'),
            ('RIGHT', 'Force Right', 'Forces vertex groups to the right side'),
            ('BOTH', 'Both Sides', 'Ensures vertices have weights for both sides'),
            ),
        default='FLIP'
        )
    
    def execute(self, context):
        lastobjectmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
        count = 0
        
        method = self.method
        
        oppositestr = {h+k: h+v for h in "._" for k,v in zip("lrLR", "rlRL")}
        
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                vgroups = obj.vertex_groups
                
                # Find groups to fix
                if method == 'FLIP' or method == 'BOTH': # All groups with a mirror suffix
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
                            # Both sides
                            elif method == 'BOTH':
                                # Vertex has entry with opposite group
                                vge2 = ([vge for vge in v.groups if vge.group == g2.index]+[None])[0]
                                if vge2 == None:
                                    g2.add([v.index], w1, 'REPLACE')
                            
                            # Force Right/Left
                            elif method == 'RIGHT' or method == 'LEFT':
                                g1.remove([v.index])
                                g2.add([v.index], w1, 'REPLACE')
        
        self.report({'INFO'}, "Fixed %s weights" % count)
        
        bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
            
        return {'FINISHED'}
classlist.append(DMR_OT_FixVertexGroupSides)

# =============================================================================

class DMR_OT_MatchMirrorGroups(bpy.types.Operator):
    """Matches right side vertex weights with left weights"""
    bl_idname = "dmr.match_mirror_groups"
    bl_label = "Match Mirror Groups"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def execute(self, context):
        thresh = 0.01
        
        thresh = thresh*thresh
        sqr = lambda x: (x*x)
        MirroredDistance = lambda v1,v2: ( sqr(v2[0]+v1[0]) + sqr(v2[1]-v1[1]) + sqr(v2[2]-v1[2]) )
        UpperLetters = lambda x: "".join([c for c in x if c in "QWERTYUIOPASDFGHJKLZXCVBNM"]) 
        Digits = lambda x: "".join([c for c in x if c in "0123456789"]) 
        
        mode = context.active_object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            
            vgroups = obj.vertex_groups
            
            loops = tuple(obj.data.loops)
            vertices = tuple(obj.data.vertices)
            polygons = tuple(obj.data.polygons)
            
            leftverts = tuple(set([vertices[i] for p in polygons if p.center[0] >= 0 for i in p.vertices]))
            rightverts = tuple(set([vertices[i] for p in polygons if p.center[0] <= 0 for i in p.vertices]))
            
            vertexpairs = tuple(
                (v1, v2)
                for v1 in vertices
                for v2 in vertices if (MirroredDistance(v1.co, v2.co) <= thresh)
            )
            
            targetgroups = [vg1 for vg1 in vgroups if (vg1.name[-2:] == ".l")]
            
            # Create mirror groups
            for vg1 in targetgroups:
                break
                if not sum([1 for vg2 in vgroups if (
                    UpperLetters(vg2.name) == (UpperLetters(vg1.name)[:-1]+"R") and
                    Digits(vg2.name) == Digits(vg1.name)
                )]):
                    vgroups.new(name=SwapBoneName(vg1.name))
            
            # Find group pairs
            oppositegroup = {
                vg1: vg2
                for vg1 in vgroups if (vg1.name[-2:] == ".l")
                for vg2 in vgroups if (
                    vg2.name == vg1.name[:-2]+".r"
                    )
            }
            
            [vg2.remove(range(0, len(vertices))) for vg1, vg2 in oppositegroup.items()]
            #[vg1.remove([v.index]) for v in rightverts for vg1 in targetgroups if v.co[0] < 0.0]
            
            for v1, v2 in vertexpairs:
                for vge1 in v1.groups:
                    vg1 = vgroups[vge1.group]
                    if vg1 in oppositegroup.keys():
                        vg2 = oppositegroup[vg1]
                        vg2.add([v2.index], vge1.weight, 'REPLACE')
           
        bpy.ops.object.mode_set(mode=mode)
        return {'FINISHED'}
classlist.append(DMR_OT_MatchMirrorGroups)

# =============================================================================

class DMR_OT_SetWeightByVertexStep(bpy.types.Operator):
    """Sets weight for each vertex by stepping from selected vertex"""
    bl_idname = "dmr.set_weight_by_step"
    bl_label = "Set Weight by Step"
    bl_options = {'REGISTER', 'UNDO'}
    
    count : bpy.props.IntProperty(name="Step Count", min=0, default = 5)
    weight_start : bpy.props.FloatProperty(name="Weight Start", min=0, max=1, default=0.0)
    weight_end : bpy.props.FloatProperty(name="Weight End", min=0, max=1, default=1.0)
    
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
