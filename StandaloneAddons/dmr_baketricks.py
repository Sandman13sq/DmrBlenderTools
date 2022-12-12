"""
    If your vertex colors are coming out black in the baked texture, 
    check that you have the correct UV layer that you want to bake to selected
    AND that your vertex color node in your material is set with a name (Not left empty).
"""

bl_info = {
    'name': 'Bake Tricks',
    'description': 'Bake to separate image textures, then combine to a final texture. Use for compositing game textures (like PRM).',
    'author': 'Dreamer13sq',
    'version': (1, 0),
    'blender': (3, 0, 0),
    'category': 'Render',
    'support': 'COMMUNITY',
}

import bpy

classlist = []

Items_BakeTypes = tuple((x,x,x) for x in 'ROUGHNESS EMIT NORMAL COMBINED'.split())
Items_BakeTypes = (
    ('ROUGHNESS', "Roughness", "Bake roughness value to image. Range is linear. Use for NON-color data.", 'IPO_LINEAR', 0),
    ('EMIT', "Emit", "Bake emit colors to image. Use for color data.", 'COLOR', 1),
    ('NORMAL', "Normal", "Bake final normal values to image. Use for normals data.", 'NORMALS_VERTEX', 2),
    ('COMBINED', "Combined", "Bake combined color values to image.", 'MATERIAL', 3),
)

Items_ColorChannels = (
    ('R', "R", "Red Channel"),
    ('G', "G", "Green Channel"),
    ('B', "B", "Blue Channel"),
    ('A', "A", "Alpha Channel"),
)

Items_ColorSpace = (
    ('Linear', 'Linear', "Linear color space. No gamma correction"),
    ('sRGB', 'sRGB', "sRGB color space. Color range is on a curve")
)

# ================================================================================
# FUNCTIONS
# ================================================================================

def ObjectRenderEnabled(obj):
    if obj == None:
        return False
    
    return not obj.hide_render and not obj.users_collection[0].hide_render

# ----------------------------------------------------------------------------

def ImageFrom4(
    self, context, 
    output1, output2, output3, output4, 
    types=['ROUGHNESS']*4,
    channels="RRRR",
    samples=[1]*4,
    image_node_label="",
    color_space='Linear',
    save_image=True
    ):
    
    # Setup
    materials = [obj.active_material for obj in context.selected_objects if obj.type == 'MESH' and obj.active_material]
    materials = list(set(materials))
    
    lastsamples = context.scene.cycles.samples
    lastbaketarget = context.scene.render.bake.target
    
    hits = 0
    
    lastselected = [obj for obj in context.selected_objects]
    for obj in [obj for obj in context.selected_objects if obj.type != 'MESH']:
        obj.select_set(False)
    for obj in context.selected_objects:
        obj.data.update()
    
    [bpy.data.images.remove(x) for x in bpy.data.images if '__temp_bake' in x.name]
    
    # Bake Per Material
    for material in materials:
        print('> Material: ' + material.name)
        
        nodes = material.node_tree.nodes
        imagenodes = [nd for nd in nodes if nd.type == 'TEX_IMAGE']
        imagenode = None
        
        # Find image node --------------------------------------------------------------------------
        image_node_label = ""
        if image_node_label:
            for nd in imagenodes:
                if nd.label.lower() == image_node_label.lower():
                    for nd2 in nodes:
                        nd2.select = False
                    nd.select = True
                    imagenode = nd
                    break
        
        if imagenode == None:
            imagenode = ([nd for nd in nodes if (nd.select and nd.type == 'TEX_IMAGE')]+[None])[0]
        
        if imagenode == None:
            self.report({'WARNING'}, "Material \"%s\" No active image node selected" % material.name)
            continue
        
        nodes.active = imagenode
        targetimage = imagenode.image
        
        if not targetimage.has_data:
            self.report({'WARNING'}, "Material \"%s\" Image \"%s\" has no data" % (material.name, targetimage.name))
        
        # Bake to temp images --------------------------------------------------------------------------
        bakeimages = []
        
        outputnodes = [x for x in nodes if x.type == 'OUTPUT_MATERIAL']
        lastoutput = ([x for x in outputnodes if x.is_active_output]+[None])[0]
        
        keyedimage = {}
        
        for channelindex, name in enumerate([output1, output2, output3, output4]):
            if name == "":
                bakeimages.append(None)
                continue
            
            bakekey = str((name, types[channelindex]))
            
            if bakekey in keyedimage.keys():
                print('> "%s", type \'%s\' (Previously Baked)' % (name, types[channelindex]))
                bakeimages.append(keyedimage[bakekey])
                continue
            
            for nd in outputnodes:
                nd.is_active_output = False
            output = ([x for x in outputnodes if name.lower() == x.label.lower()]+[None])[0]
            
            if output:
                print('> "%s", type \'%s\'' % (name, types[channelindex]))
                output.is_active_output = True
                
                # Bake Setup
                context.scene.cycles.samples = samples[channelindex]
                context.scene.render.bake.target = 'IMAGE_TEXTURES'
                
                bakeimage = bpy.data.images.new("__temp_bake%d_%s" % (channelindex, name), 
                    targetimage.size[0], targetimage.size[1], alpha=True, is_data=True)
                bakeimages.append(bakeimage)
                bakeimage.colorspace_settings.name = color_space
                imagenode.image = bakeimage
                
                # Bake ----------------------------------------
                print("> Baking...")
                bpy.ops.object.bake(type=types[channelindex])
                
                keyedimage[bakekey] = bakeimage
            else:
                bakeimages.append(None)
                print('> Output node "%s" not found' % (name))
        
        imagenode.image = targetimage
        
        # Compose final image --------------------------------------------------------------------------
        if len(bakeimages) > 0:
            print('> Compositing Output Image "%s"...' % targetimage.name)
            
            #image.colorspace_settings.name = 'Linear'
            #image.alpha_mode = 'STRAIGHT'
            
            # List of channels indices[4]
            readchannel = tuple([{'R':0, 'G':1, 'B':2, 'A':3}[channels[i]] for i in range(0, 4)])
            
            pixels = targetimage.pixels
            w, h = targetimage.size
            n = w*h
            n4 = n*4
            
            print("src_images: ", [x.name if x else "<None>" for x in bakeimages])
            
            sourcedata = tuple([tuple(bakeimages[i].pixels) for i in range(0, 4)])
            
            # pixels = image[ writeindex ][ readindex ]
            targetimage.pixels = tuple(
                sourcedata[ pi%4 ][ 4*(pi//4)+readchannel[pi%4] ]
                for pi in range(0, n4)
            )
            
            # Cleanup --------------------------------------------------------------------------
            print('> Cleaning Up...')
            
            for img in list(set(bakeimages)):
                break
                bpy.data.images.remove(img)
            
            for s in [s for a in context.screen.areas for s in a.spaces]:
                if s.type == 'IMAGE_EDITOR':
                    s.image = targetimage
                    break
            
            if save_image:
                targetimage.save()
                targetimage.update()
            
            hits += 1
        else:
            print('> No images to bake...')
        
        for nd in outputnodes:
            nd.is_active_output = False
        lastoutput.is_active_output = True
    
    context.scene.cycles.samples = lastsamples
    context.scene.render.bake.target = lastbaketarget
    
    for obj in lastselected:
        obj.select_set(True)
    
    if hits > 0:
        self.report({'INFO'}, "> Bake From 4 Complete (%d composited images)" % hits)
    else:
        self.report({'INFO'}, "> Bake From 4 - No changes made")
        
    return {'FINISHED'}

# ================================================================================
# PROPERTY GROUPS
# ================================================================================

class PRM_BakeTricks_MaterialOutputDef(bpy.types.PropertyGroup):
    output : bpy.props.StringProperty(
        name="Material Output",
        description="Label of material output node"
        )
    type : bpy.props.EnumProperty(
        name="Bake Type", 
        items=Items_BakeTypes,
        description="Bake type to use for channel"
        )
    channel : bpy.props.EnumProperty(
        name="Channel", 
        items=Items_ColorChannels,
        description="Which channel from baked material values to use"
        )
    samples : bpy.props.IntProperty(
        name="Samples", 
        min=1, 
        default=1,
        description="Number of samples to use when baking"
        )
    
    def CopyFromOther(self, other):
        self.output = other.output
        self.type = other.type
        self.channel = other.channel
        self.samples = other.samples
        
        return self
classlist.append(PRM_BakeTricks_MaterialOutputDef)

# ----------------------------------------------------------------------------

class PRM_BakeTricks_BakeDef(bpy.types.PropertyGroup):
    name : bpy.props.StringProperty(name="Name", default="New Settings")
    items : bpy.props.CollectionProperty(type=PRM_BakeTricks_MaterialOutputDef)
    itemindex : bpy.props.IntProperty()
    
    color_space : bpy.props.EnumProperty(
        name="Color Space", 
        default='Linear', 
        items=Items_ColorSpace
        )
    
    mutex : bpy.props.BoolProperty(default=False)
    
    CAPACITY = 4
    
    op_move_up : bpy.props.BoolVectorProperty(size=CAPACITY, default=[False]*CAPACITY, update=lambda s,c: s.Update(c))
    op_move_down : bpy.props.BoolVectorProperty(size=CAPACITY, default=[False]*CAPACITY, update=lambda s,c: s.Update(c))
    
    def CopyFromOther(self, other):
        for i, otheritem in enumerate(other.items):
            self.items[i].CopyFromOther(otheritem)
        return self
    
    def Serialize(self):
        return tuple(
            (x.output, x.type, x.channel, x.samples) for x in self.items
        )
    
    def Unserialize(self, data):
        []
    
    def Update(self, context):
        if self.mutex:
            return
            
        self.mutex = True
        
        # Fix 4 Items
        while (len(self.items) < 4):
            self.items.add()
        
        # Move items
        for i,move in enumerate(self.op_move_up):
            if move:
                self.MoveItem(i, False)
        
        for i,move in enumerate(self.op_move_down):
            if move:
                self.MoveItem(i, True)
        
        self.op_move_up = [False]*len(self.op_move_up)
        self.op_move_down = [False]*len(self.op_move_down)
        
        self.mutex = False
    
    def DrawPanel(self, context, layout):
        row = layout.row()
        
        c = row.column(align=1)
        c.template_list(
            "VBM_UL_AttributeList", "", 
            self, "items", 
            self, "itemindex", 
            rows=8)
classlist.append(PRM_BakeTricks_BakeDef)

# ----------------------------------------------------------------------------

class PRM_BakeTricks_Master(bpy.types.PropertyGroup):
    size : bpy.props.IntProperty()
    items : bpy.props.CollectionProperty(type=PRM_BakeTricks_BakeDef)
    itemindex : bpy.props.IntProperty()
    
    update_mutex : bpy.props.BoolProperty(default=False)
    
    op_add_item : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    op_remove_item : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    op_move_up : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    op_move_down : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    
    op_cycles : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    
    def GetActive(self):
        return self.items[self.itemindex] if self.size > 0 else None
    
    def GetItem(self, index):
        return self.items[index] if self.size else None 
    
    def FindItem(self, name):
        return ([x for x in self.items if x.name == name]+[None])[0]
    
    def Add(self):
        item = self.items.add()
        item.Update(None)
        self.size = len(self.items)
        return item
    
    def RemoveAt(self, index):
        if len(self.items) > 0:
            self.items.remove(index)
            self.size = len(self.items)
            
            self.itemindex = max(min(self.itemindex, self.size-1), 0)
    
    def MoveItem(self, index, move_down=True):
        newindex = index + (1 if move_down else -1)
        self.items.move(index, newindex)
    
    def Update(self, context):
        # Add
        if self.op_add_item:
            self.op_add_item = False
            self.Add()
            self.itemindex = self.size-1
        
        # Remove
        if self.op_remove_item:
            self.op_remove_item = False
            self.RemoveAt(self.itemindex)
        
        # Move
        if self.op_move_down:
            self.op_move_down = False
            self.items.move(self.itemindex, self.itemindex+1)
            self.itemindex = max(min(self.itemindex+1, self.size-1), 0)
        
        if self.op_move_up:
            self.op_move_up = False
            self.items.move(self.itemindex, self.itemindex-1)
            self.itemindex = max(min(self.itemindex-1, self.size-1), 0)
        
        if self.op_cycles:
            self.op_cycles = False
            context.scene.render.engine = 'CYCLES'
classlist.append(PRM_BakeTricks_Master)

# ----------------------------------------------------------------------------

class PRM_UL_BakeDefList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        c = layout.column(align=1)
        
        r = c.row(align=1)
        
        itemdata = item.Serialize()
        op = r.operator("dmr.bake_from_4", text="", icon='RENDER_STILL')
        op.output1, op.type1, op.channel1, op.samples[0] = itemdata[0]
        op.output2, op.type2, op.channel2, op.samples[1] = itemdata[1]
        op.output3, op.type3, op.channel3, op.samples[2] = itemdata[2]
        op.output4, op.type4, op.channel4, op.samples[3] = itemdata[3]
        op.color_space = item.color_space
        
        r.prop(item, 'name', text="", emboss=False)
        
        rr = r.column(align=1)
        rr.scale_y = 0.5
        rr.prop(active_data, 'op_move_up', text="", index=index, icon_only=True, icon='TRIA_UP')
        rr.prop(active_data, 'op_move_down', text="", index=index, icon_only=True, icon='TRIA_DOWN')
        r.row().prop(active_data, 'op_remove_item', text="", index=index, icon_only=True, icon='REMOVE')
classlist.append(PRM_UL_BakeDefList)

# ================================================================================
# OPERTATORS
# ================================================================================

class PRM_OT_BakeFrom4(bpy.types.Operator):
    """Composite an image using 4 material outputs"""
    bl_idname = "dmr.bake_from_4"
    bl_label = "Bake From 4"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Save on complete
    save_image : bpy.props.BoolProperty(
        name="Save on Complete", 
        default=True,
        description="Save and update image on completion."
        )
    
    # Material outputs
    output1 : bpy.props.StringProperty()
    output2 : bpy.props.StringProperty()
    output3 : bpy.props.StringProperty()
    output4 : bpy.props.StringProperty()
    
    # Bake types
    type1 : bpy.props.EnumProperty(items=Items_BakeTypes)
    type2 : bpy.props.EnumProperty(items=Items_BakeTypes)
    type3 : bpy.props.EnumProperty(items=Items_BakeTypes)
    type4 : bpy.props.EnumProperty(items=Items_BakeTypes)
    
    # Material channels
    channel1: bpy.props.EnumProperty(default='R', items=Items_ColorChannels)
    channel2: bpy.props.EnumProperty(default='R', items=Items_ColorChannels)
    channel3: bpy.props.EnumProperty(default='R', items=Items_ColorChannels)
    channel4: bpy.props.EnumProperty(default='R', items=Items_ColorChannels)
    
    samples : bpy.props.IntVectorProperty(name="Samples", size=4, default=(1,1,1,1))
    color_space : bpy.props.EnumProperty(
        name="Color Space",
        default='Linear', 
        items=Items_ColorSpace,
        )
    
    @classmethod
    def poll(self, context):
        return context.scene.render.engine == 'CYCLES' and ObjectRenderEnabled(context.active_object)
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        
        c = layout.column()
        c.label(text="Material Outputs")
        r = c.row(align=1)
        cc = [r.column(align=1) for i in range(0, 4)]
        cc[0].label(text="Output Label")
        cc[1].label(text="Type")
        cc[2].label(text="Read Channel")
        cc[3].label(text="Samples")
        
        for i, ci in enumerate('1234'):
            r = c.row(align=1)
            cc[0].prop(self, 'output'+ci, text="")
            cc[1].prop(self, 'type'+ci, text="")
            cc[2].prop(self, 'channel'+ci, text="")
            cc[3].prop(self, 'samples', index=i, text="")
        
        layout.prop(self, 'color_space')
        layout.prop(self, 'save_image')
    
    def execute(self, context):
        return ImageFrom4(self, context, 
            self.output1,
            self.output2,
            self.output3,
            self.output4,
            
            [self.type1, self.type2, self.type3, self.type4],
            channels=(self.channel1, self.channel2, self.channel3, self.channel4),
            samples=self.samples,
            color_space=self.color_space,
            save_image=self.save_image,
            )
        
        return {'FINISHED'}
classlist.append(PRM_OT_BakeFrom4)

# ================================================================================
# PANELS
# ================================================================================

class PRM_PT_BakeTricksPanel(bpy.types.Panel):
    bl_label = "Bake Tricks"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = "UI"
    bl_category = "Bake"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        render = scene.render
        cycles = scene.cycles
        
        master = context.scene.bake_tricks
        
        # Item List
        r = layout.row()
        c = r.column(align=1)
        c.template_list(
            "PRM_UL_BakeDefList", "", 
            master, "items", 
            master, "itemindex", 
            rows=3)
        
        c = r.column(align=1)
        c.prop(master, 'op_add_item', text="", icon='ADD')
        c.prop(master, 'op_remove_item', text="", icon='REMOVE')
        
        # Active Item
        activedef = context.scene.bake_tricks.GetActive()
        
        if activedef:
            c = layout.box().column()
            
            r = c.row()
            r.label(text="Color Space:")
            r.prop(activedef, 'color_space', text="")
            
            # Material Output Defs
            for item in activedef.items:
                r = c.row(align=1)
                rr = r.split(factor=0.35, align=1)
                rr.prop(item, 'output', text="")
                rr = rr.split(factor=0.4, align=1)
                rr.prop(item, 'type', text="")
                rr = rr.split(factor=0.5, align=1)
                
                rr.prop(item, 'channel', text="")
                rr.prop(item, 'samples', text="")
            
            # Bake Operator
            itemdata = activedef.Serialize()
            
            if context.scene.render.engine != 'CYCLES':
                c.prop(master, 'op_cycles', text="Switch To Cycles Rendering", toggle=True)
            else:
                op = c.operator("dmr.bake_from_4", text="Bake Using Defined Settings")
                op.output1, op.type1, op.channel1, op.samples[0] = itemdata[0]
                op.output2, op.type2, op.channel2, op.samples[1] = itemdata[1]
                op.output3, op.type3, op.channel3, op.samples[2] = itemdata[2]
                op.output4, op.type4, op.channel4, op.samples[3] = itemdata[3]
                op.color_space = activedef.color_space
        
        # Cycles Bake Settings
        c = layout.box().column()
        
        c.prop(cycles, "bake_type", text="Type")
        r = c.row(align=1)
        r.prop(cycles, "samples", text="Samples")
        r.prop(render.bake, "margin", text="Margin")
        
        c = c.column()
        c.scale_y = 1.5
        c.operator("object.bake", icon='RENDER_STILL').type = cycles.bake_type
        r = c.row(align=1)
classlist.append(PRM_PT_BakeTricksPanel)

# ----------------------------------------------------------------------------

class PRM_PT_BakeTricksPanel_Properties(bpy.types.Panel):
    bl_label = "Bake Panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    
    draw = PRM_PT_BakeTricksPanel.draw
classlist.append(PRM_PT_BakeTricksPanel_Properties)

# ================================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)
    
    bpy.types.Scene.bake_tricks = bpy.props.PointerProperty(name="PRM Bake Master", type=PRM_BakeTricks_Master)

def unregister():
    for c in classlist[::-1]:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()


