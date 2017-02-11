var tasks = {};
var progress_visible = false;
var last_mod = null;

function render_row(mvs, type) {
    var row = $('<div class="mod row">');
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

            fs2mod.install(mod.id, mod.version, []);
        });

        row.find('.info-btn').click(function (e) {
            e.preventDefault();

            fs2mod.showInfo(mod.id, mod.version);
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

            fs2mod.uninstall(mod.id, mod.version, []);
        });
    } else if(type == 'updates') {
        row.html($('#tpl-update-mod').html());

        row.find('.update-btn').click(function (e) {
            e.preventDefault();

            fs2mod.updateMod(mod.id, mod.version);
        });
    }

    var logo = row.find('.mod-logo');
    if(logo.length > 0) {
        if(mod.logo) {
            logo.attr('src', 'file://' + mod.logo_path);
        } else {
            logo.replaceWith('<div class="no-logo">');
        }
    }

    row.find('.title').text(mod.title);
    return row;
}

function update_mods(mods, type) {
    $('#loading').hide();
    $('#mods').show();
    $('.info-page').hide();

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
        console.log(mod);
        mod_list.append(render_row(mod, type));
    });
}

function display_last(mod) {
    $('#loading, .info-page').hide();
    $('#mods').hide();

    var cont = $('#last-played');
    if(!mod) {
        $('#no-last-played').show();
        return;
    } else {
        cont.show();
    }

    cont.find('.title').text(mod.title);

    if(mod.logo_path) {
        cont.find('.mod-logo').attr('src', 'file://' + mod.logo_path).show();
    } else {
        cont.find('.mod-logo').hide();
    }

    cont.find('.desc').text(mod.description);
    cont.show();
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
    prg_bar.css('width', info.progress + '%');

    label.text(info.title);
    
    var sub_well = cont.find('.well');
    
    $.each(info.subs, function (i, sub) {
        var row = sub_well.find('.s-' + i);
        if(row.length == 0) {
            row = $('<div>').html('<span></span><br><div class="progress"><div class="progress-bar"></div></div>');
            row.addClass('s-' + i);
            sub_well.append(row);
        }

        if(sub[1] == 'Done' || sub[1] == 'Ready') {
            row.hide();
        } else {
            row.show();
            row.find('span').text(sub[1]);
            row.find('.progress-bar').css('width', (sub[0] * 100) + '%');
        }
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
        subs: JSON.parse(info),
        title: text
    };

    if(progress_visible) {
        var task_cont = $('#task-' + id);
        if(task_cont.length == 0) {
            $('#mods').append(_render_task(id, tasks[id]));
        } else {
            _update_task(task_cont, tasks[id]);
        }
    }
}

function remove_task(id) {
    delete tasks[id];
    $('#task-' + id).remove();

    console.log(['Remove', id]);
}

function show_progress() {
    progress_visible = true;
    $('.info-page').hide();
    var modlist = $('#mods').empty().show();

    $.each(tasks, function (id, obj) {
        modlist.append(_render_task(id, obj));
    });
}

function process_tr(func) {
    var keys = [];
    var trans = {};

    function fakeTr(c, k) {
        return trans[k];
    }

    // Find all neccessary translation keys.
    func.toString().replace(/qsTr\('[^']+', ([^)]+)\)/g, function (m, part) {
        keys.push(eval(part));
    });

    // Call fs2mod.tr() for each key
    var next = 0;
    function fetch() {
        if(next >= keys.length) {
            // We're done and can finally call the original function
            func(fakeTr);
        } else {
            var k = keys[next++];
            fs2mod.tr('modlist', k, function (res) {
                trans[k] = res;
                fetch();
            });
        }
    }

    fetch();
}

function show_welcome() {
    $('.info-page, #mods, #loading').hide();

    process_tr(function (qsTr) {
        $('#welcome').html(qsTr('modlist', '<h1>Welcome!</h1>' +
            '<p>It looks like you started Knossos for the first time.</p>' +
            '<p>' +
                'You can tell me where your FS2 installation is, I could install FS2 using the GOG installer' +
                'or maybe you want to install a Total Conversion?' +
            '</p>') +
            '<hr>' +

            '<p>' +
                '<a class="btn btn-primary" id="sel-fso">' + qsTr('modlist', 'Select FS2 directory') + '</a>' +
            '</p>' +
            '<p>' +
                '<a class="btn btn-primary" id="gog-install">' + qsTr('modlist', 'Install FS2 using the GOG installer') + '</a>' +
            '</p>' +
            '<p>' +
                '<a class="btn btn-primary" id="tc-install">' + qsTr('modlist', 'Install a TC') + '</a>' +
            '</p>' +
            qsTr('modlist', '<p>' +
                    'This launcher is still in development. Please visit ' +
                    '<a href="http://www.hard-light.net/forums/index.php?topic=93144.0" target="_blank">this HLP thread</a> ' +
                    'and let me know what you think, what didn\'t work and what you would like to change.' +
                '</p>' +
                '<p>-- ngld</p>'
            )
        ).show();
    });
}

function init() {
    $('.hide').removeClass('hide').hide();

    process_tr(function (qsTr) {
        $('#loading').text(qsTr('modlist', 'Loading'));
        $('#no-last-played span').text(qsTr('modlist', "You haven't played any mod, yet."));
        $('.run-btn span').text(qsTr('modlist', 'Play'));
        $('.install-btn span').text(qsTr('modlist', 'Install'));
        $('.update-btn span').text(qsTr('modlist', 'Update'));
    });

    fs2mod.showWelcome.connect(show_welcome);
    fs2mod.showLastPlayed.connect(display_last);
    fs2mod.updateModlist.connect(update_mods);
    fs2mod.taskStarted.connect(add_task);
    fs2mod.taskProgress.connect(update_progress);
    fs2mod.taskFinished.connect(remove_task);

    fs2mod.finishInit();
}

if(window.qt) {
    new QWebChannel(qt.webChannelTransport, function (channel) {
        window.fs2mod = channel.objects.fs2mod;
        init();
    });
} else {
    $(init);
}