/**
 * The fs2mod object is defined through python. The methods are implemented in knossos/web.py.
 */

if(USE_WEBKIT) {
    require('es6-shim');
}

import Vue from 'vue';
import get_translation_source from './translations.js';
import KnPage from '../templates/kn-page.vue';

function init() {
    window.call = function (ref) {
        let args = Array.prototype.slice.apply(arguments, [1]);
        
        if(window.qt) {
            ref.apply(null, args);
        } else {
            let cb = args.pop();
            cb(ref.apply(null, args));
        }
    }

    window.connectOnce = function (sig, cb) {
        let wrapper = function () {
            sig.disconnect(wrapper);
            return cb.apply(this, arguments);
        };
        sig.connect(wrapper);
    }

    let tmp = [
        'kn-dev-mod',
        'kn-devel-page',
        'kn-drawer',
        'kn-dropdown',
        'kn-flag-editor',
        'kn-mod-buttons',
        'kn-mod',
        'kn-settings-page'
    ];
    window.tt = [];

    tmp.forEach((comp) => {
        let c = require(`../templates/${comp}.vue`).default;
        tt.push(c);
        Vue.component(comp, c);
    });

    window.vm = new Vue(Object.assign({ el: '#loading' }, KnPage));

    call(fs2mod.finishInit, get_translation_source(), (t) => vm.trans = t);

    let mod_table = null;
    window.task_mod_map = {};

    fs2mod.showWelcome.connect(() => vm.page = 'welcome');
    fs2mod.showDetailsPage.connect((mod) => {
        vm.mod = mod;
        vm.page = 'details';
    });
    fs2mod.showRetailPrompt.connect(() => {
        vm.showRetailPrompt();
    });
    fs2mod.updateModlist.connect((mods, type) => {
        mod_table = {};
        mods = JSON.parse(mods);
        for(let mod of mods) {
            mod_table[mod.id] = mod;
        }

        vm.mods = mods;
        vm.page = type === 'develop' ? 'develop' : 'modlist';
        vm.tab = type;
    });

    let tasks = null;
    call(fs2mod.getRunningTasks, (tasks) => {
        tasks = JSON.parse(tasks);
    });

    fs2mod.taskStarted.connect((tid, title, mods) => {
        if(!tasks) return;

        tasks[tid] = { title, mods };

        for(let mid of mods) {
            if(mod_table[mid]) {
                mod_table[mid].status = 'updating';
                task_mod_map[mid] = tid;
            }
        }
    });

    fs2mod.taskProgress.connect((tid, progress, details) => {
        if(!tasks) return;

        details = JSON.parse(details);
        for(let mid of tasks[tid].mods) {
            if(mod_table[mid]) {
                mod_table[mid].progress = progress;
                mod_table[mid].progress_info = details;
            }
        }
    });

    fs2mod.taskFinished.connect((tid) => {
        if(!tasks) return;

        for(let mid of tasks[tid].mods) {
            if(mod_table[mid]) {
                mod_table[mid].progress = 0;
                mod_table[mid].status = 'ready';
            }

            if(task_mod_map[mid]) delete task_mod_map[mid];
        }

        delete tasks[tid];
    });
}

if(window.qt) {
    new QWebChannel(qt.webChannelTransport, function (channel) {
        window.fs2mod = channel.objects.fs2mod;
        init();
    });
} else {
    window.addEventListener('load', init);
}
