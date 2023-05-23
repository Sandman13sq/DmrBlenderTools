bl_info = {
    'name': 'Shape Key Snapshots',
    'description': 'Store shape key state as snapshots with a name and vertex group mask entry',
    'author': 'Dreamer13sq',
    'version': (0, 1),
    'blender': (3, 0, 0),
    'category': 'Mesh',
    'support': 'COMMUNITY',
}

import bpy

classlist = []

'# ================================================================================'
'# PROPERTY GROUPS'
'# ================================================================================'

class ShapeKeySnapshotEntry(bpy.types.PropertyGroup):
    key_name : bpy.props.StringProperty()
    value : bpy.props.FloatProperty()
classlist.append(ShapeKeySnapshotEntry)

# -------------------------------------------------------------------

# Holds keys and values for shape keys
class ShapeKeySnapshot(bpy.types.PropertyGroup):
    name : bpy.props.StringProperty(name="Name", default='New Snapshot')
    mask_group : bpy.props.StringProperty(name="Vertex Group", default="")
    mask_group2 : bpy.props.StringProperty(name="Vertex Group 2", default="")
    keys : bpy.props.CollectionProperty(type=ShapeKeySnapshotEntry)
    size : bpy.props.IntProperty(name="Size")
    
    def Copy(self, other):
        for i in range(0, len(self.keys)):
            self.keys.remove(0)
        for k2 in other.keys:
            k = self.keys.add()
            k.key_name = k2.key_name
            k.value = k2.value
        self.vertex_group = other.mask_group
        self.mask_group = other.mask_group
        self.mask_group2 = other.mask_group
        self.name = other.name
    
    def FromMesh(self, mesh):
        for i in range(0, len(self.keys)):
            self.keys.remove(0)
        
        for sk in mesh.shape_keys.key_blocks:
            if sk.value != 0.0:
                if not sk.mute:
                    k = self.keys.add()
                    k.key_name = sk.name
                    k.value = sk.value
    
    def ToMesh(self, mesh):
        key_blocks = mesh.shape_keys.key_blocks
            
        for k in self.keys:
            if k.key_name in key_blocks.keys():
                key_blocks[k.key_name].value = k.value
classlist.append(ShapeKeySnapshot)

# ----------------------------------------------------------------------------

# Holds snapshots
class SKSNAP_PG_SnapshotSet(bpy.types.PropertyGroup):
    size : bpy.props.IntProperty()
    items : bpy.props.CollectionProperty(type=ShapeKeySnapshot)
    active_index : bpy.props.IntProperty()
    
    op_add_item : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    op_remove_item : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    op_move_up : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    op_move_down : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    op_clear : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    
    def ActiveSnapshot(self):
        return self.items[self.active_index] if self.size > 0 else None
    
    def GetItem(self, index):
        return self.items[index] if self.size else None 
    
    def FindItem(self, name):
        return ([x for x in self.items if x.name == name]+[None])[0]
    
    def Add(self, name="New Snapshot"):
        item = self.items.add()
        self.size = len(self.items)
        item.name = name
        return item
    
    def RemoveAt(self, index):
        if len(self.items) > 0:
            self.items.remove(index)
            self.size = len(self.items)
            
            self.active_index = max(min(self.active_index, self.size-1), 0)
    
    def MoveItem(self, index, move_down=True):
        newindex = index + (1 if move_down else -1)
        self.items.move(index, newindex)
    
    def Update(self, context):
        # Add
        if self.op_add_item:
            self.op_add_item = False
            self.Add()
            self.active_index = self.size-1
        
        # Remove
        if self.op_remove_item:
            self.op_remove_item = False
            self.RemoveAt(self.active_index)
        
        # Move
        if self.op_move_down:
            self.op_move_down = False
            self.items.move(self.active_index, self.active_index+1)
            self.active_index = max(min(self.active_index+1, self.size-1), 0)
        
        if self.op_move_up:
            self.op_move_up = False
            self.items.move(self.active_index, self.active_index-1)
            self.active_index = max(min(self.active_index-1, self.size-1), 0)
        
        # Clear
        if self.op_clear:
            self.op_clear = False
            self.items.clear()
            self.size = 0
            self.active_index = 0
classlist.append(SKSNAP_PG_SnapshotSet)

# ----------------------------------------------------------------------------

# Holds snapsets
class SKSNAP_PG_Master(bpy.types.PropertyGroup):
    size : bpy.props.IntProperty()
    items : bpy.props.CollectionProperty(type=SKSNAP_PG_SnapshotSet)
    active_index : bpy.props.IntProperty()
    
    op_add_item : bpy.props.BoolProperty(name="Add Snapset", default=False, update=lambda s,c: s.Update(c))
    op_remove_item : bpy.props.BoolProperty(name="Remove Snapset", default=False, update=lambda s,c: s.Update(c))
    op_move_up : bpy.props.BoolProperty(name="Move Up", default=False, update=lambda s,c: s.Update(c))
    op_move_down : bpy.props.BoolProperty(name="Move Down", default=False, update=lambda s,c: s.Update(c))
    op_clear : bpy.props.BoolProperty(name="Clear", default=False, update=lambda s,c: s.Update(c))
    
    def ActiveSet(self):
        return self.items[self.active_index] if self.size > 0 else None
    
    def GetItem(self, index):
        return self.items[index] if self.size else None 
    
    def FindItem(self, name):
        return ([x for x in self.items if x.name == name]+[None])[0]
    
    def Add(self):
        item = self.items.add()
        self.size = len(self.items)
        item.name = "New Snapset"
        return item
    
    def RemoveAt(self, index):
        if len(self.items) > 0:
            self.items.remove(index)
            self.size = len(self.items)
            
            self.active_index = max(min(self.active_index, self.size-1), 0)
    
    def MoveItem(self, index, move_down=True):
        newindex = index + (1 if move_down else -1)
        self.items.move(index, newindex)
    
    def Update(self, context):
        # Add
        if self.op_add_item:
            self.op_add_item = False
            self.Add()
            self.active_index = self.size-1
        
        # Remove
        if self.op_remove_item:
            self.op_remove_item = False
            self.RemoveAt(self.active_index)
        
        # Move
        if self.op_move_down:
            self.op_move_down = False
            self.items.move(self.active_index, self.active_index+1)
            self.active_index = max(min(self.active_index+1, self.size-1), 0)
        
        if self.op_move_up:
            self.op_move_up = False
            self.items.move(self.active_index, self.active_index-1)
            self.active_index = max(min(self.active_index-1, self.size-1), 0)
        
        # Clear
        if self.op_clear:
            self.op_clear = False
            self.items.clear()
            self.size = 0
            self.active_index = 0
classlist.append(SKSNAP_PG_Master)

'# ================================================================================'
'# OPERATORS'
'# ================================================================================'

class ShapeKey_OP(bpy.types.Operator):
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        obj = context.object
        return (obj and obj.type in {'MESH', 'LATTICE', 'CURVE', 'SURFACE'})

# ----------------------------------------------------------------------------

class SKSNAP_OP_Snapshot_Add(ShapeKey_OP):
    """Adds new snapshot to list"""
    bl_idname = "sksnap.snapshot_add"
    bl_label = "Add Shape Key Snapshot"
    
    name : bpy.props.StringProperty()
    
    def execute(self, context):
        context.object.data.sksnap.ActiveSet().Add(self.name, context.object.data)
        return {'FINISHED'}
classlist.append(SKSNAP_OP_Snapshot_Add)

# ----------------------------------------------------------------------------

class SKSNAP_OP_Snapshot_Copy(ShapeKey_OP):
    """Duplicates snapshot"""
    bl_idname = "sksnap.snapshot_copy"
    bl_label = "Copy Shape Key Snapshot"
    
    index : bpy.props.IntProperty()
    
    def execute(self, context):
        snapset = context.object.data.sksnap.ActiveSet()
        snapset.Add().Copy(snapset.ActiveSnapshot())
        snapset.items.move(len(snapset.items)-1, self.index+1)
        snapset.index = self.index+1
        
        return {'FINISHED'}
classlist.append(SKSNAP_OP_Snapshot_Copy)

# ----------------------------------------------------------------------------

class SKSNAP_OP_Snapshot_Write(ShapeKey_OP):
    """Saves current shape key values to snapshot"""
    bl_idname = "sksnap.snapshot_write"
    bl_label = "Write Shape Key Snapshot"
    
    index : bpy.props.IntProperty()
    
    def execute(self, context):
        snapshot = context.object.data.sksnap.ActiveSet().ActiveSnapshot()
        snapshot.FromMesh(context.object.data)
        return {'FINISHED'}
classlist.append(SKSNAP_OP_Snapshot_Write)

# ----------------------------------------------------------------------------

class SKSNAP_OP_Snapshot_Apply(ShapeKey_OP):
    """Applies values from snapshot to mesh shape key values"""
    bl_idname = "sksnap.snapshot_apply"
    bl_label = "Write Shape Key Snapshot"
    
    index : bpy.props.IntProperty()
    clear : bpy.props.BoolProperty(name="Clear Other Keys", default=True)
    
    def execute(self, context):
        snapshot = context.object.data.sksnap.ActiveSet().ActiveSnapshot()
        mesh = context.object.data
        
        if self.clear:
            for sk in mesh.shape_keys.key_blocks:
                sk.value = 0.0
        
        snapshot.ToMesh(mesh)
        return {'FINISHED'}
classlist.append(SKSNAP_OP_Snapshot_Apply)

# ----------------------------------------------------------------------------

class SKSNAP_OP_Snapshot_Remove(ShapeKey_OP):
    """Removes Shape Key Snapshot from list"""
    bl_idname = "sksnap.snapshot_remove"
    bl_label = "Remove Shape Key Snapshot"
    
    index : bpy.props.IntProperty()
    
    def execute(self, context):
        snapset = context.object.data.sksnap.ActiveSet()
        snapset.RemoveAt(self.index)
        return {'FINISHED'}
classlist.append(SKSNAP_OP_Snapshot_Remove)

# ----------------------------------------------------------------------------

class SKSNAP_OP_Snapshot_Move(ShapeKey_OP):
    """Moves Shape Key Snapshot in list"""
    bl_idname = "sksnap.snapshot_move"
    bl_label = "Move Shape Key Snapshot"
    
    index : bpy.props.IntProperty()
    direction : bpy.props.EnumProperty(name="Direction", items=(
        ('UP', "Up", "Move snapshot up"),
        ('DOWN', "Down", "Move snapshot down"),
    ))
    
    def execute(self, context):
        snapset = context.object.data.sksnap.ActiveSet()
        offset = 1 if self.direction=='DOWN' else -1
        snapset.MoveItem(self.index, offset)
        snapset.active_index = ((snapset.active_index + offset) % snapset.size)
        return {'FINISHED'}
classlist.append(SKSNAP_OP_Snapshot_Move)

'# ================================================================================'
'# PANELS'
'# ================================================================================'

class SKSNAP_UL_ShapeKeySnapshot(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # Extended
        if context.scene.sksnap_extend_view:
            c = layout.column(align=1)
            r = c.row().split(factor=0.3)
            r.label(text=("(%d Keys)" % len(item.keys)) if len(item.keys) > 0 else "(No Keys)")
            rr = r.row(align=1)
            rr.prop_search(item, "mask_group", context.object, 'vertex_groups', text="", icon='GROUP_VERTEX')
            rr.prop_search(item, "mask_group2", context.object, 'vertex_groups', text="", icon='GROUP_VERTEX')
            r = c.row()
            r.prop(item, "name", text="", icon='RESTRICT_RENDER_OFF')
            c.separator()
        # Compact
        else:
            r = layout.row(align=1)
            rr = r.row()
            rr.scale_x = 0.6
            rr.label(text=("(%d Keys)" % len(item.keys)) if len(item.keys) > 0 else "")
            r.prop(item, "name", text="", icon='RESTRICT_RENDER_OFF')
            rr = r.row()
            rr.scale_x = 0.8
            rr.prop_search(item, "mask_group", context.object, 'vertex_groups', text="", icon='GROUP_VERTEX')
            rr = r.row()
classlist.append(SKSNAP_UL_ShapeKeySnapshot)

# -------------------------------------------------------------------

class SKSNAP_UL_ShapeKeySnapset(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=1)
        r.prop(item, 'name', text="", emboss=False)
        r.prop(item, 'items', text="", emboss=False)
classlist.append(SKSNAP_UL_ShapeKeySnapset)

# =================================================================================

class SKSNAP_PT_Master(bpy.types.Panel):
    bl_label = 'Shape Key Snapshot'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'
    
    @classmethod
    def poll(cls, context):
        obj = context.object
        return (obj and obj.type in {'MESH', 'LATTICE', 'CURVE', 'SURFACE'})
    
    def draw(self, context):
        layout = self.layout
classlist.append(SKSNAP_PT_Master)

# -------------------------------------------------------------------

class SKSNAP_PT_ShapeKeySnapsets(bpy.types.Panel):
    bl_label = 'Snapsets'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'
    bl_parent_id = 'SKSNAP_PT_Master'
    
    @classmethod
    def poll(cls, context):
        obj = context.object
        return (obj and obj.type in {'MESH'})
    
    def draw(self, context):
        layout = self.layout
        
        master = context.object.data.sksnap
        row = layout.row()
        row.template_list(
            "SKSNAP_UL_ShapeKeySnapset", "", 
            master, "items", 
            master, "active_index", 
            rows=4)
        
        col = row.column(align=True)
        
        col.prop(master, 'op_add_item', icon='ADD', text="")
        col.prop(master, 'op_remove_item', icon='REMOVE', text="")
        
        col.separator()
        
        col.prop(master, 'op_move_up', icon='TRIA_UP', text="")
        col.prop(master, 'op_move_down', icon='TRIA_DOWN', text="")
classlist.append(SKSNAP_PT_ShapeKeySnapsets)

# -------------------------------------------------------------------

class SKSNAP_PT_ShapeKeySnapshot(bpy.types.Panel):
    bl_label = 'Shape Key Snapshot'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'
    bl_parent_id = 'SKSNAP_PT_Master'
    
    @classmethod
    def poll(cls, context):
        obj = context.object
        return (obj and obj.type in {'MESH'})
    
    def draw(self, context):
        layout = self.layout
        
        mesh = context.object.data
        snapset = mesh.sksnap.ActiveSet()
        
        if snapset:
            i = snapset.active_index
            
            r = layout.row()
            r.prop(snapset, 'name', text="")
            r.prop(context.scene, 'sksnap_extend_view')
            
            row = layout.row()
            row.template_list(
                "SKSNAP_UL_ShapeKeySnapshot", "", 
                snapset, "items", 
                snapset, "active_index", 
                rows=6)
            
            col = row.column(align=True)
            
            col.operator('sksnap.snapshot_copy', icon='ADD', text="").index = i
            col.operator('sksnap.snapshot_remove', icon='REMOVE', text="").index = i
            
            col.separator()
            
            col.operator('sksnap.snapshot_write', icon='GREASEPENCIL', text="").index = i
            col.operator('sksnap.snapshot_apply', icon='ZOOM_SELECTED', text="").index = i
            
            col.separator()
            op = col.operator('sksnap.snapshot_move', icon='TRIA_UP', text="")
            op.index = i
            op.direction = 'UP'
            op = col.operator('sksnap.snapshot_move', icon='TRIA_DOWN', text="")
            op.index = i
            op.direction = 'DOWN'
        else:
            layout.prop(mesh.sksnap, 'op_add_item', toggle=True)
classlist.append(SKSNAP_PT_ShapeKeySnapshot)

'# ================================================================================'
'# REGISTER'
'# ================================================================================'

def register():
    for c in classlist:
        bpy.utils.register_class(c)
    
    bpy.types.Curve.shape_key_snapshots = bpy.props.CollectionProperty(name='Shape Key Snapshots', type=ShapeKeySnapshot)
    bpy.types.Curve.shape_key_snapshots_index = bpy.props.IntProperty(name='Shape Key Snapshot Index', default=0)
    
    bpy.types.Mesh.shape_key_snapshots = bpy.props.CollectionProperty(name='Shape Key Snapshots', type=ShapeKeySnapshot)
    bpy.types.Mesh.shape_key_snapshots_index = bpy.props.IntProperty(name='Shape Key Snapshot Index', default=0)
    
    bpy.types.Mesh.sksnap = bpy.props.PointerProperty(name='Shape Key Snapsets', type=SKSNAP_PG_Master)
    bpy.types.Scene.sksnap_extend_view = bpy.props.BoolProperty(name="Extend View", default=False)

def unregister():
    for c in classlist[::-1]:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()


