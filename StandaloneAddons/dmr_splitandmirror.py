bl_info = {
    'name': 'Split and Mirror',
    'description': 'Operator to split active mesh in half and create a quick mirror modifier.\nSelection takes into account vertices that overlap from one side to another',
    'author': 'Dreamer13sq',
    'version': (1, 0),
    'blender': (3, 0, 0),
    'category': 'Mesh',
    'support': 'COMMUNITY',
    'doc_url': 'https://github.com/Dreamer13sq/DmrBlenderTools/wiki/Split-And-Mirror'
}

import bpy
import bmesh

classlist = []

# Auto Mirror burned me ONE too many times...
class DMR_OP_SplitAndMirror(bpy.types.Operator):
    bl_label = 'Split and Mirror'
    bl_idname = 'dmr.split_and_mirror'
    bl_description = 'Splits mesh and creates a mirror modifier at the top of the modifier stack'
    bl_options = {'REGISTER', 'UNDO'}
    
    merge_threshold : bpy.props.FloatProperty(
        name='Merge Threshold', default=0.001,
        description='Distance to merge vertices'
    )
    
    clipping : bpy.props.BoolProperty(
        name='Clipping', default=True,
        description='Prevent vertices from moving past mirror'
    )
    
    @classmethod
    def poll(self, context):
        return context.object
    
    def execute(self, context):
        thresh = self.merge_threshold
        
        obj = context.object
        mesh = obj.data
        
        lastmode = obj.mode
        
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh.update()
        
        bm = bmesh.new()
        bm.from_mesh(mesh)
        
        # Select all vertices
        vertices = bm.verts
        polygons = bm.faces
        
        # Deselect middle verts and right hand side verts
        middleverts = {v for v in vertices if v.co[0]*v.co[0] <= thresh*thresh}
        safeverts = {v for v in vertices if v.co[0] >= obj.dimensions[0]*0.1}
        
        bm.select_flush(0)
        for v in vertices:
            v.select_set(1)
        for v in middleverts:
            v.select_set(0)
        for v in safeverts:
            v.select_set(0)
        
        remainingverts = {v for v in vertices if ( (v not in middleverts) and (v not in safeverts) )}
        remainingpolys = {p for p in polygons if not p.select}
        
        # No middle seam, don't delete anything
        if not middleverts:
            safeverts = [v for v in vertices]
            remainingpolys = []
            remainingverts = []
        
        # Step by polygon to deselect vertices between right hand side and middle verts
        def IterativeSelect(v):
            #vertpolys = {p for p in remainingpolys if v.index in p.vertices}
            vertpolys = {p for p in v.link_faces if p in remainingpolys}
            for p in vertpolys:
                remainingpolys.discard(p)
            sisterverts = {
                v2 for p in vertpolys for v2 in p.verts if (v2.select and v2 in remainingverts)
            }
            
            for v2 in sisterverts:
                v2.select_set(0)
                remainingverts.discard(v2)
                IterativeSelect(v2)
        
        for v in safeverts:
            IterativeSelect(v)
        
        # From here only left hand verts are selected
        bmesh.ops.delete(bm, geom=[v for v in vertices if v.select], context='VERTS')
        bm.to_mesh(mesh)
        
        # Create Modifier
        m = obj.modifiers.new(name='Quick Mirror', type='MIRROR')
        bpy.ops.object.modifier_move_to_index(modifier=m.name, index=0)
        m.merge_threshold = self.merge_threshold
        m.use_clip = self.clipping
        
        bpy.ops.object.mode_set(mode=lastmode)
        
        return {'FINISHED'}
classlist.append(DMR_OP_SplitAndMirror)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
