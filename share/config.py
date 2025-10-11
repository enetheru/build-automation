import os.path
import platform
import sys
from pathlib import Path
from types import SimpleNamespace

gopts = SimpleNamespace(**{
    'command': " ".join( sys.argv ),
    'platform': platform.system(),
    'path': Path(os.getcwd()),
    'modules':{},
    'toolchains': {},
    'projects': {},
    'srcdef':SimpleNamespace(),
})


toolchain_base = SimpleNamespace(**{
    'verbs':[],
    'config_vars':[],
    'build_vars': [],
    'targets':[],
    'build_dir':'build-cmake'
})


project_base = SimpleNamespace(**{
    # 'name': set when generated from module as module parent folder.
    'path': 'unpathed',
    'verbs':[],
    'sources':dict[str,SimpleNamespace](),
    'sourcedir':'',
    'buildtools':dict[str,SimpleNamespace](),
    'build_configs' : dict[str,SimpleNamespace](),
})


build_base = SimpleNamespace(**{
    'project':SimpleNamespace(), # Is set at project import
    'name':'',
    'script_path':'', # is set at project import: project.path / f"{build.name}.py"
    'verbs':[],
    'script_parts':[],
    'arch':'x86_64',
    'buildtool': SimpleNamespace(),
    'source_path':'', # is set at project import
    'srcdef':SimpleNamespace(),
    'disabled':False,
})


buildtool_base = SimpleNamespace(**{
    'name':''})

cmake_base = SimpleNamespace({**vars(buildtool_base), **{
    'name':'cmake',
    'verbs':['configure','build','clean'],
    'config_type':'debug',
    'config_types':{
        'Debug':'debug',
        "Release":'release',
        "RelWithDebInfo":'reldeb',
        # "MinSizeRel":'relmin',
    },
    'config_vars':[],
    'build_vars': [],
    'targets':[],
    'build_dir':'build-cmake',
    'generator':'',
    'generators':{
        'Visual Studio 17 2022':'msvc',
        'Ninja':'ninja',
        'Ninja Multi-Config':'ninja-multi',
        'MinGW Makefiles':'mingw',
    }
}})


scons_base = SimpleNamespace({**vars(buildtool_base), **{
    'name':'scons',
    'verbs':[],
    'config_vars':[],
}})


source_base = SimpleNamespace(**{
    'name':'',
    'type':'',
    'verbs':[],
    'url':"",
})

git_base = SimpleNamespace({**vars(source_base), **{
    'type':'git',
    'remote':'origin',
    'verbs':['fetch'],
    'url':"",
    'ref':'HEAD',
    'gitdir':'git', # relative to project path.
}})