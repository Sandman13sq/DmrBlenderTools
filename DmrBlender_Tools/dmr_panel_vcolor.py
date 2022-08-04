import bpy

classlist = []

# =============================================================================

class DMR_PT_3DViewVertexColors(bpy.types.Panel): # ------------------------------
    bl_label = "Vertex Colors"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mesh" # Name of sidebar
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod 
    def poll(self, context):
        active = context.active_object
        if active:
            if active.type == 'MESH':
                return active.mode in {'EDIT', 'VERTEX_PAINT', 'OBJECT'}
        return None
    
    def draw(self, context):
        active = context.active_object
        mode = active.mode
        layout = self.layout
        color = bpy.context.scene.editmodecolor
        col255 = [x*255 for x in color[:3]]
        #colhex = '%02x%02x%02x' % (int(color[0]*255), int(color[1]*255), int(color[2]*255))
        #colhex = colhex.upper()
        
        if mode in {'EDIT', 'VERTEX_PAINT'}:
            col = layout.column(align=1)
            
            colorarea = col.row(align = 1)
            row = colorarea.row(align = 1)
            
            cc = row.column(align=1)
            cc.scale_y = 0.5
            op = cc.operator("dmr.set_vertex_color", icon='BRUSH_DATA', text="")
            op.mix_amount = 1.0
            op.color = context.scene.editmodecolor
            op = cc.operator("dmr.adjust_vertex_color", icon='CON_TRACKTO', text="")
            
            row.scale_x = 2
            row.scale_y = 2
            row.prop(context.scene, "editmodecolor", text='')
            
            cc = row.column(align=1)
            cc.scale_y = 0.5
            cc.operator("dmr.pick_vertex_color", icon='EYEDROPPER', text="")
            cc.operator("dmr.select_vertex_color", icon='RESTRICT_SELECT_OFF', text="")
            
            row = col.row(align=1)
            row.label(text = '<%d, %d, %d>   A:%.2f' % (col255[0],col255[1],col255[2], color[3]) )
            
            row = col.row(align = 1)
            row.operator("dmr.vc_clear_alpha", icon='MATSPHERE', text="Clear Alpha")
            
            row = layout.row(align = 1)
            r = row.row(align=1)
            r.label(text='Set Channel: ')
            row.operator('dmr.set_vertex_color_channel', text='', icon='COLOR_RED').channelindex = 0
            row.operator('dmr.set_vertex_color_channel', text='', icon='COLOR_GREEN').channelindex = 1
            row.operator('dmr.set_vertex_color_channel', text='', icon='COLOR_BLUE').channelindex = 2
            row.operator('dmr.set_vertex_color_channel', text='', icon='FONT_DATA').channelindex = 3
            
            row = layout.row(align = 1)
            
classlist.append(DMR_PT_3DViewVertexColors)

# =============================================================================

class DMR_PT_3DViewVertexColors_Palette(bpy.types.Panel): # ------------------------------
    bl_label = "Palettes"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = 'DMR_PT_3DViewVertexColors'
    
    @classmethod 
    def poll(self, context):
        active = context.active_object
        if active:
            if active.type == 'MESH':
                return active.mode in {'EDIT', 'VERTEX_PAINT', 'OBJECT'}
        return None
    
    def draw(self, context):
        obj = context.active_object
        mode = obj.mode
        layout = self.layout
        
        if mode in {'EDIT', 'VERTEX_PAINT'}:
            editmodecoloralpha = bpy.context.scene.editmodecolor[3]
            
            c = layout.column(align=1)
            
            r = c.row(align=1)
            r.prop(obj.data, "vc_palette_index", text="")
            
            palette = bpy.data.palettes[obj.data.vc_palette_index]
            
            r.operator('palette.new', text="", icon='ADD')
            r.operator('dmr.palette_remove', text="", icon='REMOVE').palette_name = palette.name
            r.operator('dmr.palette_rename', text="", icon='GREASEPENCIL').palette_name = palette.name
            
            rr = c.row(align=1)
            rr.prop(context.scene, "vc_palette_display_width", text="Per Row")
            rr.prop(context.scene, "vc_palette_display_count", text="Count")
            #rr.prop(context.scene, "vc_palette_display_mode", text="Mode", icon='COLLAPSEMENU' if context.scene.vc_palette_display_mode else '')
            
            palettearea = layout.column(align=1)
            
            #palettearea.template_palette(bpy.data.palettes, "[\"%s\"]" % palette.name, color=True)
            
            w = context.scene.vc_palette_display_width
            n = context.scene.vc_palette_display_count
            
            n = min( len(palette.colors), n )
            for i in range(0, n, w):
                r = palettearea.row(align=1)
                for element in palette.colors[i:min(i+w, n)]:
                    # Strips
                    if w == 1:
                        r.prop(element, "color", text="", toggle=True)
                        r.operator("dmr.set_vertex_color", icon='BRUSH_DATA', text="").color = list(element.color)+[editmodecoloralpha]
                        r.operator("dmr.set_edit_mode_vc_color", icon='ZOOM_SELECTED', text="").color = list(element.color)+[editmodecoloralpha]
                        op = r.operator("dmr.pick_vertex_color_palette", icon='EYEDROPPER', text="")
                        op.palette_name = palette.name
                        op.index = i
                        op = r.operator('dmr.palette_remove_color', text="", icon='REMOVE')
                        op.palette_name = palette.name
                        op.index = i
                    # Compact
                    else:
                        cc = r.column(align=1)
                        ccc = cc.column(align=1)
                        rr = cc.row(align=1)
                        rr.scale_y = 0.75
                        rr.operator("dmr.set_vertex_color", icon='BRUSH_DATA', text="").color = list(element.color)+[editmodecoloralpha]
                        rr.operator("dmr.set_edit_mode_vc_color", icon='ZOOM_SELECTED', text="").color = list(element.color)+[editmodecoloralpha]
                        cc.prop(element, "color", text="", toggle=True)
                    
            r = palettearea.row(align=1)
            op = r.operator('dmr.palette_add_color', text="", icon='ADD')
            op.palette_name = palette.name
            op.color = context.scene.editmodecolor
            
classlist.append(DMR_PT_3DViewVertexColors_Palette)

# =============================================================================

class DMR_PT_3DViewVertexColors_Layers(bpy.types.Panel): # ------------------------------
    bl_label = "VC Layers"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = 'DMR_PT_3DViewVertexColors'
    
    @classmethod 
    def poll(self, context):
        active = context.active_object
        if active:
            if active.type == 'MESH':
                return active.mode in {'EDIT', 'VERTEX_PAINT', 'OBJECT'}
        return None
    
    def draw(self, context):
        obj = context.active_object
        me = obj.data
        vcolors = me.vertex_colors
        
        layout = self.layout
        row = layout.row(align=0)
        col = row.column()
        col.template_list("MESH_UL_vcols", "vcols", me, "vertex_colors", me.vertex_colors, "active_index", rows=2)
        col = row.column(align=True)
        col.operator("mesh.vertex_color_add", icon='ADD', text="")
        col.operator("mesh.vertex_color_remove", icon='REMOVE', text="")
        col = col.column(align=True)
        col.operator("dmr.vertex_color_move", icon='TRIA_UP', text="").direction = 'UP'
        col.operator("dmr.vertex_color_move", icon='TRIA_DOWN', text="").direction = 'DOWN'
classlist.append(DMR_PT_3DViewVertexColors_Layers)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)
    
    bpy.types.Scene.editmodecolor = bpy.props.FloatVectorProperty(
        name="Paint Color", subtype="COLOR_GAMMA", size=4, min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0, 1.0)
    )
    
    bpy.types.Scene.vc_palette_display_width = bpy.props.IntProperty(
        name="Colors Per Row", default=1, min=1, max=4
    )
    
    bpy.types.Scene.vc_palette_display_count = bpy.props.IntProperty(
        name="Color Count", default=16, min=1, max=32
    )
    
    bpy.types.Mesh.vc_palette_index = bpy.props.EnumProperty(
        name="VC Palette Index", default=0, items = lambda x,c: (
        (x.name, x.name, x.name, 'COLOR', i) for i,x in enumerate(bpy.data.palettes)
    ))

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)
