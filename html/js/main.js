/**
 * The fs2mod object is defined through python. The methods are implemented in knossos/web.py.
 */

import './preboot';
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
    };

    let cb_id = 0;
    let cb_store = {};
    window.call_async = function (ref) {
        let args = Array.prototype.slice.apply(arguments, [1]);
        let cb = args.pop();
        args.push(cb_id);
        cb_store[cb_id] = cb;

        ref.apply(null, args);
        cb_id++;
    };

    window.call_promise = function (ref) {
        let args = Array.prototype.slice.apply(arguments, [0]);

        return new Promise((resolve) => {
            args.push(resolve);
            call.apply(null, args);
        });
    };

    window.call_async_promise = function (ref) {
        let args = Array.prototype.slice.apply(arguments, [0]);

        return new Promise((resolve) => {
            args.push(resolve);
            call_async.apply(null, args);
        });
    };

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
        'kn-global-flags',
        'kn-mod-home',
        'kn-mod-explore',
        'kn-scroll-container',
        'kn-settings-page',
        'kn-welcome-page'
    ];

    tmp.forEach((comp) => {
        Vue.component(comp, require(`../templates/${comp}.vue`).default);
    });

    window.vm = new Vue(Object.assign({ el: '#loading' }, KnPage));

    let explore_mod_table = {};
    let installed_mod_table = {};
    let mod_table = null;
    window.task_mod_map = {};

    let getModTable = function (type) {
        if(type === 'explore') {
            return explore_mod_table;
        } else if(type === 'home' || type === 'develop') {
            return installed_mod_table;
        } else {
            // TODO print error/warning unknown type!
            return explore_mod_table;
        }
    };

    let buildModArray = function (mod_order) {
        let mods = [];

        for(let mod_id of mod_order) {
            let mod = mod_table[mod_id];
            if(mod) {
                mods.push(mod);
            } else {
                // TODO print error/warning about mod not found in mod_table
            }
        }
        return mods;
    };

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
        vm.showRetailPrompt(true);
    });
    fs2mod.showLaunchPopup.connect((info) => {
        info = JSON.parse(info);

        vm.popup_mode = 'launch_mod';
        vm.popup_title = 'Launch ' + info.title;
        vm.popup_mod_id = info.id;
        vm.popup_mod_version = info.version;
        vm.popup_mod_exes = info.exes;
        vm.popup_mod_sel_exe = info.selected_exe;
        vm.popup_mod_is_tool = info.is_tool;
        vm.popup_mod_flag = info.mod_flag;
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
            vm.detail_mod = mid;
        }

        cb();
    });
    fs2mod.updateModlist.connect((updated_mods, type, mod_order) => {
        mod_table = getModTable(type);
        window.mod_table = mod_table;
        updated_mods = JSON.parse(updated_mods);

        for(let mod_id of Object.keys(updated_mods)) {
            Vue.set(mod_table, mod_id, updated_mods[mod_id]);
        }
        vm.mod_table = mod_table;

        let mods = buildModArray(mod_order);
        
        vm.updateModlist(mods);
    });
    fs2mod.hidePopup.connect(() => vm.popup_visible = false);

    let tasks = null;
    call(fs2mod.getRunningTasks, (raw_tasks) => {
        if(raw_tasks) {
            tasks = JSON.parse(raw_tasks);
        }
    });

    fs2mod.taskStarted.connect((tid, title, mods) => {
        if(!tasks) return;

        tasks[tid] = { title, mods };

        for(let mid of mods) {
            if(mod_table[mid]) {
                Vue.set(mod_table[mid], 'status', 'updating');
                task_mod_map[mid] = tid;
            }
        }
    });

    fs2mod.taskProgress.connect((tid, progress, details) => {
        if(!tasks) return;

        details = JSON.parse(details);
        for(let mid of tasks[tid].mods) {
            if(mod_table[mid]) {
                Vue.set(mod_table[mid], 'progress', progress);
                Vue.set(mod_table[mid], 'progress_info', details);
            }

            vm.$set(vm.popup_progress, mid, details);
        }
    });

    fs2mod.taskFinished.connect((tid) => {
        if(!tasks) return;

        for(let mid of tasks[tid].mods) {
            if(mod_table[mid]) {
                Vue.set(mod_table[mid], 'progress', 0);
                Vue.set(mod_table[mid], 'status', 'ready');
            }

            if(task_mod_map[mid]) delete task_mod_map[mid];
        }

        delete tasks[tid];
    });

    fs2mod.taskMessage.connect((msg) => {
        vm.popup_progress_message = msg;
    });

    fs2mod.fs2Launching.connect((msg) => {
        vm.status_message = 'FSO is launching...';
    });

    fs2mod.fs2Launched.connect((msg) => {
        vm.status_message = 'FSO is running.';
    });

    fs2mod.fs2Quit.connect((msg) => {
        vm.status_message = '';
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

        let explore_mods = JSON.parse(res.explore_mods);
        for(let mod_id of Object.keys(explore_mods)) {
            explore_mod_table[mod_id] = explore_mods[mod_id];
        }
    }), 300);

    window.addEventListener('error', (e) => {
       fs2mod.reportError(e.error ? (e.error.stack || e.error.toString()) : e.message);
    });
}

if(window.qt) {
    new QWebChannel(qt.webChannelTransport, function (channel) {
        window.fs2mod = channel.objects.fs2mod;
        init();
    });
} else if(window.fs2mod) {
    window.addEventListener('load', init);
} else if(KN_DEBUG) {
    let socket = new WebSocket('ws://localhost:4007');

    socket.onclose = function() {
        console.error("web channel closed");
    };

    socket.onerror = function(error) {
        console.error("web channel error: " + error);
    };

    socket.onopen = function() {
        window.qt = true;
        new QWebChannel(socket, function (channel) {
            window.fs2mod = channel.objects.fs2mod;
            init();
        });
    };
}
