import bpy
import mathutils

from bpy_extras.io_utils import ExportHelper, ImportHelper

RAMPPALETTESIGNATURE = "<RAMP_PALETTE>"

def NewNode(ndtree, type, label, location):
    if type[:6] == 'Shader' and ndtree.type == 'COMPOSITING':
        type = "Compositor" + type[6:]
    if type[:10] == 'Compositor' and ndtree.type == 'Shader':
        type = "Shader" + type[10:]
    
    nd = ndtree.nodes.new(type=type)
    nd.location = location
    nd.label, nd.name = [label]*2
    return nd

def LinkNodes(ndtree, n1, output_index, n2, input_index):
    return ndtree.links.new(
        (ndtree.nodes[n1] if isinstance(n1, str) else n1).outputs[output_index], 
        (ndtree.nodes[n2] if isinstance(n2, str) else n2).inputs[input_index]
        )

classlist = []

# =====================================================================================

class RampPalette_NodeGroup(bpy.types.PropertyGroup):
    def UpdateName(self, context):
        self.node_tree.name = self.name
        self.compositor_tree.name = self.name
    
    name : bpy.props.StringProperty(name="Name", default="Ramp Palette", update=UpdateName)
    node_tree : bpy.props.PointerProperty(type=bpy.types.NodeTree)
    compositor_tree : bpy.props.PointerProperty(type=bpy.types.NodeTree)
    collection : bpy.props.PointerProperty(type=bpy.types.Collection)
    
    color_index : bpy.props.IntProperty(name='Active Color Index')
    ramp_index : bpy.props.IntProperty(name='Active Ramp Index', update=lambda s,c: s.UpdateRampIndex())
    width : bpy.props.IntProperty(name='Width', default=8, min=2, max=32, update=lambda s,c: s.UpdateRamps())
    height : bpy.props.IntProperty(name='Height', default=4, min=1, max=8, update=lambda s,c: s.UpdateRamps())
    gamma_correct : bpy.props.BoolProperty( name='Gamma Correct', update=lambda s,c: s.UpdateGamma() )
    
    def GetObjects(self):
        if self.collection:
            return [obj for obj in self.collection.all_objects if obj.type == 'MESH']
        return bpy.context.selected_objects
    
    def UpdateGamma(self):
        self.node_tree.nodes['gamma'].inputs[1].default_value = 2.2 if self.gamma_correct else 1.0
    
    def Init(self):
        self.node_tree = bpy.data.node_groups.new(name=self.name + " - Material", type='ShaderNodeTree')
        self.compositor_tree = bpy.data.node_groups.new(name=self.name + " - Compositor", type='CompositorNodeTree')
        
        for ndtree in [self.node_tree, self.compositor_tree]:
            ndtree.inputs.new('NodeSocketFloat', "Palette Float")
            ndtree.inputs.new('NodeSocketFloat', "Palette Int")
            ndtree.outputs.new('NodeSocketColor', "Color")
            
            NewNode(ndtree, 'NodeFrame', RAMPPALETTESIGNATURE, (0, 400))
            
            NewNode(ndtree, 'NodeGroupInput', "input", (-1000, 0))
            NewNode(ndtree, 'ShaderNodeGamma', "gamma", (300, 0))
            NewNode(ndtree, 'NodeGroupOutput', "output", (500, 0))
            
            nd = NewNode(ndtree, 'ShaderNodeMath', "gt", (-800, 0))
            nd.operation = 'GREATER_THAN'
            nd.inputs[1].default_value = 0.0
            
            nd = NewNode(ndtree, 'ShaderNodeMath', "mul", (-600, 0))
            nd.operation = 'MULTIPLY'
            
            nd = NewNode(ndtree, 'ShaderNodeMath', "madd", (-800, -200))
            nd.operation = 'MULTIPLY_ADD'
            nd.inputs[1].default_value = 1/self.width
            nd.inputs[2].default_value = 1/self.width
            
            nd = NewNode(ndtree, 'ShaderNodeMath', "add", (-400, 0))
            nd.operation = 'ADD'
            nd.inputs[1].default_value = 1.0
            
            nd = NewNode(ndtree, 'ShaderNodeMath', "modulo", (-200, 0))
            nd.operation = 'MODULO'
            nd.inputs[1].default_value = 1.0
            
            LinkNodes(ndtree, "input", 1, "madd", 0)
            LinkNodes(ndtree, "input", 1, "gt", 0)
            LinkNodes(ndtree, "gt", 0, "mul", 0)
            
            LinkNodes(ndtree, "input", 0, "add", 1)
            LinkNodes(ndtree, "madd", 0, "mul", 1)
            LinkNodes(ndtree, "mul", 0, "add", 0)
            
            LinkNodes(ndtree, "add", 0, "modulo", 0)
            
        self.UpdateRamps()
        return self
    
    def Cleanup(self):
        if self.node_tree:
            bpy.data.node_groups.remove(self.node_tree)
        if self.compositor_tree:
            bpy.data.node_groups.remove(self.compositor_tree)
    
    def AddRamp(self):
        oldramps = self.GetColorRamps()
        
        if oldramps:
            e1 = [tuple(e.color) for e in self.GetColorRamps()[self.ramp_index].elements]
            self.height += 1
            
            r2 = [x for x in self.GetColorRamps() if x not in oldramps][0]
            
            for i in range(0, self.width):
                r2.elements[i].color = e1[i]
            self.ramp_index = list(self.GetColorRamps()).index(r2)
            
        else:
            self.height += 1
            self.ramp_index = 0
    
    def RemoveRamp(self, index):
        self.node_tree.nodes.remove( self.GetRampNodes()[index] )
        self.height = max(1, self.height-1)
    
    def MoveRamp(self, index, offset):
        nd1 = self.GetRampNodes()[index]
        nd2 = self.GetRampNodes()[(index+offset) % self.height]
        
        r1 = nd1.color_ramp
        r2 = nd2.color_ramp
        
        e1 = [tuple(e.color) for e in r1.elements]
        e2 = [tuple(e.color) for e in r2.elements]
        
        for i in range(0, self.width):
            r1.elements[i].color = e2[i]
            r2.elements[i].color = e1[i]
        
        labels = (nd1.label, nd2.label)
        nd1.label = labels[1]
        nd2.label = labels[0]
    
    def ActiveRamp(self):
        return self.node_tree.nodes["c%d"%ramp_index]
    
    def GetRampNodes(self, compositor=False):
        nodes = [nd for nd in (self.node_tree, self.compositor_tree)[compositor].nodes if nd.type == 'VALTORGB']
        nodes.sort(key=lambda x: x.name)
        return nodes
    
    def GetColorRamps(self, compositor=False):
        return [nd.color_ramp for nd in self.GetRampNodes(compositor)]
    
    def GetColorRamp(self, index):
        return self.node_tree.nodes["c%d"%index]
    
    def GetActiveElements(self):
        return [nd.color_ramp.elements[self.color_index] for nd in self.GetRampNodes()]
    
    def Resize(self, width=0, height=0):
        if height > 0:
            self.height = height
        if width > 0:
            self.width = width
    
    def ShiftElement(self, index, shift=1):
        i = self.color_index if index == None else index
        
        for ramp in self.GetColorRamps():
            elements = list(ramp.elements)
            e1, e2 = (elements[i], elements[(i+shift) % self.width])
            p = tuple(e1.color)
            e1.color = e2.color
            e2.color = p
        
        if index == None:
            self.color_index = (i+shift) % self.width
    
    def UpdateRamps(self):
        for compositor, ndtree in enumerate([self.node_tree, self.compositor_tree]):
            ramps = self.GetRampNodes(compositor)
            
            # Height
            if len(ramps) < self.height:
                for i in range(len(ramps), self.height):
                    NewNode(ndtree, 'ShaderNodeValToRGB', "", (0, -10000 - i*10))
            elif len(ramps) > self.height:
                for nd in ramps[::-1][:len(ramps)-self.height]:
                    ndtree.nodes.remove(nd)
            
            # Width
            for i, nd in enumerate(self.GetRampNodes(compositor)):
                ramp = nd.color_ramp
                nd.name = 'c%d' % i
                nd.location = (0, -i*200)
                
                while len(ramp.elements) < self.width:
                    e = ramp.elements.new(1.0)
                while len(ramp.elements) > self.width:
                    ramp.elements.remove(ramp.elements[-1])
                for j, e in enumerate(ramp.elements):
                    e.position = (j+0.5)/(self.width)
            
            nd = ndtree.nodes['madd']
            nd.inputs[1].default_value = 1/self.width
            nd.inputs[2].default_value = 1/self.width
        
        self.color_index = max(0, min(self.width-1, self.color_index))
        self.ramp_index = max(0, min(self.height-1, self.ramp_index))
        
    def UpdateRampIndex(self):
        if self.height > 0:
            index = self.ramp_index % self.height
            if index != self.ramp_index:
                self.ramp_index = index
                return
            
            for compositor, ndtree in enumerate([self.node_tree, self.compositor_tree]):
                ramps = self.GetRampNodes(compositor)
                LinkNodes(ndtree, 'modulo', 0, ramps[self.ramp_index], 0)
                LinkNodes(ndtree, ramps[self.ramp_index], 0, 'gamma', 0)
                LinkNodes(ndtree, 'gamma', 0, 'output', 0)
    
    def FromImage(self, image):
        self.width, self.height = image.size
        n = self.width * self.height
        
        pixels = tuple(image.pixels)
        
        rows = [
            [
                tuple(pixels[ (cy*self.width + cx) * 4: (cy*self.width + (cx+1)) * 4 ])
                for cx in range(0, self.width)
            ]
            for cy in range(0, self.height)
        ]
        
        rows = [
            [
                list(mathutils.Color(color[:3]).from_srgb_to_scene_linear())+[color[3]]
                for color in r
            ]
            for r in rows
        ]
        
        rows = rows[::-1]
        
        for ramps in [self.GetColorRamps(0), self.GetColorRamps(1)]:
            for ramp, row in zip(ramps, rows):
                for i, e in enumerate(ramp.elements):
                    e.color = row[i]
    
    def ToImage(self, image):
        image.scale(self.width, self.height)
        image.pixels = tuple(
            x
            for ramp in list(self.GetColorRamps())[::-1]
            for e in ramp.elements
            for x in e.color
        )
    
classlist.append(RampPalette_NodeGroup)

# -------------------------------------------------------------------

class RampPalette_Master(bpy.types.PropertyGroup):
    data : bpy.props.CollectionProperty(type=RampPalette_NodeGroup)
    data_index : bpy.props.IntProperty(name='Index')
    display_mode : bpy.props.EnumProperty(name='Display Mode', 
        items=(
            ('RAMP', "Active Ramp", "Show all colors for active slot"),
            ('COLOR', "Active Color", "Show all ramp colors for active color index")
    ))
    
    def Add(self):
        return self.data.add().Init()
    
    def Remove(self, index):
        self.data[index].Cleanup()
        self.data.remove(index)
        self.data_index = max(0, min(self.data_index, len(self.data)-1))
    
    def Active(self):
        return self.data[self.data_index] if self.data else None
    
    def SearchNodeGroups(self):
        for ng in bpy.data.node_groups:
            if ng not in [x.node_tree for x in self.data]:
                if sum([1 for nd in ng.nodes if nd.label == '<RAMP_PALETTE>']):
                    entry = self.data.add()
                    entry.name = ng.name
                    entry.node_tree = ng
                    rampnodes = entry.GetRampNodes()
                    rampdata = [
                        [tuple(e.color) for e in nd.color_ramp.elements]
                        for nd in rampnodes
                    ]
                    
                    height = len(rampnodes)
                    width = len(rampdata[0])
                    entry.height = height
                    entry.width = width
                    
                    for i, nd in enumerate(entry.GetRampNodes()):
                        for j, e in enumerate(nd.color_ramp.elements):
                            e.color = rampdata[i][j]
        
classlist.append(RampPalette_Master)

"# ============================================================================================"
"# OPERATORS"
"# ============================================================================================"

class RampPalette_OP(bpy.types.Operator):
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return 1

# -------------------------------------------------------------------
class RAMPPALETTE_OP_Palette_Add(RampPalette_OP): 
    """Adds new palette to list"""
    bl_idname = "ramppalette.palette_add"
    bl_label = "Add Palette"
    
    def execute(self, context):
        context.scene.ramp_palettes.Add()
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Palette_Add)

# -------------------------------------------------------------------
class RAMPPALETTE_OP_Palette_Remove(RampPalette_OP): 
    """Removes Palette from list"""
    bl_idname = "ramppalette.palette_remove"
    bl_label = "Remove Palette"
    index : bpy.props.IntProperty()
    
    def execute(self, context):
        context.scene.ramp_palettes.Remove(self.index)
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Palette_Remove)

# -------------------------------------------------------------------
class RAMPPALETTE_OP_Ramp_Add(RampPalette_OP): 
    """Adds new ramp to palette"""
    bl_idname = "ramppalette.ramp_add"
    bl_label = "Add Ramp"
    
    def execute(self, context):
        context.scene.ramp_palettes.Active().AddRamp()
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Ramp_Add)

# -------------------------------------------------------------------
class RAMPPALETTE_OP_Ramp_Remove(RampPalette_OP): 
    """Removes ramp from palette"""
    bl_idname = "ramppalette.ramp_remove"
    bl_label = "Remove Ramp"
    index : bpy.props.IntProperty()
    
    def execute(self, context):
        context.scene.ramp_palettes.Active().RemoveRamp(self.index)
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Ramp_Remove)

# -------------------------------------------------------------------
class RAMPPALETTE_OP_Ramp_Move(RampPalette_OP): 
    """Moves ramp"""
    bl_idname = "ramppalette.ramp_move"
    bl_label = "Move Ramp"
    index : bpy.props.IntProperty()
    offset : bpy.props.IntProperty()
    
    def execute(self, context):
        context.scene.ramp_palettes.Active().MoveRamp(self.index, self.offset)
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Ramp_Move)

# -------------------------------------------------------------------
class RAMPPALETTE_OP_Color_Shift(RampPalette_OP): 
    """Moves color of all ramps"""
    bl_idname = "ramppalette.color_shift"
    bl_label = "Shift Element"
    index : bpy.props.IntProperty()
    shift : bpy.props.IntProperty(default=1)
    
    def execute(self, context):
        context.scene.ramp_palettes.Active().ShiftElement(None, self.shift)
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Color_Shift)

# -------------------------------------------------------------------
class RAMPPALETTE_OP_Set_UV(RampPalette_OP): 
    """Sets palette index"""
    bl_idname = "ramppalette.set_uv"
    bl_label = "Set Palette Color"
    bl_options = {'REGISTER', 'UNDO'}
    
    index : bpy.props.IntProperty(name="Index")
    
    def execute(self, context):
        mode = context.object.mode
        bpy.ops.object.mode_set(mode="OBJECT")
        
        active = context.scene.ramp_palettes.Active()
        
        uv = ( (self.index + 0.5) / active.width, 0.0 )
        
        for obj in list(set(list(context.selected_objects) + [context.object])):
            if "palette" not in obj.data.uv_layers:
                obj.data.uv_layers.new(name="palette")
            lyrdata = obj.data.uv_layers['palette'].data
            
            vertices = tuple(obj.data.vertices)
            loops = tuple(obj.data.loops)
            
            targetpolys = tuple([p for p in obj.data.polygons if p.select])
            usedvertices = tuple([v for p in targetpolys for v in p.vertices])
            targetloops = [l for p in targetpolys for l in p.loop_indices]
            targetloops += [l.index for l in loops if (vertices[l.vertex_index].select and l.vertex_index not in usedvertices)]
            
            print(len(targetloops))
            
            for l in tuple(targetloops):
                lyrdata[l].uv = uv
        
        bpy.ops.object.mode_set(mode=mode)
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Set_UV)

# ----------------------------------------------------------------------------------
class RAMPPALETTE_OP_UVFromProperty(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "ramppalette.uv_from_object_property"
    bl_label = "Palette Color From Object Property"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        mode = context.object.mode
        bpy.ops.object.mode_set(mode="OBJECT")
        
        active = context.scene.ramp_palettes.Active()
        
        for obj in context.selected_objects:
            print(obj.name)
            for k in obj.keys():
                if k.lower() == 'palette':
                    uv = ( (obj[k] + 0.5) / active.width, 0.0 )
                    
                    if "palette" not in obj.data.uv_layers:
                        obj.data.uv_layers.new(name="palette")
                    lyrdata = obj.data.uv_layers['palette'].data
                    
                    for l in lyrdata:
                        l.uv = uv
                    break
        
        bpy.ops.object.mode_set(mode=mode)
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_UVFromProperty)

# -------------------------------------------------------------------
class RAMPPALETTE_OP_MoveColor(RampPalette_OP): 
    """Sets palette index"""
    bl_idname = "ramppalette.move_color"
    bl_label = "Set Palette Color"
    bl_options = {'REGISTER', 'UNDO'}
    
    index : bpy.props.IntProperty()
    offset : bpy.props.IntProperty(default=1)
    all_ramps : bpy.props.BoolProperty(default=True)
    
    def execute(self, context):
        mode = context.object.mode
        bpy.ops.object.mode_set(mode="OBJECT")
        
        active = context.scene.ramp_palettes.Active()
        active.ShiftElement(self.index, self.offset)
        
        uvx1 = (self.index + 0.5) / active.width
        uvx2 = (self.index + self.offset + 0.5) / active.width
        uvw = 1/active.width
        
        for obj in active.GetObjects():
            if "palette" not in obj.data.uv_layers:
                obj.data.uv_layers.new(name="palette")
            
            for uv in obj.data.uv_layers['palette'].data:
                if uv.uv[0] == uvx1:
                    uv.uv[0] = uvx2
                elif uv.uv[0] == uvx2:
                    uv.uv[0] = uvx1
        
        bpy.ops.object.mode_set(mode=mode)
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_MoveColor)

# ----------------------------------------------------------------------------------
class RAMPPALETTE_OP_Import(bpy.types.Operator, ImportHelper):
    """Tooltip"""
    bl_idname = "ramppalette.import"
    bl_label = "Import Palette from File"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".png"
    filter_glob: bpy.props.StringProperty(default="*"+filename_ext, options={'HIDDEN'}, maxlen=255)
    
    gamma_correct : bpy.props.BoolProperty(name="Gamma Corrected", default=True)
    
    @classmethod
    def poll(self, context):
        return context.scene.ramp_palettes.Active()
    
    def execute(self, context):
        image = bpy.data.images.load(self.filepath, check_existing=False)
        image.colorspace_settings.name = 'sRGB' if self.gamma_correct else 'Linear'
        context.scene.ramp_palettes.Active().FromImage(image)
        bpy.data.images.remove(image)
        self.report({'INFO'}, 'Palette read from "%s"' % self.filepath)
        
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Import)

# ----------------------------------------------------------------------------------
class RAMPPALETTE_OP_Export(bpy.types.Operator, ExportHelper):
    """Tooltip"""
    bl_idname = "ramppalette.export"
    bl_label = "Export Palette to File"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".png"
    filter_glob: bpy.props.StringProperty(default="*"+filename_ext, options={'HIDDEN'}, maxlen=255)
    
    @classmethod
    def poll(self, context):
        return context.scene.ramp_palettes.Active()
    
    def execute(self, context):
        palette = context.scene.ramp_palettes.Active()
        
        image = bpy.data.images.new("__temp_ramppalette", palette.width, palette.height, alpha=True)
        image.colorspace_settings.name = 'sRGB' if palette.gamma_correct else 'Linear'
        image.filepath = self.filepath
        image.file_format = 'PNG'
        image.update()
        context.scene.ramp_palettes.Active().ToImage(image)
        image.save()
        bpy.data.images.remove(image)
        self.report({'INFO'}, 'Palette saved to "%s"' % self.filepath)
        
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Export)

# ----------------------------------------------------------------------------------
class RAMPPALETTE_OP_SearchNodeGroups(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "ramppalette.search_node_groups"
    bl_label = "Search Node Groups"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.scene.ramp_palettes.SearchNodeGroups()
        
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_SearchNodeGroups)

'# ================================================================================================================='
'# PANELS'
'# ================================================================================================================='

class RAMPPALLETTE_UL_PaletteList(bpy.types.UIList):
    def draw_item(self, _context, layout, _data, item, icon, _active_data_, _active_propname, _index):
        r = layout.row()
        r.prop(item, "name", text="", emboss=False, icon_value=icon)
        r.operator('ramppalette.palette_remove', text="", icon='REMOVE').index=_index
classlist.append(RAMPPALLETTE_UL_PaletteList)

# -------------------------------------------------------------------

class RAMPPALETTE_PT_RampPalettePanel(bpy.types.Panel):
    bl_label = "Ramp Palettes"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Edit" # Name of sidebar
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        master = context.scene.ramp_palettes
        layout = self.layout
        
classlist.append(RAMPPALETTE_PT_RampPalettePanel)

# -------------------------------------------------------------------

class RAMPPALETTE_PT_RampPalettePanel_Characters(bpy.types.Panel):
    bl_label = "Node Groups"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Edit" # Name of sidebar
    bl_parent_id = 'RAMPPALETTE_PT_RampPalettePanel'
    
    def draw(self, context):
        master = context.scene.ramp_palettes
        layout = self.layout
        
        r = layout.row()
        r.operator('ramppalette.palette_add', icon='ADD')
        
        # Palette List
        layout.template_list("RAMPPALLETTE_UL_PaletteList", "", master, 'data', master, "data_index", rows=4)
    
classlist.append(RAMPPALETTE_PT_RampPalettePanel_Characters)

# -------------------------------------------------------------------

class RAMPPALETTE_PT_RampPalettePanel_ActiveCharacter(bpy.types.Panel):
    bl_label = "Active Palette"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Edit" # Name of sidebar
    bl_parent_id = 'RAMPPALETTE_PT_RampPalettePanel'
    
    def draw(self, context):
        master = context.scene.ramp_palettes
        layout = self.layout
        
        # Ramp list
        b = layout.column()
        ramppalette = master.Active()
        
        if ramppalette:
            b.prop(ramppalette, 'collection', text="")
            
            c = b.column()
            
            r = c.row()
            r.operator('ramppalette.import', text="Import Image")
            r.operator('ramppalette.export', text="Export Image")
            
            r = c.row()
            rr = r.row(align=1)
            rr.prop(ramppalette, 'width')
            rr.prop(ramppalette, 'height')
            r.prop(ramppalette, 'gamma_correct', text="", icon='CON_TRANSLIKE', toggle=1)
            
            r = c.row()
            r.operator('ramppalette.ramp_add', icon='ADD')
            
            # Draw Active Elements
            b = layout.box()
            
            if master.display_mode == 'RAMP':
                rampnodes = ramppalette.GetRampNodes()
                activenode = rampnodes[ramppalette.ramp_index]
                
                c = b.column()
                c.row().prop(master, 'display_mode', expand=True)
                r = c.row()
                r.prop(ramppalette, 'ramp_index', text=activenode.label)
                
                bb = b.box().column(align=1)
                
                for i, e in enumerate(activenode.color_ramp.elements):
                    if (i % 8) == 0:
                        r = bb.row(align=1)
                    c = r.column(align=0)
                    
                    rr = c.row(align=1)
                    rr.prop(e, 'color', text="")
                    rr.operator('ramppalette.set_uv', text='', icon='BRUSH_DATA').index=i
                    
                    rr = c.row(align=1)
                    rr.scale_y = 0.5
                    op = rr.operator('ramppalette.move_color', text='', icon='TRIA_LEFT')
                    op.index = i
                    op.offset = -1
                    op = rr.operator('ramppalette.move_color', text='', icon='TRIA_RIGHT')
                    op.index = i
                    op.offset = 1
                
            else:
                rampnodes = ramppalette.GetRampNodes()
                activenode = rampnodes[ramppalette.ramp_index]
                
                c = b.column()
                c.row().prop(master, 'display_mode', expand=True)
                r = c.row()
                elements = ramppalette.GetActiveElements()
                
                bb = b.box().column(align=1)
                
            
            
classlist.append(RAMPPALETTE_PT_RampPalettePanel_ActiveCharacter)

# -------------------------------------------------------------------

class RAMPPALETTE_PT_RampPalettePanel_Ramps(bpy.types.Panel):
    bl_label = "Color Ramps"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Edit" # Name of sidebar
    bl_parent_id = 'RAMPPALETTE_PT_RampPalettePanel'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        master = context.scene.ramp_palettes
        layout = self.layout
        ramppalette = master.Active()
        
        if ramppalette:
            # Draw ramps
            rampnodes = ramppalette.GetRampNodes()
            
            for i, nd in enumerate(rampnodes):
                c = layout.column(align=1)
                
                c.prop(nd, "label", text="")
                
                cc = c.column(align=1)
                cc.scale_y = 0.7
                
                rr = cc.row(align=0)
                rr.column().template_color_ramp(nd, "color_ramp", expand=True)
                c = rr.column(align=1)
                c.operator('ramppalette.ramp_remove', text="", icon='REMOVE').index = i
                op = c.operator('ramppalette.ramp_move', text="", icon='TRIA_UP')
                op.index = i
                op.offset = -1
                op = c.operator('ramppalette.ramp_move', text="", icon='TRIA_DOWN')
                op.index = i
                op.offset = 1
    
classlist.append(RAMPPALETTE_PT_RampPalettePanel_Ramps)

# -------------------------------------------------------------------

class RAMPPALETTE_PT_RampPalettePanel_Ramps(bpy.types.Panel):
    bl_label = "Color Ramps"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Edit" # Name of sidebar
    bl_parent_id = 'RAMPPALETTE_PT_RampPalettePanel'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        master = context.scene.ramp_palettes
        layout = self.layout
        ramppalette = master.Active()
        
        if ramppalette:
            # Draw ramps
            rampnodes = ramppalette.GetRampNodes()
            
            for i, nd in enumerate(rampnodes):
                c = layout.column(align=1)
                
                c.prop(nd, "label", text="")
                
                cc = c.column(align=1)
                cc.scale_y = 0.7
                
                rr = cc.row(align=0)
                rr.column().template_color_ramp(nd, "color_ramp", expand=True)
                c = rr.column(align=1)
                c.operator('ramppalette.ramp_remove', text="", icon='REMOVE').index = i
                op = c.operator('ramppalette.ramp_move', text="", icon='TRIA_UP')
                op.index = i
                op.offset = -1
                op = c.operator('ramppalette.ramp_move', text="", icon='TRIA_DOWN')
                op.index = i
                op.offset = 1
    
classlist.append(RAMPPALETTE_PT_RampPalettePanel_Ramps)

'# ================================================================================================================='
'# PANELS'
'# ================================================================================================================='

def register():
    for c in classlist:
        bpy.utils.register_class(c)
    
    bpy.types.Scene.ramp_palettes = bpy.props.PointerProperty(name='Ramp Palette Master', type=RampPalette_Master)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()

# Run on file start
bpy.data.texts[__file__[__file__.rfind("\\")+1:]].use_module = True
