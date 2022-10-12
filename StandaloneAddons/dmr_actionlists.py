bl_info = {
    'name': 'Action Lists',
    'description': 'Struct stored in scene that holds a list of actions. Each armature can be assigned a list.',
    'author': 'Dreamer13sq',
    'version': (1, 0),
    'blender': (3, 0, 0),
    'category': 'Animation',
    'support': 'COMMUNITY',
}

import bpy

classlist = []

def GetListItems(self, context):
    return [
        (str(i), '%s' % (x.name), x.name)
        for i, x in enumerate(context.scene.actionlists)
    ]

def FindContextArmature(context):
    objs = ([x for x in list(context.selected_objects) + [context.object, context.object.find_armature() if context.object else None] if (x and x.type == 'ARMATURE')])
    return objs[0] if objs else None

def ActiveList(self, context):
    sc = context.scene
    armobj = FindContextArmature(context)
    if armobj:
        return sc.actionlists[int(armobj.data.actionlists_index)]
    elif sc.actionlists:
        return sc.actionlists[int(sc.actionlists_index)]
    return None

def UpdateListIndices(self, context):
    sc = context.scene
    if len(sc.actionlists) > 0:
        for i, e in enumerate(sc.actionlists):
            e.index = i
        sc.actionlists_index = str(max(0, min(int(sc.actionlists_index), len(sc.actionlists)-1)))
        for a in bpy.data.armatures:
            a.actionlists_index = str(max(0, min(int(a.actionlists_index), len(sc.actionlists)-1)))

# =====================================================================================

class ActionListEntry(bpy.types.PropertyGroup):
    action : bpy.props.PointerProperty(type=bpy.types.Action)
classlist.append(ActionListEntry)

# -----------------------------------------------------------------------

class ActionList(bpy.types.PropertyGroup):
    size : bpy.props.IntProperty()
    entries : bpy.props.CollectionProperty(type=ActionListEntry)
    entryindex : bpy.props.IntProperty()
    index : bpy.props.IntProperty(default=0)
    
    def CopyFrom(self, other):
        for e in other.entries:
            self.Add(e.action)
    
    def GetActions(self):
        return [x.action for x in self.entries]
    
    def Contains(self, action):
        return [1 for x in self.entries if x.action == action]
    
    def Add(self, action):
        if not self.Contains(action):
            e = self.entries.add()
            e.action = action
            self.size = len(self.entries)
            self.entryindex = self.size-1
    
    def FromSearch(self, header):
        for a in bpy.data.actions:
            if a.name[:len(header)] == header:
                self.Add(a)
    
    def Remove(self, action):
        for i, e in enumerate(self.entries):
            if e.name == action.name:
                self.entries.remove(i)
                break
        
        self.size = len(self.entries)
        self.entryindex = max(0, min(self.entryindex, self.size-1))
    
    def RemoveAt(self, index=None):
        if index == None:
            index = self.entryindex
        
        if index < self.size:
            self.entries.remove(index)
        
        self.size = len(self.entries)
        self.entryindex = max(0, min(self.entryindex, self.size-1))
    
    def Clear(self):
        while len(self.entries) > 0:
            self.entries.remove(0)
        
        self.size = len(self.entries)
        self.entryindex = max(0, min(self.entryindex, self.size-1))
classlist.append(ActionList)

# =====================================================================================

class DMR_OP_ActionList_AddList(bpy.types.Operator):
    bl_idname = "dmr.actionlist_list_add"
    bl_label = "Add Export List"
    bl_description = "Adds action list"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        sc = context.scene
        
        activelist = ActiveList(self, context)
        newlist = sc.actionlists.add()
        
        # Copy from other list
        if activelist:
            listnames = [x.name for x in context.scene.actionlists]
            newlist.name = activelist.name
            dupindex = 0
            while (newlist.name in listnames):
                dupindex += 1
                newlist.name = activelist.name+'.'+str(dupindex).rjust(3, '0')
            
            newlist.CopyFrom(activelist)
        # Fresh list
        else:
            newlist.name = 'New Action List'
        
        UpdateListIndices(self, context)
        
        sc.actionlists_index = str(newlist.index)
        
        return {'FINISHED'}
classlist.append(DMR_OP_ActionList_AddList)

# ---------------------------------------------------------------------------

class DMR_OP_ActionList_RemoveList(bpy.types.Operator):
    bl_idname = "dmr.actionlist_list_remove"
    bl_label = "Remove Export List"
    bl_description = "Removes export list"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return ActiveList(self, context)
    
    def execute(self, context):
        sc = context.scene
        activelist = ActiveList(self, context)
        # Clamp BEFORE removing list
        sc.actionlists_index = str(max(0, min(int(sc.actionlists_index)-1, len(sc.actionlists)-1)))
        
        context.scene.actionlists.remove(activelist.index)
        UpdateListIndices(self, context)
        
        return {'FINISHED'}
classlist.append(DMR_OP_ActionList_RemoveList)

# ---------------------------------------------------------------------------

class DMR_OP_ActionList_AddEntry(bpy.types.Operator):
    bl_idname = "dmr.actionlist_entry_add"
    bl_label = "Add Entry to Export List"
    bl_description = "Adds entry to Export List"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return ActiveList(self, context) != None
    
    def execute(self, context):
        ActiveList(self, context).Add()
        return {'FINISHED'}
classlist.append(DMR_OP_ActionList_AddEntry)

# ---------------------------------------------------------------------------

class DMR_OP_ActionList_RemoveEntry(bpy.types.Operator):
    bl_idname = "dmr.actionlist_entry_remove"
    bl_label = "Remove Entry from Export List"
    bl_description = "Removes entry from export list"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return ActiveList(self, context)
    
    def execute(self, context):
        ActiveList(self, context).RemoveAt()
        return {'FINISHED'}
classlist.append(DMR_OP_ActionList_RemoveEntry)

# ---------------------------------------------------------------------------

class DMR_OP_ActionList_MoveEntry(bpy.types.Operator):
    bl_idname = "dmr.actionlist_entry_move"
    bl_label = "Move Export List Entry"
    bl_description = "Moves entry up or down on list"
    bl_options = {'REGISTER', 'UNDO'}
    
    direction : bpy.props.EnumProperty(
        name="Direction",
        description='Direction to move layer',
        items=(
            ('UP', 'Up', 'Move entry up'),
            ('DOWN', 'Down', 'Move entry down'),
            ('TOP', 'Top', 'Move entry to top of list'),
            ('BOTTOM', 'Bottom', 'Move entry to bottom of list'),
        )
    )
    
    @classmethod
    def poll(self, context):
        return ActiveList(self, context)
    
    def execute(self, context):
        activelist = ActiveList(self, context)
        entryindex = activelist.entryindex
        newindex = entryindex
        n = len(activelist.entries)
        
        if self.direction == 'UP':
            newindex = entryindex-1 if entryindex > 0 else n-1
        elif self.direction == 'DOWN':
            newindex = entryindex+1 if entryindex < n-1 else 0
        elif self.direction == 'TOP':
            newindex = 0
        elif self.direction == 'BOTTOM':
            newindex = n-1
        
        activelist.entries.move(entryindex, newindex)
        activelist.entryindex = newindex
        
        return {'FINISHED'}
classlist.append(DMR_OP_ActionList_MoveEntry)

# ---------------------------------------------------------------------------

class DMR_OP_ActionList_FromSearch(bpy.types.Operator):
    bl_idname = "dmr.actionlist_fromsearch"
    bl_label = "Add Actions from Search"
    bl_description = "Removes entry from export list"
    bl_options = {'REGISTER', 'UNDO'}
    
    header : bpy.props.StringProperty(
        name="Action Header", 
        description="Actions that start with this string will be added"
    )
    
    @classmethod
    def poll(self, context):
        return ActiveList(self, context)
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        ActiveList(self, context).FromSearch(self.header)
        return {'FINISHED'}
classlist.append(DMR_OP_ActionList_FromSearch)

# ---------------------------------------------------------------------------

class DMR_OP_SetContextArmatureAction(bpy.types.Operator):
    bl_idname = "dmr.set_context_armature_action"
    bl_label = "Set Context Armature Action"
    bl_description = "Sets action of relevant armature"
    bl_options = {'REGISTER', 'UNDO'}
    
    action : bpy.props.EnumProperty(
        name="Action", items=lambda x,c: (
            (x.name, x.name, x.name) for x in bpy.data.actions
    ))
    
    def execute(self, context):
        action = bpy.data.actions[self.action]
        FindContextArmature(context).animation_data.action = action
        markerframes = [m.frame for m in action.pose_markers]
        if markerframes:
            context.scene.frame_start = min(markerframes)
            context.scene.frame_end = max(markerframes)
        return {'FINISHED'}
classlist.append(DMR_OP_SetContextArmatureAction)

# =====================================================================================

class DMR_UL_ActionList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=1)
        if item.action != None:
            r = layout.row(align=1)
            r.scale_x = 1.5
            r.operator('dmr.set_context_armature_action', text="", icon='PLAY').action=item.action.name
            r = layout.row(align=1)
            r.prop(item, "action", text="", icon='ACTION', emboss=0)
        else:
            r.prop(item, "action", text="", icon='QUESTION')
classlist.append(DMR_UL_ActionList)

# =====================================================================================

class DMR_PT_ActionList(bpy.types.Panel):
    bl_label = "Action List"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Animation'
    
    def draw(self, context):
        layout = self.layout
        
        alllists = context.scene.actionlists
        activelist = ActiveList(self, context)
        armobj = FindContextArmature(context)
        
        if not activelist:
            layout.operator('dmr.actionlist_list_add', icon='ADD', text="New List")
        elif armobj:
            c = layout.column(align=1)
            r = c.row(align=1)
            r.prop(armobj.data, 'actionlists_index', text='', icon='PRESET', icon_only=1)
            r.prop(activelist, 'name', text="")
            r = r.row(align=1)
            r.operator('dmr.actionlist_list_add', icon='ADD', text="")
            r.operator('dmr.actionlist_list_remove', icon='REMOVE', text="")
            
            # Export List
            if activelist:
                row = layout.row()
                row.template_list(
                    "DMR_UL_ActionList", "", 
                    activelist, "entries", 
                    activelist, "entryindex", 
                    rows=5)
                
                col = row.column(align=True)

                col.operator("dmr.actionlist_entry_add", icon='ADD', text="")
                props = col.operator("dmr.actionlist_entry_remove", icon='REMOVE', text="")
                
                col.separator()
                col.operator("dmr.actionlist_fromsearch", icon='ZOOM_ALL', text="")
                
                col.separator()
                col.operator("dmr.actionlist_entry_move", icon='TRIA_UP', text="").direction = 'UP'
                col.operator("dmr.actionlist_entry_move", icon='TRIA_DOWN', text="").direction = 'DOWN'
classlist.append(DMR_PT_ActionList)

# =================================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)
    
    bpy.types.Scene.actionlists = bpy.props.CollectionProperty(
        name='Export Lists', type=ActionList)
    bpy.types.Scene.actionlists_index = bpy.props.EnumProperty(
        name='Export List Index', default=0, items=GetListItems)
    bpy.types.Armature.actionlists_index = bpy.props.EnumProperty(
        name='Export List Index', default=0, items=GetListItems)

def unregister():
    for c in classlist[::-1]:
        bpy.utils.unregister_class(c)
    del bpy.types.Scene.actionlists
    del bpy.types.Scene.actionlists_index
    del bpy.types.Armature.actionlists_index

if __name__ == "__main__":
    register()
