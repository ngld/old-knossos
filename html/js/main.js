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

    let cb_id = 0;
    let cb_store = {};
    window.call_async = function (ref) {
        let args = Array.prototype.slice.apply(arguments, [1]);
        let cb = args.pop();
        args.push(cb_id);
        cb_store[cb_id] = cb;

        ref.apply(null, args);
        cb_id++;
    }

    window.connectOnce = function (sig, cb) {
        let wrapper = function () {
            sig.disconnect(wrapper);
            return cb.apply(this, arguments);
        };
        sig.connect(wrapper);
    }

    let tmp = [
        'kn-details-page',
        'kn-dev-mod',
        'kn-devel-page',
        'kn-drawer',
        'kn-dropdown',
        'kn-fso-settings',
        'kn-fso-user-settings',
        'kn-mod-home',
        'kn-mod-explore',
        'kn-settings-page',
        'kn-welcome-page'
    ];

    tmp.forEach((comp) => {
        Vue.component(comp, require(`../templates/${comp}.vue`).default);
    });

    window.vm = new Vue(Object.assign({ el: '#loading' }, KnPage));

    let mod_table = null;
    window.task_mod_map = {};

    fs2mod.asyncCbFinished.connect((id, data) => {
        cb_store[id](JSON.parse(data));
        delete cb_store[id];
    });
    fs2mod.showWelcome.connect(() => vm.page = 'welcome');
    fs2mod.showDetailsPage.connect((mod) => {
        vm.mod = mod;
        vm.page = 'details';
    });
    fs2mod.showRetailPrompt.connect(() => {
        vm.showRetailPrompt();
    });
    fs2mod.showLaunchPopup.connect((info) => {
        info = JSON.parse(info);

        vm.popup_mode = 'launch_mod';
        vm.popup_title = 'Launch ' + info.title;
        vm.popup_mod_id = info.id;
        vm.popup_mod_version = info.version;
        vm.popup_mod_exes = info.exes;
        vm.popup_mod_flag = info.mod_flag;
        vm.popup_mod_sel_exe = info.exes[0][0];
        vm.popup_mod_flag_map = {};

        for(let part of info.mod_flag) {
            vm.popup_mod_flag_map[part[0]] = true;
        }

        vm.popup_visible = true;
    });
    fs2mod.showModDetails.connect((mid) => {
        function cb() {
            if(!mod_table || !mod_table[mid]) {
                setTimeout(cb, 300);
                return;
            }

            vm.page = 'details';
            vm.mod = mod_table[mid];
        }

        cb();
    });
    fs2mod.updateModlist.connect((mods, type) => {
        window.mod_table = mod_table = {};
        mods = JSON.parse(mods);
        for(let mod of mods) {
            mod_table[mod.id] = mod;
        }

        vm.updateModlist(mods);
    });
    fs2mod.hidePopup.connect(() => vm.popup_visible = false);

    let tasks = null;
    call(fs2mod.getRunningTasks, (raw_tasks) => {
        tasks = JSON.parse(raw_tasks);
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
                vm.$set(vm.popup_progress, mid, details);
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

    fs2mod.taskMessage.connect((msg) => {
        vm.popup_progress_message = msg;
    });

    // Open <a href="..." target="_blank">...</a> links in the system's default browser
    document.body.addEventListener('click', (e) => {
        if(e.target && e.target.nodeName === 'A' && e.target.className && e.target.className.indexOf('open-ext') > -1) {
            e.preventDefault();
            fs2mod.openExternal(e.target.href);
        }
    });

    setTimeout(() => call(fs2mod.finishInit, get_translation_source(), (res) => {
        res = JSON.parse(res);
        
        vm.trans = res.t;
        window.platform = res.platform;

        if(res.welcome) {
            vm.page = 'welcome';
        }
    }), 300);
}

if(window.qt) {
    new QWebChannel(qt.webChannelTransport, function (channel) {
        window.fs2mod = channel.objects.fs2mod;
        init();
    });
} else {
    window.addEventListener('load', init);
}
