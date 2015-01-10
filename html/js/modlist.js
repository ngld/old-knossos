//(function () {
    var tasks = {};
    var progress_visible = false;

    function render_row(mvs, type) {
        var row = $('<div class="mod">');
        var mod;

        if($.isArray(mvs)) {
            mod = mvs[0];
        } else {
            mod = mvs;
            mvs = [mod];
        }

        if(type == 'available') {
            row.html($('#tpl-avail-mod').html());

            row.find('.install-btn').click(function (e) {
                e.preventDefault();

                fs2mod.install(mod.id, mod.version);
            });
        } else if(type == 'installed') {
            row.html($('#tpl-installed-mod').html());

            row.find('.run-btn').click(function (e) {
                e.preventDefault();

                fs2mod.runMod(mod.id, mod.version);
            });
            row.find('.settings-btn').click(function (e) {
                e.preventDefault();

                fs2mod.showSettings(mod.id, mod.version);
            });
            row.find('.del-btn').click(function (e) {
                e.preventDefault();

                fs2mod.uninstall(mod.id, mod.version);
            });
        // } else if(type == 'downloading') {
        //     row.html($('#tpl-dl-mod').html());
        //     row.find('.progress-bar').attr('id', 'mod-prg-' + mod.id);

        //     row.find('.noop-btn').click(function (e) {
        //         e.preventDefault();
        //     });
        //     row.find('.abort-btn').click(function (e) {
        //         e.preventDefault();

        //         fs2mod.abortDownload(mod.id);
        //     });
        } else if(type == 'updates') {
            row.html($('#tpl-update-mod').html());

            row.find('.update-btn').click(function (e) {
                e.preventDefault();

                fs2mod.updateMod(mod.id, mod.version);
            });
        }

        row.find('.title').text(mod.title);
        return row;
    }

    function update_mods(mods, type) {
        $('#loading').hide();

        if(type == 'progress') {
            progress_visible = true;
            show_progress();
            return;
        } else {
            progress_visible = false;
        }

        var names = [];
        var mod_list = $('#mods').html('');

        $.each(mods, function (mid, info) {
            names.push([mid, info[0].title]);
        });

        names.sort(function (a, b) {
            return a[1] > b[1] ? 1 : (a[1] < b[1] ? -1 : 0);
        });

        names.forEach(function (item) {
            var mod = mods[item[0]];
            mod_list.append(render_row(mod, type));
        });
    }

    function _render_task(id, info) {
        var cont = $('<div class="mod">').html($('#tpl-dl-mod').html());
        cont.attr('id', 'task-' + id);

        cont.find('.abort-btn').click(function (e) {
            e.preventDefault();

            fs2mod.abortTask(id);
        });

        _update_task(cont, info);
        return cont;
    }

    function _update_task(cont, info) {
        var label = cont.find('.title');
        var prg_bar = cont.find('.master-prg');
        prg_bar.css('width', (info.progress * 100) + '%');

        if(info.progress == 1) {
            prg_bar.removeClass('active');
            prg_bar.removeClass('progress-bar-striped');
        }
        
        label.text(info.title);
        
        var sub_well = cont.find('.well');
        sub_well.empty();

        $.each(info.subs, function (i, sub) {
            var row = $('<div>');
            row.append($('<span>').text(sub[1]));
            row.append('<br>');

            row.append($('<div class="progress">').html($('<div class="progress-bar">').css('width', (sub[0] * 100) + '%')));
            sub_well.append(row);
        });
    }

    function add_task(id, text) {
        tasks[id] = { title: text, progress: 0, subs: [] };

        if(progress_visible) {
            $('#mods').append(_render_task(id, tasks[id]));
        }
    }

    function update_progress(id, percent, info, text) {
        tasks[id] = {
            progress: percent,
            subs: info,
            title: text
        };

        if(progress_visible) {
            var task_cont = $('#task-' + id);
            if(task_cont.length == 0) return;

            _update_task(task_cont, tasks[id]);
        }
    }

    function remove_task(id) {
        delete tasks[id];
        $('#task-' + id).remove();
    }

    function show_progress() {
        var modlist = $('#mods').empty();

        $.each(tasks, function (id, obj) {
            modlist.append(_render_task(id, obj));
        });
    }

    $(function () {
        fs2mod.updateModlist.connect(update_mods);
        fs2mod.taskStarted.connect(add_task);
        fs2mod.taskProgress.connect(update_progress);
        fs2mod.taskFinished.connect(remove_task);
    });
//})();