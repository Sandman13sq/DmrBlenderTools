import os
import sys
import io

OMITPATH = ['__init__', '__pycache__']

def FindClassNames(path, t=0):
    pathlist = os.listdir(path)
    
    for p in pathlist:
        fullpath = path+'/'+p
        
        if len([x for x in OMITPATH if x in p])==0:
            # Is file
            if os.path.isfile(fullpath):
                f = open(fullpath, 'r')
                if f:
                    classnames = [];
                    
                    for l in f:
                        if 'Operator' in l and 'class' in l:
                            c = l[l.find('class ')+len('class'):l.find('(')];
                            classnames.append(c)
                    f.close()
                    
                    if classnames:
                        print('\t# %s' % p)
                        for c in classnames:
                            print('\t%s,' % c)
            # Is directory
            else:
                FindClassNames(fullpath, t+1)
    

FindClassNames(sys.argv[1])

