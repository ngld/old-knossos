import os.path
from waflib import Task, TaskGen, Node, Utils
from waflib.Configure import conf


@TaskGen.feature('pyuic')
@TaskGen.before_method('process_source')
def build_pyuic(self):
    source = self.to_nodes(self.source)
    self.source = []

    for node in source:
        out = self.bld.bldnode.find_or_declare(os.path.join(self.outpath, node.name[:-3] + '.py'))
        self.create_task('pyuic', [node], [out])
        self.source.append(out)


@TaskGen.feature('lrelease')
@TaskGen.before_method('process_source')
def build_ts(self):
    for node in self.to_nodes(self.source):
        out = self.bld.bldnode.find_or_declare(os.path.join(self.outpath, node.name[:-3] + '.qm'))
        self.create_task('lrelease', [node], [out])

    self.source = []


Task.task_factory('pyuic', '${PYUIC} -o ${TGT} ${SRC}', ext_in=['.ui'], ext_out=['.py'])
Task.task_factory('lrelease', '${LRELEASE} -compress -removeidentical -markuntranslated "%" ${SRC} -qm ${TGT}', ext_in=['.ts'], ext_out=['.qm'])

TaskGen.declare_chain(
    name      = 'rcc',
    rule      = '${RCC} -binary ${SRC} -o ${TGT}',
    ext_in    = '.qrc',
    ext_out   = '.rcc',
    reentrant = False
)


@conf
def try_program(conf, cmds, var, msg, test_param='--version'):
    conf.start_msg('Checking for %s' % msg)

    if var in os.environ:
        cmds = [os.environ[var]]
    elif conf.env[var]:
        cmds = [conf.env[var]]

    for cmd in cmds:
        if isinstance(cmd, str):
            cmd = [cmd]

        cmd = [Utils.subst_vars(p, conf.env) for p in cmd]

        try:
            conf.cmd_and_log(cmd + [test_param])
            conf.env[var] = cmd
            conf.end_msg(' '.join(cmd))
            return
        except:
            pass

    conf.end_msg(False)
    conf.fatal('Could not find %s!' % msg)
