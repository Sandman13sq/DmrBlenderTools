import bpy
import mathutils

classlist = []

# =============================================================================

class DMR_OP_SelectByVertexColor(bpy.types.Operator):
    bl_label = "Select By Vertex Color"
    bl_idname = 'dmr.select_vertex_color'
    bl_description = 'Select similar vertices/faces by vertex color'
    bl_options = {'REGISTER', 'UNDO'}
    
    thresh : bpy.props.FloatProperty(
        name="Matching Threshold",
        description='Threshold for color comparison',
        soft_min=0.0,
        soft_max=1.0,
        default = 0.01
    )
    
    def execute(self, context):
        lastobjectmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
        
        # Get active object's selected
        obj = bpy.context.active_object
        mesh = obj.data
        
        if not mesh.vertex_colors:
            self.report({'WARNING'}, 'No vertex color data found for "%s"' % obj.name)
            return {'FINISHED'}
        
        vcolors = mesh.vertex_colors.active.data
        loops = mesh.loops
        vertexmode = 0
        
        targetpolys = [poly for poly in mesh.polygons if poly.select]
        if targetpolys:
            targetloops = [l for p in targetpolys for l in loops[p.loop_start:p.loop_start + p.loop_total]]
            vertexmode = 0
        else:
            targetloops = [l for l in loops if mesh.vertices[l.vertex_index].select]
            vertexmode = 1
        
        if len(targetloops) > 0:
            netcolor = [0.0, 0.0, 0.0, 0.0]
            netcount = len(targetloops)
            thresh = self.thresh
            thresh *= thresh
            for l in targetloops:
                color = vcolors[l.index].color
                netcolor[0] += color[0]
                netcolor[1] += color[1]
                netcolor[2] += color[2]
                netcolor[3] += color[3]
            netcolor[0] /= netcount
            netcolor[1] /= netcount
            netcolor[2] /= netcount
            netcolor[3] /= netcount
            print('net: %s' % netcolor)
            nr = netcolor[0]
            ng = netcolor[1]
            nb = netcolor[2]
            na = netcolor[3]
        
        # Set Color
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            
            mesh = obj.data
            
            if not mesh.vertex_colors:
                continue
            
            vcolors = mesh.vertex_colors.active.data
            loops = mesh.loops
            vertexmode = 0
            
            # Faces
            if vertexmode == 0:
                for f in mesh.polygons:
                    c2 = [0]*4
                    for l in f.loop_indices:
                        vc = vcolors[loops[l].index].color
                        c2[0] += vc[0]
                        c2[1] += vc[1]
                        c2[2] += vc[2]
                        c2[3] += vc[3]
                    c2 = [x / len(f.loop_indices) for x in c2]
                    r = c2[0]-nr
                    g = c2[1]-ng
                    b = c2[2]-nb
                    a = c2[3]-na
                    r*=r 
                    g*=g 
                    b*=b 
                    a*=a
                    if (r<=thresh and g<=thresh and b<=thresh and a<=thresh):
                        f.select = 1
            # Vertices
            else:
                for l in [x for x in loops if x not in targetloops]:
                    c2 = vcolors[l.index].color
                    r = c2[0]-nr
                    g = c2[1]-ng
                    b = c2[2]-nb
                    a = c2[3]-na
                    r*=r 
                    g*=g 
                    b*=b 
                    a*=a
                    if (r<=thresh and g<=thresh and b<=thresh and a<=thresh):
                        mesh.vertices[l.vertex_index].select = 1
        
        bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
        return {'FINISHED'}
classlist.append(DMR_OP_SelectByVertexColor)

# =============================================================================

class DMR_OP_SetVertexColor(bpy.types.Operator):
    bl_label = "Set Vertex Color"
    bl_idname = 'dmr.set_vertex_color'
    bl_description = 'Sets vertex color for selected vertices/faces'
    bl_options = {'REGISTER', 'UNDO'}
    
    targetcolor : bpy.props.FloatVectorProperty(
        name="Paint Color", subtype="COLOR_GAMMA", size=4, min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0, 1.0)
    )
    
    mixamount : bpy.props.FloatProperty(
        name="Mix Amount",
        description='Amount to blend from old color to new color',
        soft_min=0.0,
        soft_max=1.0,
        default=1.0
    )
    
    use_vertices : bpy.props.BoolProperty(
        name="Use Vertices", default=False,
        description='Change using vertices instead of faces.',
    )
    
    def execute(self, context):
        lastobjectmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
        
        amt = 1.0-self.mixamount
        
        targetcolor = mathutils.Vector(self.targetcolor)
        
        for obj in [x for x in context.selected_objects] + [context.object]:
            if obj.type != 'MESH': 
                continue
            
            mesh = obj.data
            # Create color layer if not found
            if not mesh.vertex_colors:
                mesh.vertex_colors.new()
            vcolors = mesh.vertex_colors.active.data
            
            targetpolys = [poly for poly in mesh.polygons if poly.select]
            targetloops = []
            # Use faces
            if targetpolys and not self.use_vertices:
                targetloops = (
                    l 
                    for p in targetpolys 
                    for l in mesh.loops[p.loop_start:p.loop_start + p.loop_total]
                    )
            # Use vertices
            else:
                targetloops = (
                    l
                    for p in mesh.polygons if not p.hide
                    for l in mesh.loops[p.loop_start:p.loop_start + p.loop_total] if mesh.vertices[l.vertex_index].select
                    )
            
            # Set colors
            for l in targetloops:
                vcolors[l.index].color = targetcolor.lerp(vcolors[l.index].color, amt)
            
        bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
        return {'FINISHED'}
classlist.append(DMR_OP_SetVertexColor)

# =============================================================================

class DMR_OP_SetVertexColorChannel(bpy.types.Operator):
    bl_label = "Set Vertex Color Channel"
    bl_idname = 'dmr.set_vertex_color_channel'
    bl_description = 'Sets vertex color channel for selected vertices/faces'
    bl_options = {'REGISTER', 'UNDO'}
    
    channelindex : bpy.props.IntProperty(
        name="Channel Index",
        description='Color Channel to modify',
        soft_min=0,
        soft_max=3,
        default=0
    )
    
    channelvalue : bpy.props.FloatProperty(
        name="Channel Value",
        description='New value for color channel',
        soft_min=0.0,
        soft_max=1.0,
        default=1.0
    )
    
    def invoke(self, context, event):
        return self.execute(context)
    
    def execute(self, context):
        lastobjectmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
        
        for obj in set([x for x in context.selected_objects] + [context.object]):
            if obj.type != 'MESH': 
                continue
            
            mesh = obj.data
            if not mesh.vertex_colors:
                mesh.vertex_colors.new()
            vcolors = mesh.vertex_colors.active.data
            loops = mesh.loops
            
            targetpolys = [poly for poly in mesh.polygons if poly.select]
            if targetpolys:
                targetloops = [l for p in targetpolys for l in loops[p.loop_start:p.loop_start + p.loop_total]]
            else:
                targetloops = [l for l in loops if mesh.vertices[l.vertex_index].select]
            
            for l in targetloops:
                vcolors[l.index].color[self.channelindex] = self.channelvalue
        
        bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
        
        return {'FINISHED'}
classlist.append(DMR_OP_SetVertexColorChannel)

# =============================================================================

class DMR_OP_VertexColorClearAlpha(bpy.types.Operator):
    bl_label = "Clear Alpha"
    bl_idname = 'dmr.vc_clear_alpha'
    bl_description = 'Sets vertex color alpha for selected vertices/faces'
    bl_options = {'REGISTER', 'UNDO'}
    
    clearvalue : bpy.props.FloatProperty(
        name="Clear Value",
        description='New value for alpha channel',
        soft_min=0.0,
        soft_max=1.0
    )
    
    def execute(self, context):
        lastobjectmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
        
        for obj in context.selected_objects:
            if obj.type != 'MESH': 
                continue
            
            mesh = obj.data
            if not mesh.vertex_colors:
                mesh.vertex_colors.new()
            vcolors = mesh.vertex_colors.active.data
            loops = mesh.loops
            
            targetpolys = [poly for poly in mesh.polygons if poly.select]
            if targetpolys:
                targetloops = [l for p in targetpolys for l in loops[p.loop_start:p.loop_start + p.loop_total]]
            else:
                targetloops = [l for l in loops if mesh.vertices[l.vertex_index].select]
            
            for l in targetloops:
                vcolors[l.index].color[3] = self.clearvalue
        
        bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
        return {'FINISHED'}
classlist.append(DMR_OP_VertexColorClearAlpha)

# =============================================================================

class DMR_OP_PickVertexColor(bpy.types.Operator):
    bl_label = "Pick Vertex Color"
    bl_idname = 'dmr.pick_vertex_color'
    bl_description = 'Gets vertex color from selected vertices/faces'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        lastobjectmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
        
        mesh = context.active_object.data
        
        if not mesh.vertex_colors:
            self.report({'WARNING'}, 'No vertex color data found')
            bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
            return {'FINISHED'}
        
        vcolors = mesh.vertex_colors.active.data
        loops = mesh.loops
        
        targetpolys = [poly for poly in mesh.polygons if poly.select]
        if targetpolys:
            targetloops = [l for p in targetpolys for l in loops[p.loop_start:p.loop_start + p.loop_total]]
        else:
            targetloops = [l for l in loops if mesh.vertices[l.vertex_index].select]
        
        if len(targetloops) == 0:
            self.report({'WARNING'}, 'No vertices selected')
        else:
            netcolor = [0.0, 0.0, 0.0, 0.0]
            netcount = len(targetloops)
            for l in targetloops:
                color = vcolors[l.index].color
                netcolor[0] += color[0]
                netcolor[1] += color[1]
                netcolor[2] += color[2]
                netcolor[3] += color[3]
            netcolor[0] /= netcount
            netcolor[1] /= netcount
            netcolor[2] /= netcount
            netcolor[3] /= netcount
            bpy.context.scene.editmodecolor = netcolor
        
        bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
        return {'FINISHED'}
classlist.append(DMR_OP_PickVertexColor)

# =============================================================================

class DMR_OP_QuickDirtyColors(bpy.types.Operator):
    bl_idname = "dmr.quick_n_dirty"
    bl_label = "Quick Dirty Vertex Colors"
    bl_description = "Creates new vertex color slot with dirty vertex colors"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        objs = [x for x in context.selected_objects]
        bpy.ops.object.select_all(action='DESELECT')
        oldactive = bpy.context.view_layer.objects.active
        
        for obj in objs:
            if obj.type == 'MESH':
                # Get 'dirty' group
                vcolors = obj.data.vertex_colors
                if 'dirty' not in vcolors.keys():
                    vcolors.new(name = 'dirty')
                vcolorgroup = vcolors['dirty']
                vcolors.active_index = vcolors.keys().index('dirty')
                
                # Set dirt
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode = 'VERTEX_PAINT')
                oldselmode = bpy.context.object.data.use_paint_mask_vertex
                bpy.context.object.data.use_paint_mask_vertex = True
                selected = [x for x in obj.data.vertices if x.select]
                
                bpy.ops.paint.vert_select_all(action='SELECT')
                bpy.ops.paint.vertex_color_brightness_contrast(brightness=100) # Clear with White
                bpy.ops.paint.vertex_color_dirt(
                    blur_strength=1, blur_iterations=1, 
                    clean_angle=3.14159, dirt_angle=0, dirt_only=False, normalize=True)

                bpy.ops.paint.vert_select_all(action='DESELECT')
                
                for x in selected:
                    x.select = 1
                bpy.context.object.data.use_paint_mask_vertex = oldselmode
                bpy.ops.object.mode_set(mode = 'OBJECT')
        
        for obj in objs:
            obj.select_set(1)
        bpy.context.view_layer.objects.active = oldactive
            
        return {'FINISHED'}
classlist.append(DMR_OP_QuickDirtyColors)

# =============================================================================

class DMR_OP_MergeVertexColors(bpy.types.Operator):
    bl_label = "Merge Vertex Color Layer"
    bl_idname = 'dmr.merge_vertex_color'
    bl_description = 'Sets vertex color of selected vertices/faces of active layer to those of another'
    bl_options = {'REGISTER', 'UNDO'}
    
    def GetVCLayers(self, context):
        return [
            (lyr.name, lyr.name, 'Source from "%s"' % lyr.name)
            for lyr in context.object.data.vertex_colors
            ]
    
    sourcelayer : bpy.props.EnumProperty(
        name="Source Layer",
        description='Layer to take colors from',
        items=GetVCLayers
    )
    
    mixamount : bpy.props.FloatProperty(
        name="Mix Amount",
        description='Amount to blend from old color to new color',
        soft_min=0.0,
        soft_max=1.0,
        default=1.0
    )
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'MESH'
    
    def invoke(self, context, event):
        if not context.object.data.vertex_colors:
            self.report({'WARNING'}, 'No vertex color data found.')
            return {'FINISHED'}
        return self.execute(context)
    
    def execute(self, context):
        lastobjectmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
        
        mixamount = self.mixamount
        
        obj = context.object
        mesh = obj.data
        vcolors = mesh.vertex_colors.active.data
        sourcecolors = mesh.vertex_colors[self.sourcelayer].data
        loops = mesh.loops
        
        targetpolys = [poly for poly in mesh.polygons if poly.select]
        if targetpolys:
            targetloops = [l.index for p in targetpolys for l in loops[p.loop_start:p.loop_start + p.loop_total]]
        else:
            targetloops = [l.index for l in loops if mesh.vertices[l.vertex_index].select]
        
        amt = 1.0-mixamount
        
        for l in targetloops:
            vcolors[l].color = mathutils.Vector(sourcecolors[l].color).lerp(vcolors[l].color, amt)
        
        bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
        return {'FINISHED'}
classlist.append(DMR_OP_MergeVertexColors)

# =============================================================================

class DMR_OP_VertexColorMove(bpy.types.Operator):
    bl_idname = "dmr.vertex_color_move"
    bl_label = "Move Vertex Color Data"
    bl_description = "Moves vertex color layer up or down on list"
    bl_options = {'REGISTER', 'UNDO'}
    
    direction : bpy.props.EnumProperty(
        name="Direction",
        description='Direction to move layer',
        items=(
            ('UP', 'Up', 'Move vertex color layer up'),
            ('DOWN', 'Down', 'Move vertex color layer down'),
            ('TOP', 'Top', 'Move vertex color layer to top of list'),
            ('BOTTOM', 'Bottom', 'Move vertex color layer to bottom of list'),
        )
    )
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'MESH'
    
    def execute(self, context):
        object = context.object
        vclayers = context.object.data.vertex_colors
        
        if not vclayers:
            self.report({'WARNING'}, 'No vertex color data found')
            return {'FINISHED'}
        
        lastmode = object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        GetLyrData = lambda x: {i: tuple(vc.color[:]) for i, vc in enumerate(x.data)}
        
        vcactive = vclayers.active
        vcname = vcactive.name
        vcindex = [x for x in vclayers].index(vcactive)
        vcrendername = [x for x in vclayers if x.active_render][0].name
        prenames = [x.name for x in vclayers]
        postnames = prenames[:]
        
        # Sort Names
        if self.direction == 'UP' and vcindex != 0:
            postnames = [x.name for x in vclayers if x.name != vcname]
            postnames.insert(vcindex-1, vcname)
        elif self.direction == 'DOWN' and vcindex != len(vclayers)-1:
            postnames = [x.name for x in vclayers if x.name != vcname]
            postnames.insert(vcindex+1, vcname)
        elif self.direction == 'TOP' and vcindex != 0:
            postnames = [x.name for x in vclayers if x.name != vcname]
            postnames.insert(0, vcname)
        elif self.direction == 'BOTTOM' and vcindex != len(vclayers)-1:
            postnames = [x.name for x in vclayers if x.name != vcname]
            postnames.insert(len(vclayers), vcname)
        
        # Different name order from start
        isequal = True
        for n1, n2 in zip(prenames, postnames):
            if n1 != n2:
                isequal = False
                break
        
        # Different name order from start
        if not isequal:
            vcdatadict = {vclyr.name: GetLyrData(vclyr) for vclyr in vclayers}
            
            for i in range(0, len(vclayers)):
                vclayers.remove(vclayers[0])
            
            for n in postnames:
                data = vcdatadict[n]
                for i, vc in enumerate(vclayers.new(name=n).data):
                    vc.color = data[i]
            
            for vclyr in vclayers:
                if vclyr.name == vcrendername:
                    vclyr.active_render = True
                    break
            vclayers.active = vclayers[vcname]
        
        bpy.ops.object.mode_set(mode=lastmode)
            
        return {'FINISHED'}
bpy.utils.register_class(DMR_OP_VertexColorMove)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
