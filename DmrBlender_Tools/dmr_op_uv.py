import bpy
import os

classlist = []

# =============================================================================

class DMR_OP_FitMirrorModifierToUVEdge(bpy.types.Operator):
    """Sets the \"Mirror U\" value to object UV bounds"""
    bl_idname = "dmr.mirror_modifier_fit_to_uv_bounds"
    bl_label = "Fit Mirror Modifier U Offset to UV Bounds"
    bl_options = {'REGISTER', 'UNDO'}
    
    edge : bpy.props.EnumProperty(
        name="Edge", default = 0, items=(
            ('LEFT', "Left", "Fit to left bound of UVs"),
            ('RIGHT', "Right", "Fit to right bound of UVs"),
            ('CURSOR', "2D Cursor", "Fit to 2D Cursor"),
        ))
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        object = context.object
        uvlayer = object.data.uv_layers.active.data
        print([m.type for m in object.modifiers])
        
        bound = 0
        if self.edge == 'LEFT':
            bound = min([uv.uv[0] for uv in uvlayer])-0.5
        elif self.edge == 'RIGHT':
            bound = max([uv.uv[0] for uv in uvlayer])-0.5
        elif self.edge == 'RIGHT':
            bound = context.area.spaces.active.cursor_location[0]-0.5
        
        for m in context.object.modifiers:
            if m.type == 'MIRROR' and m.use_mirror_u:
                m.mirror_offset_u = bound*2
                print(bound)
        return {'FINISHED'}
classlist.append(DMR_OP_FitMirrorModifierToUVEdge)

# =============================================================================

class DMR_OP_FlipUVsAlongAnchor(bpy.types.Operator):
    """Flips selected UVs along anchor"""
    bl_idname = "dmr.flip_uvs_along_anchor"
    bl_label = "Flips UVs Along Anchor"
    bl_options = {'REGISTER', 'UNDO'}   
    
    anchor : bpy.props.EnumProperty(name="Side", items = (
        ('LEFT', "Left", "Flip over left side"),
        ('RIGHT', "Right", "Flip over right side")
    ))
    
    def execute(self, context):
        mode = context.active_object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        for obj in [x for x in bpy.context.selected_objects if x.type == 'MESH']:
            if not obj.data.uv_layers:
                continue
            uvlayer = obj.data.uv_layers.active
            selectedloops = [i for p in obj.data.polygons if p.select for i in p.loop_indices]
            targetloops = tuple([l for i,l in enumerate(uvlayer.data) if (l.select and i in selectedloops)])
            
            if self.anchor == 'LEFT':
                point = min([l.uv[0] for l in targetloops if l.uv[0] != 0.0])
                for l in targetloops:
                    l.uv[0] = point-(l.uv[0]-point)
            
            elif self.anchor == 'RIGHT':
                point = max([l.uv[0] for l in targetloops if l.uv[0] != 0.0])
                for l in targetloops:
                    l.uv[0] = point-(l.uv[0]-point)
        
        bpy.ops.object.mode_set(mode=mode)
        return {'FINISHED'}
classlist.append(DMR_OP_FlipUVsAlongAnchor)

# =============================================================================

class DMR_OT_MatchMirrorUVs(bpy.types.Operator):
    """Copies UVs of selected loops to loops mirrored along the X axis. Result can be offsetted and flipped."""
    bl_idname = "dmr.match_mirror_uv"
    bl_label = "Match Mirror UVs"
    bl_options = {'REGISTER', 'UNDO'}
    
    offset : bpy.props.FloatVectorProperty(name="Offset", size=2, default=(0.0, 0.0))
    flip : bpy.props.EnumProperty(name="Flip", items=(
        ('NONE', 'None', "No flip"),
        ('LEFT', 'Left', "Flip on left edge"),
        ('RIGHT', 'Right', "Flip on right edge")
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

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
