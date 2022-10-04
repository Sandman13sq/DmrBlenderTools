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

# =====================================================================================

class ShapeKeySnapshotEntry(bpy.types.PropertyGroup):
    key_name : bpy.props.StringProperty()
    value : bpy.props.FloatProperty()
classlist.append(ShapeKeySnapshotEntry)

# -------------------------------------------------------------------

class ShapeKeySnapshot(bpy.types.PropertyGroup):
    name : bpy.props.StringProperty(default='New Snapshot')
    mask_group : bpy.props.StringProperty(default='Vertex Group')
    keys : bpy.props.CollectionProperty(type=ShapeKeySnapshotEntry)
    
    def Copy(self, other):
        for i in range(0, len(self.keys)):
            self.keys.remove(0)
        for k2 in other.keys:
            k = self.keys.add()
            k.key_name = k2.key_name
            k.value = k2.value
        self.vertex_group = other.mask_group
        self.mask_group = other.mask_group
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

# =====================================================================================

class ShapeKey_OP(bpy.types.Operator):
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        obj = context.object
        return (obj and obj.type in {'MESH', 'LATTICE', 'CURVE', 'SURFACE'})

class SKSNAP_OP_Snapshot_Add(ShapeKey_OP): # -------------------------------
    """Adds new snapshot to list"""
    bl_idname = "sksnap.snapshot_add"
    bl_label = "Add Shape Key Snapshot"
    
    name : bpy.props.StringProperty()
    
    def execute(self, context):
        mesh = context.object.data
        snapshot = mesh.shape_key_snapshots.add()
        snapshot.name = self.name
        snapshot.FromMesh(mesh)
        return {'FINISHED'}
classlist.append(SKSNAP_OP_Snapshot_Add)

class SKSNAP_OP_Snapshot_Copy(ShapeKey_OP): # -------------------------------
    """Duplicates snapshot"""
    bl_idname = "sksnap.snapshot_copy"
    bl_label = "Copy Shape Key Snapshot"
    
    index : bpy.props.IntProperty()
    
    def execute(self, context):
        mesh = context.object.data
        mesh.shape_key_snapshots.add().Copy(mesh.shape_key_snapshots[self.index])
        mesh.shape_key_snapshots.move(len(mesh.shape_key_snapshots)-1, self.index+1)
        mesh.shape_key_snapshots_index = self.index+1
        return {'FINISHED'}
classlist.append(SKSNAP_OP_Snapshot_Copy)

class SKSNAP_OP_Snapshot_Write(ShapeKey_OP): # -------------------------------
    """Saves current shape key values to snapshot"""
    bl_idname = "sksnap.snapshot_write"
    bl_label = "Write Shape Key Snapshot"
    
    index : bpy.props.IntProperty()
    
    def execute(self, context):
        mesh = context.object.data
        mesh.shape_key_snapshots[self.index].FromMesh(mesh)
        return {'FINISHED'}
classlist.append(SKSNAP_OP_Snapshot_Write)

class SKSNAP_OP_Snapshot_Apply(ShapeKey_OP): # -------------------------------
    """Applies values from snapshot to mesh shape key values"""
    bl_idname = "sksnap.snapshot_apply"
    bl_label = "Write Shape Key Snapshot"
    
    index : bpy.props.IntProperty()
    clear : bpy.props.BoolProperty(name="Clear Other Keys", default=True)
    
    def execute(self, context):
        mesh = context.object.data
        
        if self.clear:
            for sk in mesh.shape_keys.key_blocks:
                sk.value = 0.0
        
        mesh.shape_key_snapshots[self.index].ToMesh(mesh)
        return {'FINISHED'}
classlist.append(SKSNAP_OP_Snapshot_Apply)

class SKSNAP_OP_Snapshot_Remove(ShapeKey_OP): # -------------------------------
    """Removes Shape Key Snapshot from list"""
    bl_idname = "sksnap.snapshot_remove"
    bl_label = "Remove Shape Key Snapshot"
    
    index : bpy.props.IntProperty()
    
    def execute(self, context):
        mesh = context.object.data
        mesh.shape_key_snapshots.remove(self.index)
        return {'FINISHED'}
classlist.append(SKSNAP_OP_Snapshot_Remove)

class SKSNAP_OP_Snapshot_Move(ShapeKey_OP): # -------------------------------
    """Moves Shape Key Snapshot in list"""
    bl_idname = "sksnap.snapshot_move"
    bl_label = "Move Shape Key Snapshot"
    
    index : bpy.props.IntProperty()
    direction : bpy.props.EnumProperty(name="Direction", items=(
        ('UP', "Up", "Move snapshot up"),
        ('DOWN', "Down", "Move snapshot down"),
    ))
    
    def execute(self, context):
        mesh = context.object.data
        n = len(mesh.shape_key_snapshots)
        
        if self.direction == 'UP':
            newindex = n-1 if self.index == 0 else self.index - 1
        elif self.direction == 'DOWN':
            newindex = 0 if self.index == n-1 else self.index + 1
        
        mesh.shape_key_snapshots_index = newindex
        mesh.shape_key_snapshots.move(self.index, newindex)
        return {'FINISHED'}
classlist.append(SKSNAP_OP_Snapshot_Move)

# -------------------------------------------------------------------

class SKSNAP_UL_ShapeKeySnapshot(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=1)
        rr = r.row()
        rr.scale_x = 0.6
        rr.label(text=("(%d Keys)" % len(item.keys)) if len(item.keys) > 0 else "")
        r.prop(item, "name", text="", icon='RESTRICT_RENDER_OFF')
        rr = r.row()
        rr.scale_x = 0.8
        rr.prop(item, "mask_group", text="", icon='GROUP_VERTEX')
        rr = r.row()
classlist.append(SKSNAP_UL_ShapeKeySnapshot)

# -------------------------------------------------------------------

class SKSNAP_PT_ShapeKeySnapshot(bpy.types.Panel):
    bl_label = 'Shape Key Snapshot'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'
    
    @classmethod
    def poll(cls, context):
        engine = context.engine
        obj = context.object
        return (obj and obj.type in {'MESH', 'LATTICE', 'CURVE', 'SURFACE'})
    
    def draw(self, context):
        layout = self.layout
        
        mesh = context.object.data
        snapshots = mesh.shape_key_snapshots
        i = mesh.shape_key_snapshots_index
        
        row = layout.row()
        row.template_list(
            "SKSNAP_UL_ShapeKeySnapshot", "", 
            mesh, "shape_key_snapshots", 
            mesh, "shape_key_snapshots_index", 
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

classlist.append(SKSNAP_PT_ShapeKeySnapshot)

# =====================================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)
    
    bpy.types.Curve.shape_key_snapshots = bpy.props.CollectionProperty(name='Shape Key Snapshots', type=ShapeKeySnapshot)
    bpy.types.Curve.shape_key_snapshots_index = bpy.props.IntProperty(name='Shape Key Snapshot Index', default=0)
    
    bpy.types.Mesh.shape_key_snapshots = bpy.props.CollectionProperty(name='Shape Key Snapshots', type=ShapeKeySnapshot)
    bpy.types.Mesh.shape_key_snapshots_index = bpy.props.IntProperty(name='Shape Key Snapshot Index', default=0)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
