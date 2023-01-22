import bpy

context = bpy.context

def EvaluateIslands():
    obj = context.object
    
    lastmode = obj.mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    uvlyr = obj.data.uv_layers.active
    uvdata = tuple(uvlyr.data)
    
    polygons = tuple([p for p in obj.data.polygons if p.select])
    targetloops = tuple(set([l for p in obj.data.polygons if p.select for l in p.loop_indices]))
    uvpool = tuple([uvdata[l] for l in targetloops])
    
    def SharedUVs(p1, p2):
        return sum([(uvdata[l1].uv == uvdata[l2].uv) for l1 in p1.loop_indices for l2 in p2.loop_indices]) > 0
    
    nlast = -1
    islands = [[p] for p in polygons]
    
    while nlast != len(islands):
        nlast = len(islands)
        
        for is1 in islands:
            for is2 in islands:
                if is1 == is2:
                    continue
                
                for p1 in is1:
                    for p2 in is2:
                        if SharedUVs(p1, p2):
                            is1 += is2
                            is2.clear()
                            break
        
        for island in islands[::-1]:
            if len(island) == 0:
                islands.remove(island)
        
        print(len(islands))
    
    uvislands = [ list(set(uvdata[l] for p in island for l in p.loop_indices)) for island in islands ]
    
    for island in uvislands:
        center = obj.location.to_2d()
        center.zero()
        
        for uv in island:
            center += uv.uv
        
        center /= len(island)
        
        for uv in island:
            uv.uv -= center
    
    bpy.ops.object.mode_set(mode=lastmode)
    
EvaluateIslands()


