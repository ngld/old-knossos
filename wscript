import os
from waflib import Options
from waflib.Build import BuildContext

top = '.'
out = 'build'

UI_FILES = [
    'ui/flags.ui',
    'ui/gogextract.ui',
    'ui/hell.ui',
    'ui/install.ui',
    'ui/log_viewer.ui',
    'ui/mod_settings.ui',
    'ui/mod_versions.ui',
    'ui/select_list.ui'
]

SRC_FILES = [
    'knossos/third_party/__init__.py',
    'knossos/third_party/cpuinfo.py',
    'knossos/ui/__init__.py',
    'knossos/__init__.py',
    'knossos/__main__.py',
    'knossos/api.py',
    'knossos/center.py',
    'knossos/clibs.py',
    'knossos/integration.py',
    'knossos/ipc.py',
    'knossos/launcher.py',
    'knossos/progress.py',
    'knossos/py2_compat.py',
    'knossos/qt.py',
    'knossos/repo.py',
    'knossos/runner.py',
    'knossos/tasks.py',
    'knossos/util.py',
    'knossos/web.py',
    'knossos/windows.py'
]

LOCALES = [
    # 'locale/knossos_%CODE%.ts'
]


def build_qrc(task):
    out = '<!DOCTYPE RCC><RCC version="1.0">'
    out += '<qresource>'

    for node in task.inputs:
        if node.name == 'hlp.png':
            out += '<file alias="hlp.png">%s</file>' % node.abspath()
        else:
            out += '<file alias="%s">%s</file>' % (node.relpath(), node.abspath())

    out += '</qresource>'
    out += '</RCC>'
    
    qrc = task.get_cwd().find_or_declare('res.qrc')
    qrc.write(out, 'w', 'utf8')

    e = task.env
    task.exec_command(e.RCC + ['-binary', qrc.abspath(), '-o', task.outputs[0].abspath()])


def options(opt):
    opt.load('python')


def configure(cfg):
    cfg.load('python')
    cfg.load('pyextras', tooldir='tools/waf')

    cfg.check_python_version((2, 7, 0))
    cfg.check_python_module('PyQt5')
    cfg.check_python_module('semantic_version')
    cfg.check_python_module('six')
    cfg.check_python_module('requests')

    cfg.try_program([['${PYTHON}', '-mPyQt5.uic.pyuic'], ['pyuic5'], ['pyuic']], var='PYUIC', msg='pyuic')
    cfg.try_program([['${PYTHON}', '-mPyQt5.pylupdate_main'], ['pylupdate5'], ['pylupdate']], var='PYLUPDATE', msg='pylupdate', test_param='-version')

    cfg.find_program(['lupdate-qt5', 'lupdate'], var='LUPDATE', msg='Checking for lupdate')
    cfg.find_program(['lrelease-qt5', 'lrelease'], var='LRELEASE', msg='Checking for lrelease')
    cfg.find_program(['rcc-qt5', 'rcc'], var='RCC', msg='Checking for rcc')

    cfg.env.JS_LUPDATE = cfg.env.PYTHON + [cfg.path.find_node('./tools/common/js_lupdate.py').abspath()]
    cfg.env.NOPYCACHE = True


def build(bld):
    bld.load('python')
    bld.load('pyextras', tooldir='tools/waf')

    bld(features='pyuic py', source=UI_FILES, outpath='knossos/ui')
    bld(features='py', source=SRC_FILES)

    bld(
        rule    = '${JS_LUPDATE} -o ${TGT} ${SRC}',
        source  = ['html/js/modlist.js', 'html/index.html'],
        target  = 'html/js/modlist_ts.js'
    )

    bld(
        rule   = build_qrc,
        source = bld.path.ant_glob('html/**') + bld.path.ant_glob('ui/**.png') + bld.path.ant_glob('ui/**.jpg') +
            bld.path.ant_glob('ui/**.css') + ['knossos/data/hlp.png'],
        target       = 'knossos/data/resources.rcc',
        install_path = '${PYTHONDIR}/knossos/data'
    )

    bld.install_as('${PYTHONDIR}/knossos/data/hlp.png', 'knossos/data/hlp.png')
    bld(
        features     = 'lrelease',
        source       = LOCALES,
        outpath      = '${PYTHONDIR}/knossos/data',
        install_path = '${PYTHONDIR}/knossos/data'
    )


class LaunchCmd(BuildContext):
    cmd = 'launch'
    fun = 'launch'


def launch(ctx):
    ctx.exec_command(ctx.env.PYTHON + ['-mknossos'], cwd=ctx.bldnode, stdout=None, stderr=None)


def run(ctx):
    Options.commands = ['build', 'launch'] + Options.commands


class UpdateTrans(BuildContext):
    cmd = 'update-trans'
    fun = 'update_trans'


def update_trans(ctx):
    ctx(
        rule   = '${PYLUPDATE} ${SRC} -ts ${TGT}',
        source = SRC_FILES,
        target = 'locale/_py.ts',
        shell  = False
    )

    ctx(
        rule   = '${LUPDATE} -no-obsolete ${SRC} -ts ${TGT}',
        source = ['locale/_py.ts', 'html/js/modlist_ts.js'] + UI_FILES,
        target = 'locale/knossos.ts',
        shell  = False
    )

    for fn in LOCALES:
        ctx(
            rule = '${LUPDATE} -no-obsolete ${SRC} -ts ${TGT}',
            source = 'locale/knossos.ts',
            target = fn,
            shell  = False
        )
