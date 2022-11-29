import bpy
import mathutils

classlist = []

def GetActiveVCLayer(mesh, render_layer=False):
    if bpy.app.version >= (3, 2, 2):
        return mesh.color_attributes.active if render_layer else mesh.color_attributes.active_color
    else:
        if render_layer:
            return [lyr for lyr in mesh.vertex_colors if lyr.active_render][0]
        return mesh.vertex_colors.active

def GetTargetLoops(mesh, use_vertices=False):
    targetpolys = [poly for poly in mesh.polygons if poly.select]
    targetloops = []
    
    # Use faces
    if targetpolys and not use_vertices:
        targetloops = tuple(
            l 
            for p in targetpolys 
            for l in mesh.loops[p.loop_start:p.loop_start + p.loop_total]
            )
    # Use vertices
    else:
        targetloops = tuple(
            l
            for p in mesh.polygons if not p.hide
            for l in mesh.loops[p.loop_start:p.loop_start + p.loop_total] if mesh.vertices[l.vertex_index].select
            )
    
    return targetloops

def PickColorFromObject(obj, use_render_layer=False):
    mesh = obj.data
    
    if not mesh.vertex_colors:
        return None
    
    vclayer = GetActiveVCLayer(mesh, use_render_layer)
    vcolors = vclayer.data
    
    # Blender 3.2
    if bpy.app.version >= (3, 2, 2):
        targetloops = GetTargetLoops(mesh) if vclayer.domain not in ['POINT', 'EDGE'] else tuple([v for v in mesh.vertices if v.select])
        
        if len(targetloops) == 0:
            return None
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
    # < 3.2
    else:
        targetloops = GetTargetLoops(mesh, False)
        
        if len(targetloops) == 0:
            return None
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
        
    return netcolor

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
    
    use_render_layer : bpy.props.BoolProperty(
        name="Use Render Layer", default=False,
        description='Sample render layer instead of selected layer',
    )
    
    ignore_alpha : bpy.props.BoolProperty(
        name="Ignore Alpha", default=True,
        description="Ignore alpha channel in comparison",
    )
    
    def execute(self, context):
        lastobjectmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
        
        # Get active object's selected
        obj = context.active_object
        mesh = obj.data
        
        if not GetActiveVCLayer(mesh):
            self.report({'WARNING'}, 'No vertex color data found for "%s"' % obj.name)
            return {'FINISHED'}
        
        vcolors = GetActiveVCLayer(mesh, self.use_render_layer).data
        
        loops = mesh.loops
        vertexmode = 0
        
        targetpolys = [poly for poly in mesh.polygons if poly.select]
        vertexmode = len(targetpolys) == 0
        targetloops = GetTargetLoops(mesh)
        
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
        
        ignore_alpha = self.ignore_alpha
        
        hits = 0
        
        # Select Colors
        for obj in set(list(context.selected_objects)+[context.active_object]):
            if not obj:
                continue
            if obj.type != 'MESH':
                continue
            
            mesh = obj.data
            
            if not GetActiveVCLayer(mesh):
                continue
            
            print(obj.name)
            vcolors = GetActiveVCLayer(mesh, self.use_render_layer).data
            loops = mesh.loops
            
            # Faces
            if vertexmode == False:
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
                    if ignore_alpha:
                        a = thresh
                    if (r<=thresh and g<=thresh and b<=thresh and a<=thresh):
                        f.select = True
                        hits += 1
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
                    if ignore_alpha:
                        a = 0.0
                    if (r<=thresh and g<=thresh and b<=thresh and a<=thresh):
                        mesh.vertices[l.vertex_index].select = True
                        hits += 1
        
        print("Hits: %d" % hits)
        bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
        return {'FINISHED'}
classlist.append(DMR_OP_SelectByVertexColor)

# =============================================================================

class DMR_OP_SetVertexColor_Super(bpy.types.Operator):
    color : bpy.props.FloatVectorProperty(
        name="Paint Color", subtype="COLOR_GAMMA" if bpy.app.version < (3, 2, 2) else "COLOR", size=4, min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0, 1.0)
    )
    
    mix_amount : bpy.props.FloatProperty(
        name="Mix Amount",
        description='Amount to blend from old color to new color',
        soft_min=0.0,
        soft_max=1.0,
        default=1.0
    )
    
    keep_alpha : bpy.props.BoolProperty(
        name="Keep Alpha", default=False,
        description="Prevent changing the alpha value of existing colors",
    )
    
    use_vertices : bpy.props.BoolProperty(
        name="Use Vertices", default=False,
        description='Change using vertices instead of faces.',
    )
    
    channels : bpy.props.BoolVectorProperty(
        name="Channels", size=4, default=(True, True, True, True)
    )
    
    def execute(self, context):
        lastobjectmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
        
        amt = 1.0-self.mix_amount
        
        targetcolor = mathutils.Vector(self.color)
        vectorsize = 3 if self.keep_alpha else 4
        
        channels = tuple(self.channels)
        
        for obj in [x for x in context.selected_objects] + [context.object]:
            if obj.type != 'MESH': 
                continue
            
            mesh = obj.data
            # Create color layer if not found
            if bpy.app.version >= (3, 2, 2):
                if not mesh.color_attributes:
                    mesh.color_attributes.new("Col", "BYTE_COLOR", 'CORNER')
            else:
                if not mesh.vertex_colors:
                    mesh.vertex_colors.new()
            
            vcolors = GetActiveVCLayer(mesh).data
            
            targetpolys = [poly for poly in mesh.polygons if poly.select]
            targetloops = GetTargetLoops(mesh, self.use_vertices)
            
            # Set colors
            for l in targetloops:
                colorelement = vcolors[l.index]
                precolor = colorelement.color
                outcolor = targetcolor.lerp(precolor, amt)
                
                vcolors[l.index].color[0] = outcolor[0] if channels[0] else precolor[0]
                vcolors[l.index].color[1] = outcolor[1] if channels[1] else precolor[1]
                vcolors[l.index].color[2] = outcolor[2] if channels[2] else precolor[2]
                vcolors[l.index].color[3] = outcolor[3] if channels[3] else precolor[3]
            
        bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
        return {'FINISHED'}

# -----------------------------------------------------------------------------

class DMR_OP_SetVertexColor(DMR_OP_SetVertexColor_Super):
    bl_label = "Set Vertex Color"
    bl_idname = 'dmr.set_vertex_color'
    bl_description = 'Sets vertex color for selected vertices/faces'
    bl_options = {'REGISTER', 'UNDO'}
classlist.append(DMR_OP_SetVertexColor)

# -----------------------------------------------------------------------------

class DMR_OP_AdjustVertexColor(DMR_OP_SetVertexColor_Super):
    bl_label = "Adjust Vertex Color"
    bl_idname = 'dmr.adjust_vertex_color'
    bl_description = 'Adjusts vertex color for active vertex/face'
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'MESH' and context.object.data.vertex_colors
    
    def invoke(self, context, event):
        obj = context.object
        lastobjectmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
        
        loops = [l.index for l in obj.data.loops if obj.data.vertices[l.vertex_index].select]
        
        if len(loops) == 0:
            self.report({'WARNING'}, "No vertices selected")
            bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
            return {'FINISHED'}
        
        self.color = [ obj.data.vertex_colors.active.data[l] for l in loops ][0].color
        bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
        
        return self.execute(context)
classlist.append(DMR_OP_AdjustVertexColor)

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
    
    use_vertices : bpy.props.BoolProperty(
        name="Use Vertices", default=False,
        description='Change using vertices instead of faces.',
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
            vcolors = GetActiveVCLayer(mesh).data
            
            for l in GetTargetLoops(mesh, self.use_vertices):
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
            vcolors = GetActiveVCLayer(mesh).data
            loops = mesh.loops
            
            targetloops = GetTargetLoops(mesh)
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
    
    use_render_layer : bpy.props.BoolProperty(
        name="Use Render Layer", default=False,
        description='Sample render layer instead of selected layer',
    )
    
    def execute(self, context):
        lastobjectmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
        
        mesh = context.active_object.data
        
        if not mesh.vertex_colors:
            self.report({'WARNING'}, 'No vertex color data found')
            bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
            return {'FINISHED'}
        
        newcolor = PickColorFromObject(context.active_object, self.use_render_layer)
        
        if newcolor != None:
            bpy.context.scene.editmodecolor = newcolor
        else:
            self.report({'WARNING'}, 'No loops selected')
        
        bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
        return {'FINISHED'}
classlist.append(DMR_OP_PickVertexColor)

# =============================================================================

class DMR_OP_PickVertexColor_Palette(bpy.types.Operator):
    bl_label = "Pick Vertex Color for Palette"
    bl_idname = 'dmr.pick_vertex_color_palette'
    bl_description = 'Gets vertex color from selected vertices/faces and sets palette color'
    bl_options = {'REGISTER', 'UNDO'}
    
    palette_name : bpy.props.EnumProperty(
        name="Palette Name", default = 0,
        items=lambda x,c: (tuple([x.name]*3) for x in bpy.data.palettes)
    )
    index : bpy.props.IntProperty(name='Color Index', default=0)
    
    use_render_layer : bpy.props.BoolProperty(
        name="Use Render Layer", default=False,
        description='Sample render layer instead of selected layer',
    )
    
    def execute(self, context):
        lastobjectmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
        
        mesh = context.active_object.data
        
        if not mesh.vertex_colors:
            self.report({'WARNING'}, 'No vertex color data found')
            bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
            return {'FINISHED'}
        
        palette = bpy.data.palettes[self.palette_name]
        
        newcolor = PickColorFromObject(context.active_object, self.use_render_layer)
        
        if newcolor != None:
            palette.colors[self.index].color = newcolor[:3]
        else:
            self.report({'WARNING'}, 'No loops selected')
        
        bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
        return {'FINISHED'}
classlist.append(DMR_OP_PickVertexColor_Palette)

# =============================================================================

class DMR_OP_SetEditModeVCColor(bpy.types.Operator):
    bl_label = "Set Edit Mode VC Color"
    bl_idname = 'dmr.set_edit_mode_vc_color'
    bl_description = "Sets the edit mode color used for painting vertex colors"
    bl_options = {'REGISTER', 'UNDO'}
    
    color : bpy.props.FloatVectorProperty(
        name="Paint Color", subtype="COLOR_GAMMA", size=4, min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0, 1.0)
    )
    
    def execute(self, context):
        bpy.context.scene.editmodecolor = self.color
        return {'FINISHED'}
classlist.append(DMR_OP_SetEditModeVCColor)

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

class DMR_OP_VertexColorGammaCorrect(bpy.types.Operator):
    bl_label = "Gamma Correct Vertex Colors"
    bl_idname = 'dmr.vc_gamma_correct'
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    
    revert : bpy.props.BoolProperty(name="Revert Correction", default=False)
    selectedonly : bpy.props.BoolProperty(name="Selected Only", default=False)
    
    use_vertices : bpy.props.BoolProperty(
        name="Use Vertices", default=False,
        description='Change using vertices instead of faces.',
    )
    
    def execute(self, context):
        lastobjectmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
        
        exponent = 2.2 if not self.revert else 0.4545
        
        for obj in [x for x in context.selected_objects] + [context.object]:
            if obj.type != 'MESH': 
                continue
            
            mesh = obj.data
            vcolors = GetActiveVCLayer(mesh).data
            print(GetActiveVCLayer(mesh))
            
            #targetpolys = [poly for poly in mesh.polygons if poly.select]
            
            if self.selectedonly:
                targetloops = GetTargetLoops(mesh, self.use_vertices)
            else:
                targetloops = tuple(mesh.loops)
            
            # Set colors
            if not self.revert:
                for l in targetloops:
                    vcolors[l.index].color[:3] = mathutils.Color(vcolors[l.index].color[:3]).from_scene_linear_to_srgb()
            else:
                for l in targetloops:
                    vcolors[l.index].color[:3] = mathutils.Color(vcolors[l.index].color[:3]).from_srgb_to_scene_linear()
            
        bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
        return {'FINISHED'}
classlist.append(DMR_OP_VertexColorGammaCorrect)


# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()

