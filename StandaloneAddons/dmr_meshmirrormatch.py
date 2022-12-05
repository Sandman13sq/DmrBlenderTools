bl_info = {
    'name': 'Mesh Mirror Match',
    'description': 'Operators to sync loop data on left side of mesh to right. Comes with a better (but slower) symmetrize: Super Symmetrize',
    'author': 'Dreamer13sq',
    'version': (1, 0),
    'blender': (3, 3, 1),
    'category': 'Mesh',
    'support': 'COMMUNITY',
}

import bpy

classlist = []

# ==========================================================================================================

# Returns array of islands of vertices per separated parts of mesh
def FindMeshIslands(mesh):
    Sqr = lambda x: x*x
    Abs = lambda x: x if x >= 0 else -x
    
    mode = bpy.context.object.mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    vertices = tuple(mesh.vertices)
    vertexindices = tuple([v.index for v in vertices])
    edges = tuple(mesh.edges)
    polygons = tuple(mesh.polygons)
    
    # Find Islands
    islands = []
    targetverts = [v.index for v in vertices]
    
    vertexshapelist = polygons
    
    while len(targetverts) > 0:
        island = [targetverts[0]]
        nlast = 0
        
        while nlast != len(island):
            nlast = len(island)
            island += [
                vi 
                for p in vertexshapelist if sum([1 for vi in p.vertices if vi in island]) 
                for vi in p.vertices if vi not in island
                ]
        
        island.sort(key=lambda vi: -(vertices[vi].co[0]) )
        islands.append(tuple(island))
        
        targetverts = [
            vi for vi in vertexindices 
            if vi not in [vi for isl in islands for vi in isl]
            ]
        
        if len(targetverts) == 0:
            break
        
        #print(len(island), len(targetverts))
    
    print("> %d Islands Found" % len(islands))
    
    islands = [
        tuple([vertices[vi] for vi in island])
        for island in islands
    ]
    
    islands.sort(key=lambda x: Abs(sum([v.co[0] for v in x])) )
    
    bpy.ops.object.mode_set(mode=mode)
    
    return islands

# ----------------------------------------------------------------------------------------------------------

# Returns ( islandspairs[], islandsisolated[] )
def FindMirroredIslands(mesh, islands, separate_threshold=0.1):
    Sqr = lambda x: x*x
    Abs = lambda x: x if x >= 0 else -x
    
    # Find Mirrored Island Pairs
    usedislands = []
    islandpairs = []
    
    for i1 in islands:
        if i1 in usedislands:
            continue
        
        for i2 in islands[::-1]:
            if i2 in usedislands:
                continue
            if i1 == i2:
                continue
            
            if (
                Sqr( sum([v.co[0] for v in i1])+sum([v.co[0] for v in i2]) ) +
                Sqr( sum([v.co[1] for v in i1])-sum([v.co[1] for v in i2]) ) +
                Sqr( sum([v.co[2] for v in i1])-sum([v.co[2] for v in i2]) )
                ) <= separate_threshold:
                islandpairs.append((i1, i2))
                usedislands.append(i1)
                usedislands.append(i2)
                break
    
    islandsolos = [
        isl for isl in islands if not sum([1 for pair in islandpairs if isl in pair])
    ]
    
    return (islandpairs, islandsolos)

# ==========================================================================================================
# SUPER SYMMETRIZE
# ==========================================================================================================

class DMR_OT_SuperSymmetrize(bpy.types.Operator):
    """Symmetrizes mesh data while being aware of overlapping geometry. Assumes there is at least a straight line of vertices for the x-axis on centered parts."""
    bl_idname = "dmr.super_symmetrize"
    bl_label = "Super Symmetrize"
    bl_options = {'REGISTER', 'UNDO'}
    
    high_accuracy : bpy.props.BoolProperty(
        name="High Accuracy", 
        description="Matching calcuation is aware of overlapping geometry. (Slow)", 
        default=False
        )
    
    separate_threshold : bpy.props.FloatProperty(name="Seperated Threshold", default=0.01)
    center_threshold : bpy.props.FloatProperty(name="Center Threshold", default=0.001)
    
    use_modifier : bpy.props.BoolProperty(name="Split with Modifier", default=False)
    apply_modifier : bpy.props.BoolProperty(name="Apply Mirror", default=False)
    
    uvs : bpy.props.BoolProperty(name="Symmetrize UVs", default=False)
    weights : bpy.props.BoolProperty(name="Symmetrize Weights", default=False)
    colors : bpy.props.BoolProperty(name="Symmetrize Colors", default=False)
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'MESH'
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        Sqr = lambda x: x*x
        Abs = lambda x: x if x >= 0 else -x
        
        obj = context.object
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        selectedpolyindices = [p.index for p in obj.data.polygons if p.select]
        
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Data
        vertices = tuple(obj.data.vertices)
        vertexindices = tuple([v.index for v in vertices])
        edges = tuple(obj.data.edges)
        polygons = tuple(obj.data.polygons)
        loops = tuple(obj.data.loops)
        selectedpolys = [polygons[i] for i in selectedpolyindices]
        
        # Find islands
        if self.high_accuracy:
            islands = FindMeshIslands(obj.data)
            islandpairs, islandsolos = FindMirroredIslands(obj.data, islands)
            
            print("> %d Mirrored Islands" % len(islandpairs))
            print("> %d Solo Islands" % len(islandsolos))
        # All one island
        else:
            islands = [[v for v in vertices]]
            islandpairs = []
            islandsolos = islands
        
        # Process Islands -----------------------------------------------------------------------------------
        
        # Select Sides of Solo Islands
        for island in islandsolos:
            centerindices = [v.index for v in island if Sqr(v.co[0]) <= Sqr(self.center_threshold)]
            islandpolys = [p for p in edges if sum(1 for vi in p.vertices if vertices[vi] in island)]
            islandpolys.sort(key=lambda p: -(sum([vertices[vi].co[0] for vi in p.vertices])) )
            
            islandside = [ island[0].index ]
            nlast = 0
            while nlast != len(islandside):
                nlast = len(islandside)
                islandside += [
                    vi
                    for p in islandpolys if (
                        sum([1 for vi in p.vertices if vi in islandside]) and 
                        not sum([1 for vi in p.vertices if vi in centerindices])
                        )
                    for vi in p.vertices if vi not in islandside
                    ]
            
            for vi in islandside+centerindices:
                vertices[vi].select = True
        
        # Select Left Mirrored Islands
        for islandL, islandR in islandpairs:
            for v in islandL:
                v.select = True
        
        targetpolys = [p for p in polygons if sum(vertices[vi].select for vi in p.vertices) == len(p.vertices) and p in selectedpolys]
        polypairs = [
            (p1, p2)
            for p1 in targetpolys
            for p2 in polygons if p1 != p2 and (
                Sqr( p1.center[0]+p2.center[0] ) +
                Sqr( p1.center[1]-p2.center[1] ) +
                Sqr( p1.center[2]-p2.center[2] )
            ) <= Sqr(self.separate_threshold)
        ]
        
        # Match Loops
        match_uvs = self.uvs
        match_colors = self.colors
        
        if match_uvs or match_colors:
            uv_layer = obj.data.uv_layers.active
            vc_layer = obj.data.color_attributes.active
            #vgroups = obj.data.vgroups
            
            for p1, p2 in polypairs:
                loops1 = [loops[l] for l in p1.loop_indices]
                loops2 = [loops[l] for l in p2.loop_indices]
                loops1.sort( key=lambda l: vertices[l.vertex_index].co.magnitude )
                loops2.sort( key=lambda l: vertices[l.vertex_index].co.magnitude )
                
                for l1, l2 in zip(loops1, loops2):
                    if match_uvs:
                        uv_layer.data[l2.index].uv = uv_layer.data[l1.index].uv
                    if match_colors:
                        vc_layer.data[l2.index].color = vc_layer.data[l1.index].color
            
            
        # Store loop state
        lastuvs = {}
        lastcolors = {}
        
        if self.use_modifier and self.apply_modifier:
            if not match_uvs:
                lastuvs = {
                    p.center.copy().freeze(): tuple( [
                        tuple( [lyr.data[l].uv.copy() for lyrindex, lyr in enumerate(obj.data.uv_layers)] )
                        for l in p.loop_indices
                    ] )
                    for p in polygons
                }
            
            if not match_colors:
                lastcolors = {
                    p.center.copy().freeze(): tuple( [
                        tuple( [tuple(lyr.data[l].color) for lyrindex, lyr in enumerate(obj.data.color_attributes)] )
                        for l in p.loop_indices
                    ] )
                    for p in polygons
                }
        
        # Use Mirror
        if self.use_modifier:
            bpy.ops.object.mode_set(mode='EDIT')
            
            bpy.ops.mesh.select_all(action='INVERT')
            bpy.ops.mesh.delete(type='VERT')
            
            bpy.ops.object.mode_set(mode='OBJECT')
            m = None
            for x in obj.modifiers:
                if x.type == 'MIRROR':
                    m = x
                    break
            if m == None:
                m = obj.modifiers.new(type='MIRROR', name='Mirror - Symmetrize')
            while (obj.modifiers.find(m.name) > 0):
                bpy.ops.object.modifier_move_up(modifier=m.name)
        
        # Apply Mirror
        if self.apply_modifier:
            bpy.ops.object.mode_set(mode='OBJECT')
            m = None
            for x in obj.modifiers:
                if x.type == 'MIRROR':
                    m = x
                    break
            if m:
                bpy.ops.object.modifier_apply(modifier=m.name)
            
            # Restore UVs
            if lastuvs:
                for p in tuple(obj.data.polygons):
                    rankedlastpolys = list(lastuvs.keys())
                    rankedlastpolys.sort(key = lambda k: (p.center-k).length)
                    
                    if (p.center-rankedlastpolys[0]).length <= 0.001:
                        last = lastuvs[rankedlastpolys[0]]
                        
                        for li, l in enumerate(p.loop_indices):
                            for lyrindex, lyr in enumerate(obj.data.uv_layers):
                                lyr.data[l].uv = last[li][lyrindex]
            
            # Restore Colors
            if lastcolors:
                for p in tuple(obj.data.polygons):
                    rankedlastpolys = list(lastcolors.keys())
                    rankedlastpolys.sort(key = lambda k: (p.center-k).length)
                    
                    if (p.center-rankedlastpolys[0]).length <= 0.001:
                        last = lastcolors[rankedlastpolys[0]]
                        
                        for li, l in enumerate(p.loop_indices):
                            for lyrindex, lyr in enumerate(obj.data.color_attributes):
                                lyr.data[l].color = last[li][lyrindex]
        
        bpy.ops.object.mode_set(mode='EDIT')
        
        return {'FINISHED'}
classlist.append(DMR_OT_SuperSymmetrize)

# ==========================================================================================================
# OPERATORS
# ==========================================================================================================

class DMR_OT_MatchMirrorUVs(bpy.types.Operator):
    """Copies UVs of selected loops to loops mirrored along the X axis. Result can be offsetted and flipped."""
    bl_idname = "dmr.match_mirror_uv"
    bl_label = "Match Mirror UVs"
    bl_options = {'REGISTER', 'UNDO'}
    
    offset : bpy.props.FloatVectorProperty(name="Offset", size=2, default=(0.0, 0.0))
    flip : bpy.props.EnumProperty(name="Flip", items=(
        ('NONE', 'None', "No flip"),
        ('LEFT', 'Left', "Flip on leftmost loop"),
        ('RIGHT', 'Right', "Flip on rightmost loop"),
    ))

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        thresh = 0.0005
        
        offset = self.offset
        
        thresh = thresh*thresh
        sqr = lambda x: (x*x)
        MirroredDistance = lambda v1,v2: ( sqr(v2[0]+v1[0]) + sqr(v2[1]-v1[1]) + sqr(v2[2]-v1[2]) )
        
        bpy.ops.object.mode_set(mode='OBJECT')
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            
            uvlayer = obj.data.uv_layers.active
            
            loops = tuple(obj.data.loops)
            vertices = tuple(obj.data.vertices)
            polygons = tuple(obj.data.polygons)
            
            selectedpolys = tuple(p for p in obj.data.polygons if p.select)
            polypairs = {
                p1: p2 
                for p1 in polygons if (p1.select and p1.center[0] > 0)
                for p2 in polygons if (
                    MirroredDistance(p1.center, p2.center) <= thresh
                )
            }
            loopco = {l.index: vertices[l.vertex_index].co for l in loops}
            
            targetuvs = []
            
            for p1, p2 in polypairs.items():
                for l1 in p1.loop_indices:
                    for l2 in p2.loop_indices:
                        if MirroredDistance(loopco[l1], loopco[l2]) <= thresh:
                            targetuvs.append(uvlayer.data[l2])
                            uvlayer.data[l2].uv = uvlayer.data[l1].uv
                            break
            
            if targetuvs:
                if self.flip == 'LEFT':
                    point = min([l.uv[0] for l in targetuvs if l.uv[0] != 0.0])
                    for l in targetuvs:
                        l.uv[0] = point-(l.uv[0]-point)
                
                elif self.flip == 'RIGHT':
                    point = max([l.uv[0] for l in targetuvs if l.uv[0] != 0.0])
                    for l in targetuvs:
                        l.uv[0] = point-(l.uv[0]-point)
                
                for uv in targetuvs:
                    uv.uv[0] += offset[0]
                    uv.uv[1] += offset[1]
                
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}
classlist.append(DMR_OT_MatchMirrorUVs)

# ------------------------------------------------------------------

class DMR_OT_MatchMirrorGroups(bpy.types.Operator):
    """Matches right side vertex weights with left weights of selected vertices"""
    bl_idname = "dmr.match_mirror_groups"
    bl_label = "Match Mirror Groups"
    bl_options = {'REGISTER', 'UNDO'}
    
    mirrored_groups = bpy.props.BoolProperty(name="Match Mirrored Groups", default=True)
    centered_groups = bpy.props.BoolProperty(name="Match Centered Groups", default=False)
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
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
        
        # Iterate through selected meshes
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            
            vgroups = obj.vertex_groups
            
            vertices = tuple(obj.data.vertices)
            polygons = tuple(obj.data.polygons)
            
            # Prepare data
            polypairs = tuple(
                (p1, p2)
                for p1 in [p for p in polygons if p.select]
                for p2 in polygons if (MirroredDistance(p1.center, p2.center) <= thresh)
            )
            
            leftverts = []
            rightverts = []
            vertexpairs = []
            
            for p1, p2 in polypairs:
                verts1 = [vertices[i] for i in p1.vertices]
                verts2 = [vertices[i] for i in p2.vertices]
                vertexpairs += [
                    (v1, v2)
                    for v1 in verts1
                    for v2 in verts2 if (MirroredDistance(v1.co, v2.co) <= thresh)
                ]
            
            # Mirrored Groups
            if self.mirrored_groups:
                # Find group pairs
                oppositegroup = {
                    vg1: vg2
                    for vg1 in vgroups if (vg1.name[-2] in "-._" and vg1.name[-1].upper() == "L")
                    for vg2 in vgroups if (
                        vg2.name[:-1] == vg1.name[:-1] and vg2.name[-1].upper() == "R"
                        )
                }
                
                [vg2.remove(range(0, len(vertices))) for vg1, vg2 in oppositegroup.items()]
                
                for v1, v2 in vertexpairs:
                    for vge1 in v1.groups:
                        vg1 = vgroups[vge1.group]
                        if vg1 in oppositegroup.keys():
                            vg2 = oppositegroup[vg1]
                            vg2.add([v2.index], vge1.weight, 'REPLACE')
            
            # Centered groups
            if self.centered_groups:
                centeredgroups = [vg1 for vg1 in vgroups if not (vg1.name[-2] in "-._" and vg1.name[-1].upper() in "LR")]
                
                for v1, v2 in vertexpairs:
                    for vge1 in v1.groups:
                        vg1 = vgroups[vge1.group]
                        vg1.add([v2.index], vge1.weight, 'REPLACE')
           
        bpy.ops.object.mode_set(mode=mode)
        return {'FINISHED'}
classlist.append(DMR_OT_MatchMirrorGroups)

# ------------------------------------------------------------------

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

# ==========================================================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in list(classlist)[::-1]:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()

