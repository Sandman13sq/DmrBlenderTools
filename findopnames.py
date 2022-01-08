import os
import sys
import io
import string
import pyperclip

OMITPATH = ['__init__', '__pycache__']

VARCHAR = string.ascii_letters + '_0123456789';

def GetPropType(l):
    if 'BoolProperty' in l:
        return 'bool'
    if 'FloatProperty' in l:
        return 'float'
    if 'IntProperty' in l:
        return 'int'
    if 'StringProperty' in l:
        return 'string'
    if 'EnumProperty' in l:
        return 'enum'
    return '???'

def ParseQuote(l, newchar):
    qchar = 0
    qpos = -1
    l = [x for x in l]
    
    for i,c in enumerate(l):
        if qchar == 0:
            if c == '"' or c == "'":
                qchar = c
                qpos = i
        else:
            if c == qchar:
                l[i] = newchar
                l[qpos] = newchar
                qchar = 0
    
    return ''.join(l)


def FindClassNames(path, t=0):
    if os.path.isfile(path):
        FileCheck(path, path[path.rfind('/')+1:])
        return
    
    pathlist = os.listdir(path)
    
    for p in pathlist:
        fullpath = path+'/'+p
        
        if len([x for x in OMITPATH if x in p])==0:
            # Is file
            if os.path.isfile(fullpath):
                FileCheck(fullpath, p)
            # Is directory
            else:
                FindClassNames(fullpath, t+1)

def FileCheck(fullpath, p):
    f = open(fullpath, 'r')
    if f:
        classnames = [];
        classinfo = []
        
        mode = 0
        pstack = 0
        out = ''
        
        oplinenumber = 0
        paramlinenumber = 0
        
        info = None
        
        for linenumber, l in enumerate(f):
            if 'register()' in l:
                break
            
            l = l.replace('%%s', '<input>')
            l = l.replace('%%d', '<input>')
            
            if 'Operator' in l and 'class' in l:
                if info:
                    if not info['desc']:
                        print('> Missing Description for "%s" line %d' % (info['label'], oplinenumber))
                
                c = l[l.find('class ')+len('class'):l.find('(')];
                classnames.append(c)
                info = {'label': '', 'idname': '', 'desc': '', 'params': []}
                classinfo.append(info)
                oplinenumber = linenumber
                mode = 0

            l = ParseQuote(l, '`')
            lsub = l[l.find('`')+1: l.rfind('`')]
            if 'bl_description' in l:
                info['desc'] = lsub
            elif 'bl_idname' in l:
                info['idname'] = lsub
            elif 'bl_label' in l:
                info['label'] = lsub
            elif 'Property' in l:
                mode = 1
                pstack = 0
                param = {'name': '', 'desc': '', 'type': GetPropType(l), 'varname': ''}
                param['varname'] = ''.join([x for x in l[:l.find(':')] if x in VARCHAR])
                paramlinenumber = linenumber
            
            if mode == 1:
                if '(' in l:
                    pstack += 1
                
                if 'name=' in l or 'name =' in l:
                    pos = l.find('`', l.find('name'))
                    param['name'] = l[pos+1:l.find('`', pos+1)]
                    print(param['name'])
                if 'description=' in l or 'description =' in l:
                    pos = l.find('`', l.find('description'))
                    param['desc'] = l[pos+1:l.find('`', pos+1)]
                
                if ')' in l:
                    pstack -= 1
                    if pstack == 0:
                        mode = 0
                        
                        if not param['desc']:
                            print('> Missing Description for "%s" line %d' % (param['varname'], paramlinenumber))
                        
                        info['params'].append(param)
            
        f.close()
        
        if classinfo:
            for info in classinfo:
                out += '## %s  \n' % info['label']
                out += '> %s(' % info['idname']
                
                if info['params']:
                    pend = len(info['params'])-1
                    for i, p in enumerate(info['params']):
                        out += p['varname']
                        if i < pend:
                            out += ', '
                        
                out += ')  \n'
                
                out += '- %s  \n' % info['desc']
                
                for p in info['params']:
                    out += str.format('\t- **%s**: %s *(%s)*\n' % (p['name'], p['desc'], p['type']))
                
                out += '\n'
                
                print(info['label'])
        
        pyperclip.copy(out)
        
print('-'*80)
FindClassNames(sys.argv[1])

