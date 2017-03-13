var tasks = {};
var last_mod = null;
var tr_table = {};

function render_row(mod, type) {
    var row = $('<div class="mod row">').attr('id', 'mod-' + mod.id);

    if(type == 'available') {
        row.html($('#tpl-avail-mod').html());

        row.find('.avail-cover').click(function (e) {
            e.preventDefault();

            fs2mod.showAvailableDetails(mod.id, mod.version);
        });
    } else if(type == 'installed') {
        row.html($('#tpl-installed-mod').html());

        row.find('.run-btn').click(function (e) {
            e.preventDefault();

            fs2mod.runMod(mod.id, mod.version);
        });
        row.find('.fred-btn').click(function (e) {
            e.preventDefault();

            fs2mod.runFredMod(mod.id, mod.version);
        });
        row.find('.settings-btn').click(function (e) {
            e.preventDefault();

            fs2mod.showInstalledDetails(mod.id, mod.version);
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

    var logo = row.find('.mod-logo-legacy');
    if(logo.length > 0) {
        if(mod.logo) {
            logo.attr('src', 'file://' + mod.logo_path);
        } else {
            logo.replaceWith('<div class="no-logo">');
        }
    }

    row.find('.mod-title').text(mod.title);
    return row;
}

function update_mods(mods, type) {
    $('#loading').hide();
    $('#mods').show();
    $('.info-page').hide();

    $('#tab-bar .main-btn').removeClass('active');
    $('#' + type + '-tab').addClass('active');

    var mod_list = $('#mods').html('');

    $.each(mods, function (mid, info) {
        mod_list.append(render_row(info[0], type));
    });
}

function display_mod_details(mod) {
    $('#details-box').text(js_beautify(JSON.stringify(mod)));

    $('#details-page *[data-field]').each(function () {
        var $this = $(this);
        $this.text(mod[$this.attr('data-field')]);
    });

    $('#mods, #tab-bar').hide();
    $('#details-page, #details-tab-bar').show();
}

function add_task(id, text, mods) {
    tasks[id] = { title: text, progress: 0, mods: mods };

    $.each(mods, function (i, mid) {
        $('#mod-' + mid + ' .mod-progress .bar').css('width', '0%')
    });
}

function update_progress(id, percent, text) {
    var mods = tasks[id].mods;
    tasks[id] = {
        progress: percent,
        title: text,
        mods: mods
    };

    $.each(mods, function (i, mid) {
        $('#mod-' + mid + ' .mod-progress .bar').css('width', percent + '%')
    });
}

function remove_task(id) {
    var mods = tasks[id].mods;
    delete tasks[id];

    $.each(mods, function (i, mid) {
        $('#mod-' + mid + ' .mod-progress .bar').css('width', '0%')
    });
}

function load_translations(cb) {
    tr_table = {};
    var keys = get_translation_source();

    // Call fs2mod.tr() for each key
    if(window.qt) {
        var next = 0;
        function fetch() {
            if(next < keys.length) {
                var k = keys[next++];
                fs2mod.tr('modlist_ts', k, function (res) {
                    tr_table[k] = res;
                    fetch();
                });
            } else {
                cb();
            }
        }

        fetch();
    } else {
        for(var i = 0; i < keys.length; i++) {
            tr_table[keys[i]] = fs2mod.tr('modlist_ts', keys[i]);
        }

        cb();
    }
}

function show_welcome() {
    $('.info-page, #mods, #loading').hide();
    $('#welcome').show();
}

function init() {
    $('.hide').removeClass('hide').hide();

    $('#last-played .run-btn').click(function (e) {
        e.preventDefault();

        fs2mod.runMod($(this).data('modid'), '');
    });

    load_translations(function () {
        $('div[data-tr], span[data-tr]').each(function () {
            var $this = $(this);
            $this.html(tr_table[$this.html()]);
        });

        $('a[target="_blank"]').click(function (e) {
            e.preventDefault();

            fs2mod.openExternal($(this).attr('href'));
        });

        $('#update-list').click(function (e) {
            e.preventDefault();

            fs2mod.fetchModlist();
        });

        $('#settings-btn').click(function (e) {
            e.preventDefault();

            fs2mod.showSettings('', '');
        });

        $('#installed-tab').click(function (e) {
            e.preventDefault();

            fs2mod.showTab('installed');
        });

        $('#available-tab').click(function (e) {
            e.preventDefault();

            fs2mod.showTab('available');
        });

        $('#search-field').keyup(function (e) {
            fs2mod.triggerSearch($(this).val());
        });

        $('#details-exit').click(function (e) {
            e.preventDefault();

            $('#details-tab-bar, #details-page').hide();
            $('#tab-bar, #mods').show();
        });

        $('.browse-btn').click(function (e) {
            e.preventDefault();

            var target = $(this).attr('data-browse-target');
            if(window.qt) {
                fs2mod.browseFolder('Please select a folder', $(target).val(), function (path) {
                    if(path) $(target).val(path);
                });
            } else {
                var path = fs2mod.browseFolder('Please select a folder', $(target).val());
                if(path) $(target).val(path);
            }
        });

        $('.welcome-continue').click(function (e) {
            e.preventDefault();

            fs2mod.setBasePath($('#kn-data-path').val());
        });
    });

    fs2mod.showWelcome.connect(show_welcome);
    fs2mod.showDetailsPage.connect(display_mod_details);
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